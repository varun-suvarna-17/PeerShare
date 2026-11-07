"""Unit tests for Stop-and-Wait (One-Bit) ARQ protocol."""

import uuid
import pytest

from app.protocol.config import get_default_config
from app.protocol.constants import ProtocolType, TransferStatus
from app.protocol.simulator import NetworkSimulator
from app.protocol.stop_and_wait import StopAndWaitReceiver, StopAndWaitSender


@pytest.fixture
def session_and_transfer_ids() -> tuple[uuid.UUID, uuid.UUID]:
    return uuid.uuid4(), uuid.uuid4()


def test_stop_and_wait_clean_transfer(session_and_transfer_ids: tuple[uuid.UUID, uuid.UUID]) -> None:
    """Successful Stop-and-Wait transfer with zero loss."""
    session_id, transfer_id = session_and_transfer_ids
    config = get_default_config(ProtocolType.STOP_AND_WAIT)

    chunks = [b"Chunk 0", b"Chunk 1", b"Chunk 2", b"Chunk 3", b"Chunk 4"]
    sender = StopAndWaitSender(session_id, transfer_id, config, chunks)
    receiver = StopAndWaitReceiver(session_id, transfer_id, config, len(chunks))

    sim = NetworkSimulator(sender, receiver, loss_rate=0.0)
    status = sim.run()

    assert status == TransferStatus.COMPLETED
    assert receiver.status == TransferStatus.COMPLETED
    assert receiver.get_reconstructed_data() == b"".join(chunks)
    assert sender.stats.total_frames == 5
    assert sender.stats.total_transmissions == 5
    assert sender.stats.total_retransmissions == 0
    assert receiver.stats.unique_frames_received == 5


def test_stop_and_wait_empty_file(session_and_transfer_ids: tuple[uuid.UUID, uuid.UUID]) -> None:
    """Empty file transfer (0 data frames, FIN/FIN-ACK handshake only)."""
    session_id, transfer_id = session_and_transfer_ids
    config = get_default_config(ProtocolType.STOP_AND_WAIT)

    sender = StopAndWaitSender(session_id, transfer_id, config, [])
    receiver = StopAndWaitReceiver(session_id, transfer_id, config, 0)

    sim = NetworkSimulator(sender, receiver)
    status = sim.run()

    assert status == TransferStatus.COMPLETED
    assert receiver.status == TransferStatus.COMPLETED
    assert receiver.get_reconstructed_data() == b""


def test_stop_and_wait_data_frame_loss_and_retransmit(
    session_and_transfer_ids: tuple[uuid.UUID, uuid.UUID]
) -> None:
    """Simulate single data frame loss. Sender must timeout and retransmit."""
    session_id, transfer_id = session_and_transfer_ids
    config = get_default_config(ProtocolType.STOP_AND_WAIT)

    chunks = [b"Frame A", b"Frame B", b"Frame C"]
    sender = StopAndWaitSender(session_id, transfer_id, config, chunks)
    receiver = StopAndWaitReceiver(session_id, transfer_id, config, len(chunks))

    sim = NetworkSimulator(sender, receiver, drop_data_indices={1})
    status = sim.run()

    assert status == TransferStatus.COMPLETED
    assert receiver.get_reconstructed_data() == b"".join(chunks)
    assert sender.stats.total_retransmissions == 1
    assert sender.stats.total_transmissions == 4  # 3 initial + 1 retransmission


def test_stop_and_wait_ack_loss_and_duplicate_handling(
    session_and_transfer_ids: tuple[uuid.UUID, uuid.UUID]
) -> None:
    """Simulate ACK loss. Sender retransmits; receiver drops duplicate and resends ACK."""
    session_id, transfer_id = session_and_transfer_ids
    config = get_default_config(ProtocolType.STOP_AND_WAIT)

    chunks = [b"Chunk 0", b"Chunk 1"]
    sender = StopAndWaitSender(session_id, transfer_id, config, chunks)
    receiver = StopAndWaitReceiver(session_id, transfer_id, config, len(chunks))

    # Drop ACK for frame index 0
    sim = NetworkSimulator(sender, receiver, drop_ack_indices={0})
    status = sim.run()

    assert status == TransferStatus.COMPLETED
    assert receiver.get_reconstructed_data() == b"".join(chunks)
    assert receiver.stats.discarded_frames == 1  # 1 duplicate dropped
    assert sender.stats.total_retransmissions == 1


def test_stop_and_wait_corrupted_frame(session_and_transfer_ids: tuple[uuid.UUID, uuid.UUID]) -> None:
    """Simulate corrupted frame. Receiver ignores it; sender retransmits upon timeout."""
    session_id, transfer_id = session_and_transfer_ids
    config = get_default_config(ProtocolType.STOP_AND_WAIT)

    chunks = [b"Data 1", b"Data 2"]
    sender = StopAndWaitSender(session_id, transfer_id, config, chunks)
    receiver = StopAndWaitReceiver(session_id, transfer_id, config, len(chunks))

    sim = NetworkSimulator(sender, receiver, corrupt_data_indices={0})
    status = sim.run()

    assert status == TransferStatus.COMPLETED
    assert receiver.get_reconstructed_data() == b"".join(chunks)
    assert receiver.stats.corrupted_frames == 1
    assert sender.stats.total_retransmissions == 1


def test_stop_and_wait_max_retries_exceeded(session_and_transfer_ids: tuple[uuid.UUID, uuid.UUID]) -> None:
    """When retries exceed max_retries, sender fails the transfer."""
    session_id, transfer_id = session_and_transfer_ids
    config = get_default_config(ProtocolType.STOP_AND_WAIT)
    config.max_retries = 2

    chunks = [b"Unreachable frame"]
    sender = StopAndWaitSender(session_id, transfer_id, config, chunks)
    receiver = StopAndWaitReceiver(session_id, transfer_id, config, len(chunks))

    # Continuous loss by setting 100% loss rate
    sim = NetworkSimulator(sender, receiver, loss_rate=100.0)
    status = sim.run()

    assert status == TransferStatus.FAILED


def test_stop_and_wait_probabilistic_loss_with_seed(
    session_and_transfer_ids: tuple[uuid.UUID, uuid.UUID]
) -> None:
    """Test transfer under 20% loss with fixed random seed."""
    session_id, transfer_id = session_and_transfer_ids
    config = get_default_config(ProtocolType.STOP_AND_WAIT)
    config.max_retries = 10

    chunks = [f"Payload block {i}".encode() for i in range(15)]
    sender = StopAndWaitSender(session_id, transfer_id, config, chunks)
    receiver = StopAndWaitReceiver(session_id, transfer_id, config, len(chunks))

    sim = NetworkSimulator(sender, receiver, loss_rate=20.0, loss_seed=12345)
    status = sim.run()

    assert status == TransferStatus.COMPLETED
    assert receiver.get_reconstructed_data() == b"".join(chunks)
    assert sender.stats.total_retransmissions > 0

