"""Integration tests for all three ARQ protocols over real asynchronous UDP sockets."""

import asyncio
import time
import uuid
import pytest

from app.protocol.config import get_default_config
from app.protocol.constants import ProtocolType, TransferStatus
from app.protocol.go_back_n import GoBackNReceiver, GoBackNSender
from app.protocol.selective_repeat import SelectiveRepeatReceiver, SelectiveRepeatSender
from app.protocol.stop_and_wait import StopAndWaitReceiver, StopAndWaitSender
from app.network.loss import PacketLossSimulator
from app.network.receiver import UdpReceiver
from app.network.sender import UdpSender


@pytest.fixture
def session_and_transfer_ids() -> tuple[uuid.UUID, uuid.UUID]:
    return uuid.uuid4(), uuid.uuid4()


# ---------------------------------------------------------------------------
# Stop-and-Wait over UDP
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_udp_stop_and_wait_clean(session_and_transfer_ids: tuple[uuid.UUID, uuid.UUID]) -> None:
    """Stop-and-Wait transfer over real UDP with zero loss."""
    session_id, transfer_id = session_and_transfer_ids
    config = get_default_config(ProtocolType.STOP_AND_WAIT)
    config.timeout_ms = 150
    config.frame_delay_ms = 0

    chunks = [f"StopAndWait UDP chunk {i}".encode() for i in range(8)]

    arq_receiver = StopAndWaitReceiver(session_id, transfer_id, config, len(chunks))
    udp_receiver = UdpReceiver(arq_receiver=arq_receiver, host="127.0.0.1", port=0)
    await udp_receiver.start()

    arq_sender = StopAndWaitSender(session_id, transfer_id, config, chunks)
    udp_sender = UdpSender(
        peer_host="127.0.0.1",
        peer_port=udp_receiver.local_port,
        arq_sender=arq_sender,
    )
    await udp_sender.start()

    success = await udp_sender.wait_complete(timeout=5.0)
    assert success is True
    assert arq_sender.status == TransferStatus.COMPLETED

    recv_success = await udp_receiver.wait_complete(timeout=2.0)
    assert recv_success is True
    assert arq_receiver.get_reconstructed_data() == b"".join(chunks)
    assert arq_sender.stats.total_retransmissions == 0

    await udp_sender.close()
    await udp_receiver.close()


@pytest.mark.asyncio
async def test_udp_stop_and_wait_data_loss(session_and_transfer_ids: tuple[uuid.UUID, uuid.UUID]) -> None:
    """Stop-and-Wait recovers from a dropped data frame over UDP."""
    session_id, transfer_id = session_and_transfer_ids
    config = get_default_config(ProtocolType.STOP_AND_WAIT)
    config.timeout_ms = 100
    config.frame_delay_ms = 0

    chunks = [b"Chunk 0", b"Chunk 1", b"Chunk 2"]
    arq_receiver = StopAndWaitReceiver(session_id, transfer_id, config, len(chunks))
    udp_receiver = UdpReceiver(arq_receiver=arq_receiver, host="127.0.0.1", port=0)
    await udp_receiver.start()

    # Drop data frame index 1 once
    sender_loss = PacketLossSimulator(loss_percentage=0.0, drop_indices={1})
    arq_sender = StopAndWaitSender(session_id, transfer_id, config, chunks)
    udp_sender = UdpSender(
        peer_host="127.0.0.1",
        peer_port=udp_receiver.local_port,
        arq_sender=arq_sender,
        loss_simulator=sender_loss,
    )
    await udp_sender.start()

    success = await udp_sender.wait_complete(timeout=5.0)
    assert success is True
    await udp_receiver.wait_complete(timeout=2.0)

    assert arq_receiver.get_reconstructed_data() == b"".join(chunks)
    assert arq_sender.stats.total_retransmissions == 1

    await udp_sender.close()
    await udp_receiver.close()


@pytest.mark.asyncio
async def test_udp_stop_and_wait_ack_loss(session_and_transfer_ids: tuple[uuid.UUID, uuid.UUID]) -> None:
    """Stop-and-Wait recovers from a dropped ACK frame over UDP."""
    session_id, transfer_id = session_and_transfer_ids
    config = get_default_config(ProtocolType.STOP_AND_WAIT)
    config.timeout_ms = 100
    config.frame_delay_ms = 0

    chunks = [b"Chunk 0", b"Chunk 1"]
    # Receiver drops ACK for frame index 0
    receiver_loss = PacketLossSimulator(loss_percentage=0.0, drop_indices={0})
    arq_receiver = StopAndWaitReceiver(session_id, transfer_id, config, len(chunks))
    udp_receiver = UdpReceiver(
        arq_receiver=arq_receiver,
        host="127.0.0.1",
        port=0,
        loss_simulator=receiver_loss,
    )
    await udp_receiver.start()

    arq_sender = StopAndWaitSender(session_id, transfer_id, config, chunks)
    udp_sender = UdpSender(
        peer_host="127.0.0.1",
        peer_port=udp_receiver.local_port,
        arq_sender=arq_sender,
    )
    await udp_sender.start()

    success = await udp_sender.wait_complete(timeout=5.0)
    assert success is True
    await udp_receiver.wait_complete(timeout=2.0)

    assert arq_receiver.get_reconstructed_data() == b"".join(chunks)
    assert arq_sender.stats.total_retransmissions == 1
    assert arq_receiver.stats.discarded_frames >= 1

    await udp_sender.close()
    await udp_receiver.close()


@pytest.mark.asyncio
async def test_udp_stop_and_wait_corrupted_frame(session_and_transfer_ids: tuple[uuid.UUID, uuid.UUID]) -> None:
    """Receiver discards corrupted datagram (CRC failure), sender retransmits over UDP."""
    session_id, transfer_id = session_and_transfer_ids
    config = get_default_config(ProtocolType.STOP_AND_WAIT)
    config.timeout_ms = 100
    config.frame_delay_ms = 0

    chunks = [b"Payload 0", b"Payload 1"]
    arq_receiver = StopAndWaitReceiver(session_id, transfer_id, config, len(chunks))
    udp_receiver = UdpReceiver(arq_receiver=arq_receiver, host="127.0.0.1", port=0)
    await udp_receiver.start()

    # Corrupt frame index 0 on transmission
    arq_sender = StopAndWaitSender(session_id, transfer_id, config, chunks)
    udp_sender = UdpSender(
        peer_host="127.0.0.1",
        peer_port=udp_receiver.local_port,
        arq_sender=arq_sender,
        corrupt_indices={0},
    )
    await udp_sender.start()

    success = await udp_sender.wait_complete(timeout=5.0)
    assert success is True
    await udp_receiver.wait_complete(timeout=2.0)

    assert arq_receiver.get_reconstructed_data() == b"".join(chunks)
    assert arq_receiver.stats.corrupted_frames == 1
    assert arq_sender.stats.total_retransmissions == 1

    await udp_sender.close()
    await udp_receiver.close()


# ---------------------------------------------------------------------------
# Go-Back-N over UDP
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_udp_go_back_n_clean(session_and_transfer_ids: tuple[uuid.UUID, uuid.UUID]) -> None:
    """Go-Back-N transfer over real UDP with zero loss."""
    session_id, transfer_id = session_and_transfer_ids
    config = get_default_config(ProtocolType.GO_BACK_N)
    config.sender_window_size = 4
    config.timeout_ms = 150
    config.frame_delay_ms = 0

    chunks = [f"GBN UDP block {i}".encode() for i in range(12)]
    arq_receiver = GoBackNReceiver(session_id, transfer_id, config, len(chunks))
    udp_receiver = UdpReceiver(arq_receiver=arq_receiver, host="127.0.0.1", port=0)
    await udp_receiver.start()

    arq_sender = GoBackNSender(session_id, transfer_id, config, chunks)
    udp_sender = UdpSender(
        peer_host="127.0.0.1",
        peer_port=udp_receiver.local_port,
        arq_sender=arq_sender,
    )
    await udp_sender.start()

    success = await udp_sender.wait_complete(timeout=5.0)
    assert success is True
    await udp_receiver.wait_complete(timeout=2.0)

    assert arq_receiver.get_reconstructed_data() == b"".join(chunks)
    assert arq_sender.stats.total_retransmissions == 0

    await udp_sender.close()
    await udp_receiver.close()


@pytest.mark.asyncio
async def test_udp_go_back_n_data_loss(session_and_transfer_ids: tuple[uuid.UUID, uuid.UUID]) -> None:
    """Go-Back-N retransmits all outstanding frames when a data frame is lost."""
    session_id, transfer_id = session_and_transfer_ids
    config = get_default_config(ProtocolType.GO_BACK_N)
    config.sender_window_size = 4
    config.timeout_ms = 120
    config.frame_delay_ms = 0

    chunks = [b"GBN 0", b"GBN 1", b"GBN 2", b"GBN 3"]
    arq_receiver = GoBackNReceiver(session_id, transfer_id, config, len(chunks))
    udp_receiver = UdpReceiver(arq_receiver=arq_receiver, host="127.0.0.1", port=0)
    await udp_receiver.start()

    # Drop frame index 1
    sender_loss = PacketLossSimulator(loss_percentage=0.0, drop_indices={1})
    arq_sender = GoBackNSender(session_id, transfer_id, config, chunks)
    udp_sender = UdpSender(
        peer_host="127.0.0.1",
        peer_port=udp_receiver.local_port,
        arq_sender=arq_sender,
        loss_simulator=sender_loss,
    )
    await udp_sender.start()

    success = await udp_sender.wait_complete(timeout=5.0)
    assert success is True
    await udp_receiver.wait_complete(timeout=2.0)

    assert arq_receiver.get_reconstructed_data() == b"".join(chunks)
    assert arq_sender.stats.total_retransmissions >= 3  # Frames 1, 2, 3 retransmitted
    assert arq_receiver.stats.discarded_frames >= 2

    await udp_sender.close()
    await udp_receiver.close()


@pytest.mark.asyncio
async def test_udp_go_back_n_seeded_loss(session_and_transfer_ids: tuple[uuid.UUID, uuid.UUID]) -> None:
    """Go-Back-N succeeds under 15% packet loss with seeded PRNG."""
    session_id, transfer_id = session_and_transfer_ids
    config = get_default_config(ProtocolType.GO_BACK_N)
    config.sender_window_size = 4
    config.timeout_ms = 100
    config.max_retries = 15
    config.frame_delay_ms = 0

    chunks = [f"GBN loss test chunk {i}".encode() for i in range(16)]
    arq_receiver = GoBackNReceiver(session_id, transfer_id, config, len(chunks))
    udp_receiver = UdpReceiver(arq_receiver=arq_receiver, host="127.0.0.1", port=0)
    await udp_receiver.start()

    sender_loss = PacketLossSimulator(loss_percentage=15.0, seed=54321)
    arq_sender = GoBackNSender(session_id, transfer_id, config, chunks)
    udp_sender = UdpSender(
        peer_host="127.0.0.1",
        peer_port=udp_receiver.local_port,
        arq_sender=arq_sender,
        loss_simulator=sender_loss,
    )
    await udp_sender.start()

    success = await udp_sender.wait_complete(timeout=10.0)
    assert success is True
    await udp_receiver.wait_complete(timeout=3.0)

    assert arq_receiver.get_reconstructed_data() == b"".join(chunks)
    assert arq_sender.stats.total_retransmissions > 0

    await udp_sender.close()
    await udp_receiver.close()


# ---------------------------------------------------------------------------
# Selective Repeat over UDP
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_udp_selective_repeat_clean(session_and_transfer_ids: tuple[uuid.UUID, uuid.UUID]) -> None:
    """Selective Repeat transfer over real UDP with zero loss."""
    session_id, transfer_id = session_and_transfer_ids
    config = get_default_config(ProtocolType.SELECTIVE_REPEAT)
    config.sender_window_size = 4
    config.receiver_window_size = 4
    config.timeout_ms = 150
    config.frame_delay_ms = 0

    chunks = [f"Selective Repeat block {i}".encode() for i in range(12)]
    arq_receiver = SelectiveRepeatReceiver(session_id, transfer_id, config, len(chunks))
    udp_receiver = UdpReceiver(arq_receiver=arq_receiver, host="127.0.0.1", port=0)
    await udp_receiver.start()

    arq_sender = SelectiveRepeatSender(session_id, transfer_id, config, chunks)
    udp_sender = UdpSender(
        peer_host="127.0.0.1",
        peer_port=udp_receiver.local_port,
        arq_sender=arq_sender,
    )
    await udp_sender.start()

    success = await udp_sender.wait_complete(timeout=5.0)
    assert success is True
    await udp_receiver.wait_complete(timeout=2.0)

    assert arq_receiver.get_reconstructed_data() == b"".join(chunks)
    assert arq_sender.stats.total_retransmissions == 0

    await udp_sender.close()
    await udp_receiver.close()


@pytest.mark.asyncio
async def test_udp_selective_repeat_retransmits_only_lost_frame(
    session_and_transfer_ids: tuple[uuid.UUID, uuid.UUID]
) -> None:
    """Selective Repeat retransmits only the single lost frame, not the whole window."""
    session_id, transfer_id = session_and_transfer_ids
    config = get_default_config(ProtocolType.SELECTIVE_REPEAT)
    config.sender_window_size = 4
    config.receiver_window_size = 4
    config.timeout_ms = 100
    config.frame_delay_ms = 0

    chunks = [b"SR 0", b"SR 1", b"SR 2", b"SR 3"]
    arq_receiver = SelectiveRepeatReceiver(session_id, transfer_id, config, len(chunks))
    udp_receiver = UdpReceiver(arq_receiver=arq_receiver, host="127.0.0.1", port=0)
    await udp_receiver.start()

    # Drop frame index 1 once
    sender_loss = PacketLossSimulator(loss_percentage=0.0, drop_indices={1})
    arq_sender = SelectiveRepeatSender(session_id, transfer_id, config, chunks)
    udp_sender = UdpSender(
        peer_host="127.0.0.1",
        peer_port=udp_receiver.local_port,
        arq_sender=arq_sender,
        loss_simulator=sender_loss,
    )
    await udp_sender.start()

    success = await udp_sender.wait_complete(timeout=5.0)
    assert success is True
    await udp_receiver.wait_complete(timeout=2.0)

    assert arq_receiver.get_reconstructed_data() == b"".join(chunks)
    # Only frame 1 retransmitted! (Notice total_retransmissions is exactly 1)
    assert arq_sender.stats.total_retransmissions == 1
    assert arq_receiver.stats.buffered_frames >= 2

    await udp_sender.close()
    await udp_receiver.close()


@pytest.mark.asyncio
async def test_udp_selective_repeat_seeded_loss_30_percent(
    session_and_transfer_ids: tuple[uuid.UUID, uuid.UUID]
) -> None:
    """Selective Repeat succeeds under 30% loss over UDP."""
    session_id, transfer_id = session_and_transfer_ids
    config = get_default_config(ProtocolType.SELECTIVE_REPEAT)
    config.sender_window_size = 4
    config.receiver_window_size = 4
    config.timeout_ms = 100
    config.max_retries = 15
    config.frame_delay_ms = 0

    chunks = [f"SR seeded loss packet {i}".encode() for i in range(16)]
    arq_receiver = SelectiveRepeatReceiver(session_id, transfer_id, config, len(chunks))
    udp_receiver = UdpReceiver(arq_receiver=arq_receiver, host="127.0.0.1", port=0)
    await udp_receiver.start()

    sender_loss = PacketLossSimulator(loss_percentage=30.0, seed=123456)
    arq_sender = SelectiveRepeatSender(session_id, transfer_id, config, chunks)
    udp_sender = UdpSender(
        peer_host="127.0.0.1",
        peer_port=udp_receiver.local_port,
        arq_sender=arq_sender,
        loss_simulator=sender_loss,
    )
    await udp_sender.start()

    success = await udp_sender.wait_complete(timeout=10.0)
    assert success is True
    await udp_receiver.wait_complete(timeout=3.0)

    assert arq_receiver.get_reconstructed_data() == b"".join(chunks)
    assert arq_sender.stats.total_retransmissions > 0

    await udp_sender.close()
    await udp_receiver.close()


@pytest.mark.asyncio
async def test_udp_frame_delay_pacing(session_and_transfer_ids: tuple[uuid.UUID, uuid.UUID]) -> None:
    """Configurable frame delay slows transmission pacing as intended."""
    session_id, transfer_id = session_and_transfer_ids
    config = get_default_config(ProtocolType.SELECTIVE_REPEAT)
    config.frame_delay_ms = 25  # 25ms pacing per frame

    chunks = [f"Paced chunk {i}".encode() for i in range(6)]
    arq_receiver = SelectiveRepeatReceiver(session_id, transfer_id, config, len(chunks))
    udp_receiver = UdpReceiver(arq_receiver=arq_receiver, host="127.0.0.1", port=0)
    await udp_receiver.start()

    arq_sender = SelectiveRepeatSender(session_id, transfer_id, config, chunks)
    udp_sender = UdpSender(
        peer_host="127.0.0.1",
        peer_port=udp_receiver.local_port,
        arq_sender=arq_sender,
    )

    t0 = time.monotonic()
    await udp_sender.start()
    success = await udp_sender.wait_complete(timeout=5.0)
    elapsed = time.monotonic() - t0

    assert success is True
    await udp_receiver.wait_complete(timeout=2.0)
    assert arq_receiver.get_reconstructed_data() == b"".join(chunks)

    # With 6 frames and 25ms delay per frame, transmission should take >= 0.12s
    assert elapsed >= 0.12

    await udp_sender.close()
    await udp_receiver.close()

