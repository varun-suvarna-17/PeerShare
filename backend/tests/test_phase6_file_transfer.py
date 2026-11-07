"""Unit and integration tests for Phase 6: File Transfer and Integrity.

Covers all 14 Phase 6 testing requirements:
1. Small file transfer.
2. Maximum permitted file size (5 MB boundary & rejection of > 5MB).
3. Empty file transfer (0 bytes, 0 frames).
4. All three ARQ protocols (Stop-and-Wait, Go-Back-N, Selective Repeat).
5. Packet loss during file transfer (deterministic seeded simulation).
6. ACK loss and retransmission.
7. Out-of-order frame delivery and Selective Repeat buffering.
8. Duplicate frame handling and discard tracking.
9. File reconstruction and collision avoidance naming.
10. SHA-256 verification and corruption failure cleanup.
11. Interrupted transfer (timeout & retry limit exceeded).
12. Invalid filename and path traversal attempts.
13. Insufficient disk space handling.
14. Lost FIN-ACK and completion recovery (receiver linger).
Multi-process integration test between two independent backend processes.
"""

import asyncio
import hashlib
import multiprocessing as mp
import os
import shutil
import tempfile
import time
import uuid
import pytest

from app.file.manager import (
    FileManager,
    FileTooLargeError,
    InsufficientDiskSpaceError,
    IntegrityVerificationError,
    InvalidFilenameError,
    calculate_sha256,
    sanitize_filename,
    validate_filename,
)
from app.file.models import MAX_FILE_SIZE
from app.network.loss import PacketLossSimulator
from app.network.receiver import UdpReceiver
from app.network.sender import UdpSender
from app.protocol.config import get_default_config
from app.protocol.constants import FrameType, ProtocolType, TransferStatus
from app.protocol.frame import DataFrame
from app.transfer.coordinator import (
    TransferCoordinator,
    create_arq_receiver,
    create_arq_sender,
)
from app.transfer.models import Transfer


@pytest.fixture
def temp_dir() -> str:
    with tempfile.TemporaryDirectory() as d:
        yield d


# ---------------------------------------------------------------------------
# Requirement 1: Small File Transfer (< 1024 B, single chunk)
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_small_file_transfer(temp_dir: str) -> None:
    """Single-chunk small file (< 1024 B) transfers and reconstructs cleanly."""
    sender_fm = FileManager(storage_dir=os.path.join(temp_dir, "sender"))
    receiver_fm = FileManager(storage_dir=os.path.join(temp_dir, "receiver"))

    src_path = os.path.join(temp_dir, "small.txt")
    content = b"Small file payload under 1024 bytes for PeerShare test."
    with open(src_path, "wb") as f:
        f.write(content)

    meta = sender_fm.register_file(src_path)
    assert meta.file_size == len(content)
    assert meta.total_frames == 1

    session_id = uuid.uuid4()
    transfer_id = uuid.uuid4()
    config = get_default_config(ProtocolType.STOP_AND_WAIT)
    config.timeout_ms = 150
    config.frame_delay_ms = 0

    sender_transfer = Transfer(
        transfer_id=transfer_id,
        session_id=session_id,
        file_id=meta.file_id,
        file_name=meta.file_name,
        file_size=meta.file_size,
        file_sha256=meta.sha256_hash,
        protocol=ProtocolType.STOP_AND_WAIT,
        configuration=config,
        total_frames=meta.total_frames,
    )

    receiver_transfer = Transfer(
        transfer_id=transfer_id,
        session_id=session_id,
        file_id=meta.file_id,
        file_name=meta.file_name,
        file_size=meta.file_size,
        file_sha256=meta.sha256_hash,
        protocol=ProtocolType.STOP_AND_WAIT,
        configuration=config,
        total_frames=meta.total_frames,
    )

    sender_coord = TransferCoordinator(sender_fm)
    receiver_coord = TransferCoordinator(receiver_fm)

    ready_event = asyncio.Event()
    rx_task = asyncio.create_task(
        receiver_coord.run_receiver_transfer(
            receiver_transfer,
            ready_event=ready_event,
            timeout=3.0,
        )
    )
    await ready_event.wait()

    tx_ok = await sender_coord.run_sender_transfer(
        sender_transfer,
        peer_udp_host="127.0.0.1",
        peer_udp_port=receiver_transfer.local_udp_port,
        timeout=3.0,
    )
    rx_ok, saved_path = await rx_task

    assert tx_ok is True
    assert rx_ok is True
    assert sender_transfer.status == TransferStatus.COMPLETED
    assert receiver_transfer.status == TransferStatus.COMPLETED
    assert saved_path is not None
    assert os.path.exists(saved_path)
    assert calculate_sha256(saved_path) == meta.sha256_hash
    with open(saved_path, "rb") as f:
        assert f.read() == content


# ---------------------------------------------------------------------------
# Requirement 2: Maximum Permitted File Size (5 MB Boundary & Rejection)
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_maximum_permitted_file_size(temp_dir: str) -> None:
    """Exact 5 MB file transfers and verifies; file > 5 MB is rejected."""
    fm = FileManager(storage_dir=temp_dir)

    # 1. Reject file exceeding 5 MB limit
    oversized = os.path.join(temp_dir, "oversized.bin")
    with open(oversized, "wb") as f:
        f.seek(MAX_FILE_SIZE + 10)
        f.write(b"\x00")

    with pytest.raises(FileTooLargeError):
        fm.register_file(oversized)

    # 2. Accept and transfer exact 5 MB file (5,242,880 bytes -> 5120 frames)
    exact_5mb = os.path.join(temp_dir, "exact_5mb.bin")
    payload = os.urandom(MAX_FILE_SIZE)
    with open(exact_5mb, "wb") as f:
        f.write(payload)

    meta = fm.register_file(exact_5mb)
    assert meta.file_size == MAX_FILE_SIZE
    assert meta.total_frames == 5120

    session_id = uuid.uuid4()
    transfer_id = uuid.uuid4()
    config = get_default_config(ProtocolType.SELECTIVE_REPEAT)
    config.sender_window_size = 16
    config.receiver_window_size = 16
    config.timeout_ms = 200
    config.frame_delay_ms = 0

    arq_rx = create_arq_receiver(ProtocolType.SELECTIVE_REPEAT, session_id, transfer_id, config, meta.total_frames)
    udp_rx = UdpReceiver(arq_receiver=arq_rx, host="127.0.0.1", port=0)
    await udp_rx.start()

    chunks = fm.get_chunks(meta.file_id)
    arq_tx = create_arq_sender(ProtocolType.SELECTIVE_REPEAT, session_id, transfer_id, config, chunks)
    udp_tx = UdpSender(peer_host="127.0.0.1", peer_port=udp_rx.local_port, arq_sender=arq_tx)
    await udp_tx.start()

    tx_ok = await udp_tx.wait_complete(timeout=10.0)
    rx_ok = await udp_rx.wait_complete(timeout=5.0)

    assert tx_ok is True
    assert rx_ok is True

    reconstructed = arq_rx.get_reconstructed_data()
    assert len(reconstructed) == MAX_FILE_SIZE
    saved_path, verified = fm.save_reconstructed_file("verified_5mb.bin", reconstructed, meta.sha256_hash)
    assert verified is True
    assert calculate_sha256(saved_path) == meta.sha256_hash

    await udp_tx.close()
    await udp_rx.close()


# ---------------------------------------------------------------------------
# Requirement 3: Empty File Transfer (0 Bytes, 0 Frames)
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_empty_file_transfer(temp_dir: str) -> None:
    """Empty 0-byte file transmits via FIN/FIN-ACK handshake and reconstructs cleanly."""
    sender_fm = FileManager(storage_dir=os.path.join(temp_dir, "sender"))
    receiver_fm = FileManager(storage_dir=os.path.join(temp_dir, "receiver"))

    empty_path = os.path.join(temp_dir, "empty.txt")
    with open(empty_path, "wb"):
        pass

    meta = sender_fm.register_file(empty_path)
    assert meta.file_size == 0
    assert meta.total_frames == 0
    expected_empty_hash = hashlib.sha256(b"").hexdigest()
    assert meta.sha256_hash == expected_empty_hash

    session_id = uuid.uuid4()
    transfer_id = uuid.uuid4()
    config = get_default_config(ProtocolType.STOP_AND_WAIT)
    config.timeout_ms = 150
    config.frame_delay_ms = 0

    sender_transfer = Transfer(
        transfer_id=transfer_id,
        session_id=session_id,
        file_id=meta.file_id,
        file_name=meta.file_name,
        file_size=0,
        file_sha256=meta.sha256_hash,
        protocol=ProtocolType.STOP_AND_WAIT,
        configuration=config,
        total_frames=0,
    )

    receiver_transfer = Transfer(
        transfer_id=transfer_id,
        session_id=session_id,
        file_id=meta.file_id,
        file_name=meta.file_name,
        file_size=0,
        file_sha256=meta.sha256_hash,
        protocol=ProtocolType.STOP_AND_WAIT,
        configuration=config,
        total_frames=0,
    )

    sender_coord = TransferCoordinator(sender_fm)
    receiver_coord = TransferCoordinator(receiver_fm)

    ready_event = asyncio.Event()
    rx_task = asyncio.create_task(
        receiver_coord.run_receiver_transfer(receiver_transfer, ready_event=ready_event, timeout=3.0)
    )
    await ready_event.wait()

    tx_ok = await sender_coord.run_sender_transfer(
        sender_transfer,
        peer_udp_host="127.0.0.1",
        peer_udp_port=receiver_transfer.local_udp_port,
        timeout=3.0,
    )
    rx_ok, saved_path = await rx_task

    assert tx_ok is True
    assert rx_ok is True
    assert saved_path is not None
    assert os.path.getsize(saved_path) == 0
    assert calculate_sha256(saved_path) == expected_empty_hash


# ---------------------------------------------------------------------------
# Requirement 4: All Three ARQ Protocols Over Real UDP
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
@pytest.mark.parametrize("protocol", [
    ProtocolType.STOP_AND_WAIT,
    ProtocolType.GO_BACK_N,
    ProtocolType.SELECTIVE_REPEAT,
])
async def test_full_file_transfer_over_udp_all_protocols(temp_dir: str, protocol: ProtocolType) -> None:
    """Full file transfer over UDP with SHA-256 verification across all 3 ARQ engines."""
    sender_fm = FileManager(storage_dir=os.path.join(temp_dir, "sender"))
    receiver_fm = FileManager(storage_dir=os.path.join(temp_dir, "receiver"))

    src_path = os.path.join(temp_dir, f"source_{protocol.value}.bin")
    content = os.urandom(3500)  # 4 chunks (1024, 1024, 1024, 428)
    with open(src_path, "wb") as f:
        f.write(content)

    meta = sender_fm.register_file(src_path)
    assert meta.total_frames == 4

    session_id = uuid.uuid4()
    transfer_id = uuid.uuid4()
    config = get_default_config(protocol)
    config.timeout_ms = 150
    config.frame_delay_ms = 0

    sender_transfer = Transfer(
        transfer_id=transfer_id,
        session_id=session_id,
        file_id=meta.file_id,
        file_name=meta.file_name,
        file_size=meta.file_size,
        file_sha256=meta.sha256_hash,
        protocol=protocol,
        configuration=config,
        total_frames=meta.total_frames,
    )

    receiver_transfer = Transfer(
        transfer_id=transfer_id,
        session_id=session_id,
        file_id=meta.file_id,
        file_name=meta.file_name,
        file_size=meta.file_size,
        file_sha256=meta.sha256_hash,
        protocol=protocol,
        configuration=config,
        total_frames=meta.total_frames,
    )

    sender_coord = TransferCoordinator(sender_fm)
    receiver_coord = TransferCoordinator(receiver_fm)

    ready_event = asyncio.Event()
    rx_task = asyncio.create_task(
        receiver_coord.run_receiver_transfer(receiver_transfer, ready_event=ready_event, timeout=4.0)
    )
    await ready_event.wait()

    tx_ok = await sender_coord.run_sender_transfer(
        sender_transfer,
        peer_udp_host="127.0.0.1",
        peer_udp_port=receiver_transfer.local_udp_port,
        timeout=4.0,
    )
    rx_ok, saved_path = await rx_task

    assert tx_ok is True
    assert rx_ok is True
    assert saved_path is not None
    assert calculate_sha256(saved_path) == meta.sha256_hash
    assert sender_transfer.stats is not None
    assert receiver_transfer.stats is not None
    assert sender_transfer.stats.total_frames == 4
    assert receiver_transfer.stats.unique_frames_received == 4


# ---------------------------------------------------------------------------
# Requirement 5: Packet Loss Simulation and Recovery
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_packet_loss_simulation_and_recovery(temp_dir: str) -> None:
    """Deterministic seeded 15% packet loss on data frames is recovered via ARQ retransmission."""
    sender_fm = FileManager(storage_dir=os.path.join(temp_dir, "sender"))
    receiver_fm = FileManager(storage_dir=os.path.join(temp_dir, "receiver"))

    src_path = os.path.join(temp_dir, "loss_test.bin")
    content = os.urandom(4096)  # 4 chunks
    with open(src_path, "wb") as f:
        f.write(content)

    meta = sender_fm.register_file(src_path)

    session_id = uuid.uuid4()
    transfer_id = uuid.uuid4()
    config = get_default_config(ProtocolType.SELECTIVE_REPEAT)
    config.timeout_ms = 100
    config.frame_delay_ms = 0
    config.max_retries = 10

    # Seeded loss simulator dropping data frames
    loss_sim = PacketLossSimulator(loss_percentage=20.0, seed=123)

    sender_transfer = Transfer(
        transfer_id=transfer_id,
        session_id=session_id,
        file_id=meta.file_id,
        file_name=meta.file_name,
        file_size=meta.file_size,
        file_sha256=meta.sha256_hash,
        protocol=ProtocolType.SELECTIVE_REPEAT,
        configuration=config,
        total_frames=meta.total_frames,
    )

    receiver_transfer = Transfer(
        transfer_id=transfer_id,
        session_id=session_id,
        file_id=meta.file_id,
        file_name=meta.file_name,
        file_size=meta.file_size,
        file_sha256=meta.sha256_hash,
        protocol=ProtocolType.SELECTIVE_REPEAT,
        configuration=config,
        total_frames=meta.total_frames,
    )

    sender_coord = TransferCoordinator(sender_fm)
    receiver_coord = TransferCoordinator(receiver_fm)

    ready_event = asyncio.Event()
    rx_task = asyncio.create_task(
        receiver_coord.run_receiver_transfer(receiver_transfer, ready_event=ready_event, timeout=5.0)
    )
    await ready_event.wait()

    tx_ok = await sender_coord.run_sender_transfer(
        sender_transfer,
        peer_udp_host="127.0.0.1",
        peer_udp_port=receiver_transfer.local_udp_port,
        loss_simulator=loss_sim,
        timeout=5.0,
    )
    rx_ok, saved_path = await rx_task

    assert tx_ok is True
    assert rx_ok is True
    assert saved_path is not None
    assert calculate_sha256(saved_path) == meta.sha256_hash
    # Retransmissions or dropped frames occurred
    assert sender_transfer.stats.dropped_data_frames > 0 or sender_transfer.stats.total_retransmissions > 0


# ---------------------------------------------------------------------------
# Requirement 6: ACK Loss and Retransmission
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_ack_loss_and_retransmission(temp_dir: str) -> None:
    """Dropped ACK datagram causes sender timeout and successful retransmission."""
    sender_fm = FileManager(storage_dir=os.path.join(temp_dir, "sender"))
    receiver_fm = FileManager(storage_dir=os.path.join(temp_dir, "receiver"))

    src_path = os.path.join(temp_dir, "ack_loss.bin")
    content = os.urandom(3000)  # 3 chunks
    with open(src_path, "wb") as f:
        f.write(content)

    meta = sender_fm.register_file(src_path)

    session_id = uuid.uuid4()
    transfer_id = uuid.uuid4()
    config = get_default_config(ProtocolType.STOP_AND_WAIT)
    config.timeout_ms = 100
    config.frame_delay_ms = 0

    # Deterministically drop ACK for frame_index 1 once
    ack_loss_sim = PacketLossSimulator(drop_indices={1})

    sender_transfer = Transfer(
        transfer_id=transfer_id,
        session_id=session_id,
        file_id=meta.file_id,
        file_name=meta.file_name,
        file_size=meta.file_size,
        file_sha256=meta.sha256_hash,
        protocol=ProtocolType.STOP_AND_WAIT,
        configuration=config,
        total_frames=meta.total_frames,
    )

    receiver_transfer = Transfer(
        transfer_id=transfer_id,
        session_id=session_id,
        file_id=meta.file_id,
        file_name=meta.file_name,
        file_size=meta.file_size,
        file_sha256=meta.sha256_hash,
        protocol=ProtocolType.STOP_AND_WAIT,
        configuration=config,
        total_frames=meta.total_frames,
    )

    sender_coord = TransferCoordinator(sender_fm)
    receiver_coord = TransferCoordinator(receiver_fm)

    ready_event = asyncio.Event()
    rx_task = asyncio.create_task(
        receiver_coord.run_receiver_transfer(
            receiver_transfer,
            loss_simulator=ack_loss_sim,
            ready_event=ready_event,
            timeout=4.0,
        )
    )
    await ready_event.wait()

    tx_ok = await sender_coord.run_sender_transfer(
        sender_transfer,
        peer_udp_host="127.0.0.1",
        peer_udp_port=receiver_transfer.local_udp_port,
        timeout=4.0,
    )
    rx_ok, saved_path = await rx_task

    assert tx_ok is True
    assert rx_ok is True
    assert saved_path is not None
    assert calculate_sha256(saved_path) == meta.sha256_hash
    # Retransmissions occurred because of lost ACK
    assert sender_transfer.stats.total_retransmissions >= 1
    assert receiver_transfer.stats.dropped_ack_frames >= 1


# ---------------------------------------------------------------------------
# Requirement 7: Out-of-Order Frame Delivery and Selective Repeat Buffering
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_out_of_order_frame_delivery_selective_repeat(temp_dir: str) -> None:
    """Selective Repeat receiver buffers out-of-order frames and reassembles them in order."""
    session_id = uuid.uuid4()
    transfer_id = uuid.uuid4()
    config = get_default_config(ProtocolType.SELECTIVE_REPEAT)
    config.receiver_window_size = 4

    chunks = [f"Payload chunk {i}".encode().ljust(100, b"x") for i in range(4)]
    full_data = b"".join(chunks)
    expected_sha = hashlib.sha256(full_data).hexdigest()

    from app.protocol.selective_repeat import SelectiveRepeatReceiver
    arq_rx = SelectiveRepeatReceiver(session_id, transfer_id, config, total_frames=4)

    now = time.monotonic()
    # Receive frame 1 first (out of order, expecting 0)
    frame_1 = DataFrame(session_id, transfer_id, sequence_number=1, frame_index=1, payload=chunks[1])
    ack_1 = arq_rx.handle_data_frame(frame_1, now)
    assert ack_1 is not None
    assert ack_1.frame_index == 1
    assert arq_rx.stats.buffered_frames == 1
    assert 1 in arq_rx.buffered_frames

    # Receive frame 2 next (also out of order)
    frame_2 = DataFrame(session_id, transfer_id, sequence_number=2, frame_index=2, payload=chunks[2])
    ack_2 = arq_rx.handle_data_frame(frame_2, now)
    assert ack_2 is not None
    assert arq_rx.stats.buffered_frames == 2

    # Receive missing frame 0 (in-order base frame)
    frame_0 = DataFrame(session_id, transfer_id, sequence_number=0, frame_index=0, payload=chunks[0])
    ack_0 = arq_rx.handle_data_frame(frame_0, now)
    assert ack_0 is not None
    # Base window slides past 0, 1, 2
    assert arq_rx.base_frame_index == 3

    # Receive frame 3
    frame_3 = DataFrame(session_id, transfer_id, sequence_number=3, frame_index=3, payload=chunks[3])
    arq_rx.handle_data_frame(frame_3, now)
    assert arq_rx.base_frame_index == 4

    # FIN
    fin_frame = DataFrame(session_id, transfer_id, sequence_number=4, frame_index=4, payload=b"", frame_type=FrameType.FIN)
    fin_ack = arq_rx.handle_data_frame(fin_frame, now)
    assert fin_ack is not None
    assert fin_ack.frame_type == FrameType.FIN_ACK
    assert arq_rx.status == TransferStatus.COMPLETED

    reconstructed = arq_rx.get_reconstructed_data()
    assert reconstructed == full_data
    assert hashlib.sha256(reconstructed).hexdigest() == expected_sha


# ---------------------------------------------------------------------------
# Requirement 8: Duplicate Frame Handling
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_duplicate_frame_handling(temp_dir: str) -> None:
    """Duplicate received frame is acknowledged, recorded in stats, and not duplicated in payload."""
    session_id = uuid.uuid4()
    transfer_id = uuid.uuid4()
    config = get_default_config(ProtocolType.STOP_AND_WAIT)

    from app.protocol.stop_and_wait import StopAndWaitReceiver
    arq_rx = StopAndWaitReceiver(session_id, transfer_id, config, total_frames=2)

    now = time.monotonic()
    frame_0 = DataFrame(session_id, transfer_id, sequence_number=0, frame_index=0, payload=b"CHUNK_0")

    # Send frame 0 first time
    ack1 = arq_rx.handle_data_frame(frame_0, now)
    assert ack1 is not None
    assert ack1.frame_index == 0
    assert arq_rx.stats.unique_frames_received == 1

    # Send duplicate frame 0
    ack2 = arq_rx.handle_data_frame(frame_0, now)
    assert ack2 is not None
    assert ack2.frame_index == 0
    assert arq_rx.stats.discarded_frames == 1
    assert arq_rx.stats.unique_frames_received == 1

    # Send frame 1
    frame_1 = DataFrame(session_id, transfer_id, sequence_number=1, frame_index=1, payload=b"CHUNK_1")
    arq_rx.handle_data_frame(frame_1, now)

    # Reconstructed data only contains single copy of chunk 0
    assert arq_rx.get_reconstructed_data() == b"CHUNK_0CHUNK_1"


# ---------------------------------------------------------------------------
# Requirement 9: File Reconstruction and Collision Avoidance
# ---------------------------------------------------------------------------
def test_file_reconstruction_and_collision_avoidance(temp_dir: str) -> None:
    """Saving reconstructed file, avoiding filename collisions, and verifying SHA-256."""
    fm = FileManager(storage_dir=temp_dir)
    data = b"Sample peer transfer data for integrity check"
    expected_sha = hashlib.sha256(data).hexdigest()

    path1, verified1 = fm.save_reconstructed_file("report.txt", data, expected_sha)
    assert verified1 is True
    assert os.path.basename(path1) == "report.txt"

    # Second file with same name triggers collision avoidance (_1)
    path2, verified2 = fm.save_reconstructed_file("report.txt", data, expected_sha)
    assert verified2 is True
    assert os.path.basename(path2) == "report_1.txt"

    # Third file with same name triggers collision avoidance (_2)
    path3, verified3 = fm.save_reconstructed_file("report.txt", data, expected_sha)
    assert verified3 is True
    assert os.path.basename(path3) == "report_2.txt"


# ---------------------------------------------------------------------------
# Requirement 10: SHA-256 Verification and Corrupted File Handling
# ---------------------------------------------------------------------------
def test_sha256_verification_and_corrupted_file_cleanup(temp_dir: str) -> None:
    """Corrupted expected hash raises IntegrityVerificationError and deletes failed file."""
    fm = FileManager(storage_dir=temp_dir)
    data = b"Legitimate file content"
    mismatched_sha = "ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff"

    target_file = os.path.join(temp_dir, "corrupt.dat")
    with pytest.raises(IntegrityVerificationError):
        fm.save_reconstructed_file("corrupt.dat", data, mismatched_sha)

    # Failed file must be removed from destination directory
    assert not os.path.exists(target_file)


# ---------------------------------------------------------------------------
# Requirement 11: Interrupted Transfer (Timeout & Max Retries)
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_interrupted_transfer_sender_and_receiver_timeout(temp_dir: str) -> None:
    """Sender reaches max retries to unreachable peer; receiver times out waiting for frames."""
    fm = FileManager(storage_dir=temp_dir)
    src_path = os.path.join(temp_dir, "abort.bin")
    with open(src_path, "wb") as f:
        f.write(b"data to transmit to nowhere")
    meta = fm.register_file(src_path)

    coord = TransferCoordinator(fm)
    config = get_default_config(ProtocolType.STOP_AND_WAIT)
    config.timeout_ms = 40
    config.max_retries = 2

    session_id = uuid.uuid4()
    transfer_id = uuid.uuid4()

    # 1. Sender fails when transmitting to closed port
    sender_transfer = Transfer(
        transfer_id=transfer_id,
        session_id=session_id,
        file_id=meta.file_id,
        file_name=meta.file_name,
        file_size=meta.file_size,
        file_sha256=meta.sha256_hash,
        protocol=ProtocolType.STOP_AND_WAIT,
        configuration=config,
        total_frames=meta.total_frames,
    )

    # Port 1 is reserved and unassigned
    tx_ok = await coord.run_sender_transfer(
        sender_transfer,
        peer_udp_host="127.0.0.1",
        peer_udp_port=1,
        timeout=1.0,
    )
    assert tx_ok is False
    assert sender_transfer.status == TransferStatus.FAILED
    assert "retry limit" in sender_transfer.failure_reason.lower() or "timeout" in sender_transfer.failure_reason.lower()

    # 2. Receiver fails when no frames arrive
    receiver_transfer = Transfer(
        transfer_id=uuid.uuid4(),
        session_id=session_id,
        file_id=meta.file_id,
        file_name="rx_timeout.bin",
        file_size=meta.file_size,
        file_sha256=meta.sha256_hash,
        protocol=ProtocolType.STOP_AND_WAIT,
        configuration=config,
        total_frames=meta.total_frames,
    )
    rx_ok, _ = await coord.run_receiver_transfer(receiver_transfer, timeout=0.1)
    assert rx_ok is False
    assert receiver_transfer.status == TransferStatus.FAILED
    assert "timed out" in receiver_transfer.failure_reason.lower()


# ---------------------------------------------------------------------------
# Requirement 12: Invalid Filename and Path Traversal Attempts
# ---------------------------------------------------------------------------
def test_invalid_filename_and_path_traversal(temp_dir: str) -> None:
    """Directory traversal sequences and invalid characters are rejected or neutralized."""
    # 1. Direct path traversal validation
    with pytest.raises(InvalidFilenameError):
        validate_filename("../../etc/passwd")

    with pytest.raises(InvalidFilenameError):
        validate_filename("/root/secret.key")

    with pytest.raises(InvalidFilenameError):
        validate_filename("..\\..\\windows\\system32\\calc.exe")

    # 2. Saving with traversal attempt raises InvalidFilenameError
    fm = FileManager(storage_dir=temp_dir)
    with pytest.raises(InvalidFilenameError):
        fm.save_reconstructed_file("../../malicious.sh", b"evil", "any_hash")

    # 3. Sanitizer strips unsafe characters and path components
    assert sanitize_filename("../../etc/passwd") == "passwd"
    assert sanitize_filename("..\\..\\windows\\system32\\calc.exe") == "calc.exe"
    assert sanitize_filename("normal_file.pdf") == "normal_file.pdf"
    assert sanitize_filename("invalid:chars*in?name.txt") == "invalidcharsinname.txt"
    assert sanitize_filename("") == "unnamed_file"


# ---------------------------------------------------------------------------
# Requirement 13: Insufficient Disk Space Handling
# ---------------------------------------------------------------------------
def test_insufficient_disk_space_handling(temp_dir: str, monkeypatch: pytest.MonkeyPatch) -> None:
    """Attempting to save reconstructed file when free disk space is insufficient raises error."""
    fm = FileManager(storage_dir=temp_dir)
    data = os.urandom(5000)
    data_hash = hashlib.sha256(data).hexdigest()

    # Mock shutil.disk_usage to return 100 bytes free space
    class MockDiskUsage:
        total = 10**9
        used = 10**9 - 100
        free = 100

    monkeypatch.setattr(shutil, "disk_usage", lambda _: MockDiskUsage())

    with pytest.raises(InsufficientDiskSpaceError):
        fm.save_reconstructed_file("large.bin", data, data_hash)


# ---------------------------------------------------------------------------
# Requirement 14: Lost FIN-ACK and Receiver Linger Recovery
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_lost_fin_ack_and_linger_recovery(temp_dir: str) -> None:
    """First FIN-ACK is dropped; lingering receiver re-sends FIN-ACK upon duplicate FIN."""
    sender_fm = FileManager(storage_dir=os.path.join(temp_dir, "sender"))
    receiver_fm = FileManager(storage_dir=os.path.join(temp_dir, "receiver"))

    src_path = os.path.join(temp_dir, "linger_test.bin")
    content = b"Content for testing lost FIN-ACK recovery."
    with open(src_path, "wb") as f:
        f.write(content)

    meta = sender_fm.register_file(src_path)

    session_id = uuid.uuid4()
    transfer_id = uuid.uuid4()
    config = get_default_config(ProtocolType.STOP_AND_WAIT)
    config.timeout_ms = 100  # Quick sender timeout
    config.frame_delay_ms = 0

    # FIN frame_index is meta.total_frames (1). Drop the first FIN-ACK
    fin_drop_sim = PacketLossSimulator(drop_indices={meta.total_frames})

    sender_transfer = Transfer(
        transfer_id=transfer_id,
        session_id=session_id,
        file_id=meta.file_id,
        file_name=meta.file_name,
        file_size=meta.file_size,
        file_sha256=meta.sha256_hash,
        protocol=ProtocolType.STOP_AND_WAIT,
        configuration=config,
        total_frames=meta.total_frames,
    )

    receiver_transfer = Transfer(
        transfer_id=transfer_id,
        session_id=session_id,
        file_id=meta.file_id,
        file_name=meta.file_name,
        file_size=meta.file_size,
        file_sha256=meta.sha256_hash,
        protocol=ProtocolType.STOP_AND_WAIT,
        configuration=config,
        total_frames=meta.total_frames,
    )

    sender_coord = TransferCoordinator(sender_fm)
    receiver_coord = TransferCoordinator(receiver_fm)

    ready_event = asyncio.Event()
    # Receiver lingers for 0.4s (4x timeout) after completion
    rx_task = asyncio.create_task(
        receiver_coord.run_receiver_transfer(
            receiver_transfer,
            loss_simulator=fin_drop_sim,
            linger_seconds=0.4,
            ready_event=ready_event,
            timeout=4.0,
        )
    )
    await ready_event.wait()

    tx_ok = await sender_coord.run_sender_transfer(
        sender_transfer,
        peer_udp_host="127.0.0.1",
        peer_udp_port=receiver_transfer.local_udp_port,
        timeout=4.0,
    )
    rx_ok, saved_path = await rx_task

    assert tx_ok is True
    assert rx_ok is True
    assert sender_transfer.status == TransferStatus.COMPLETED
    assert receiver_transfer.status == TransferStatus.COMPLETED
    assert saved_path is not None
    assert calculate_sha256(saved_path) == meta.sha256_hash


# ---------------------------------------------------------------------------
# Multi-Process Integration Test
# ---------------------------------------------------------------------------
def _run_receiver_process_task(
    dest_dir: str,
    session_id: uuid.UUID,
    transfer_id: uuid.UUID,
    file_name: str,
    file_size: int,
    file_sha256: str,
    total_frames: int,
    protocol: ProtocolType,
    port_queue: mp.Queue,
    result_queue: mp.Queue,
) -> None:
    """Target function executed in an independent operating system process."""
    async def _runner() -> None:
        receiver_fm = FileManager(storage_dir=dest_dir)
        coord = TransferCoordinator(receiver_fm)
        config = get_default_config(protocol)
        config.timeout_ms = 150
        config.frame_delay_ms = 0

        transfer = Transfer(
            transfer_id=transfer_id,
            session_id=session_id,
            file_id=uuid.uuid4(),
            file_name=file_name,
            file_size=file_size,
            file_sha256=file_sha256,
            protocol=protocol,
            configuration=config,
            total_frames=total_frames,
        )

        ready_event = asyncio.Event()
        rx_task = asyncio.create_task(
            coord.run_receiver_transfer(
                transfer,
                ready_event=ready_event,
                dest_dir=dest_dir,
                timeout=6.0,
            )
        )
        await ready_event.wait()
        port_queue.put(transfer.local_udp_port)

        success, saved_path = await rx_task
        result_queue.put({
            "success": success,
            "status": transfer.status.value,
            "saved_path": saved_path,
            "integrity_verified": transfer.integrity_verified,
            "file_exists": os.path.exists(saved_path) if saved_path else False,
            "sha256": calculate_sha256(saved_path) if saved_path and os.path.exists(saved_path) else None,
        })

    asyncio.run(_runner())


@pytest.mark.asyncio
async def test_multi_process_file_transfer(temp_dir: str) -> None:
    """End-to-end file transfer between two independent OS processes using TransferCoordinator."""
    sender_dir = os.path.join(temp_dir, "sender_proc")
    receiver_dir = os.path.join(temp_dir, "receiver_proc")
    os.makedirs(sender_dir, exist_ok=True)
    os.makedirs(receiver_dir, exist_ok=True)

    sender_fm = FileManager(storage_dir=sender_dir)

    # 4 KB multi-chunk file
    src_file = os.path.join(sender_dir, "multiprocess_test.dat")
    payload = os.urandom(4096)
    with open(src_file, "wb") as f:
        f.write(payload)

    meta = sender_fm.register_file(src_file)

    session_id = uuid.uuid4()
    transfer_id = uuid.uuid4()
    protocol = ProtocolType.SELECTIVE_REPEAT
    config = get_default_config(protocol)
    config.timeout_ms = 150
    config.frame_delay_ms = 0

    ctx = mp.get_context("spawn")
    port_queue = ctx.Queue()
    result_queue = ctx.Queue()

    # Launch Receiver in independent child OS process
    proc = ctx.Process(
        target=_run_receiver_process_task,
        args=(
            receiver_dir,
            session_id,
            transfer_id,
            meta.file_name,
            meta.file_size,
            meta.sha256_hash,
            meta.total_frames,
            protocol,
            port_queue,
            result_queue,
        ),
    )
    proc.start()

    try:
        # Await ephemeral UDP port reported by receiver process
        receiver_port = await asyncio.to_thread(port_queue.get, timeout=5.0)
        assert receiver_port > 0

        # Execute sender transfer in this process
        sender_transfer = Transfer(
            transfer_id=transfer_id,
            session_id=session_id,
            file_id=meta.file_id,
            file_name=meta.file_name,
            file_size=meta.file_size,
            file_sha256=meta.sha256_hash,
            protocol=protocol,
            configuration=config,
            total_frames=meta.total_frames,
        )
        sender_coord = TransferCoordinator(sender_fm)

        tx_ok = await sender_coord.run_sender_transfer(
            sender_transfer,
            peer_udp_host="127.0.0.1",
            peer_udp_port=receiver_port,
            timeout=5.0,
        )
        assert tx_ok is True
        assert sender_transfer.status == TransferStatus.COMPLETED

        # Retrieve result from child process
        rx_result = await asyncio.to_thread(result_queue.get, timeout=5.0)
        assert rx_result["success"] is True
        assert rx_result["status"] == TransferStatus.COMPLETED.value
        assert rx_result["integrity_verified"] is True
        assert rx_result["file_exists"] is True
        assert rx_result["sha256"] == meta.sha256_hash

    finally:
        proc.join(timeout=3.0)
        if proc.is_alive():
            proc.terminate()
