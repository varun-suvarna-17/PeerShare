"""Unit tests for Selective Repeat ARQ protocol."""

import uuid
import pytest

from app.protocol.config import get_default_config
from app.protocol.constants import ProtocolType, TransferStatus
from app.protocol.simulator import NetworkSimulator
from app.protocol.selective_repeat import SelectiveRepeatReceiver, SelectiveRepeatSender


@pytest.fixture
def ids() -> tuple[uuid.UUID, uuid.UUID]:
    return uuid.uuid4(), uuid.uuid4()


def test_selective_repeat_clean_transfer(ids: tuple[uuid.UUID, uuid.UUID]) -> None:
    """Selective Repeat transfer with zero loss."""
    session_id, transfer_id = ids
    config = get_default_config(ProtocolType.SELECTIVE_REPEAT)
    config.sender_window_size = 4
    config.receiver_window_size = 4

    chunks = [f"SR block {i}".encode() for i in range(12)]
    sender = SelectiveRepeatSender(session_id, transfer_id, config, chunks)
    receiver = SelectiveRepeatReceiver(session_id, transfer_id, config, len(chunks))

    sim = NetworkSimulator(sender, receiver, loss_rate=0.0)
    status = sim.run()

    assert status == TransferStatus.COMPLETED
    assert receiver.status == TransferStatus.COMPLETED
    assert receiver.get_reconstructed_data() == b"".join(chunks)
    assert sender.stats.total_retransmissions == 0
    assert receiver.stats.unique_frames_received == 12


def test_selective_repeat_receiver_buffering(ids: tuple[uuid.UUID, uuid.UUID]) -> None:
    """Receiver buffers out-of-order frames and flushes them when missing frame arrives."""
    session_id, transfer_id = ids
    config = get_default_config(ProtocolType.SELECTIVE_REPEAT)
    config.sender_window_size = 4
    config.receiver_window_size = 4

    chunks = [b"Chunk 0", b"Chunk 1", b"Chunk 2", b"Chunk 3"]
    sender = SelectiveRepeatSender(session_id, transfer_id, config, chunks)
    receiver = SelectiveRepeatReceiver(session_id, transfer_id, config, len(chunks))

    # Temporarily drop frame 1 once
    sim = NetworkSimulator(sender, receiver, drop_data_indices={1})
    status = sim.run()

    assert status == TransferStatus.COMPLETED
    assert receiver.get_reconstructed_data() == b"".join(chunks)
    # Frames 2 and 3 were buffered
    assert receiver.stats.buffered_frames >= 2
    # Only frame 1 was retransmitted! (Notice total_retransmissions == 1, NOT 3 as in GBN)
    assert sender.stats.total_retransmissions == 1


def test_selective_repeat_retransmits_only_missing_frame(ids: tuple[uuid.UUID, uuid.UUID]) -> None:
    """Verify that only the lost frame is retransmitted, not subsequent frames."""
    session_id, transfer_id = ids
    config = get_default_config(ProtocolType.SELECTIVE_REPEAT)
    config.sender_window_size = 4
    config.receiver_window_size = 4

    chunks = [f"Payload {i}".encode() for i in range(6)]
    sender = SelectiveRepeatSender(session_id, transfer_id, config, chunks)
    receiver = SelectiveRepeatReceiver(session_id, transfer_id, config, len(chunks))

    # Drop frame index 2 once
    sim = NetworkSimulator(sender, receiver, drop_data_indices={2})
    status = sim.run()

    assert status == TransferStatus.COMPLETED
    assert receiver.get_reconstructed_data() == b"".join(chunks)
    assert sender.stats.total_retransmissions == 1


def test_selective_repeat_ack_loss_and_recovery(ids: tuple[uuid.UUID, uuid.UUID]) -> None:
    """When ACK is lost, sender retransmits frame; receiver discards duplicate and resends ACK."""
    session_id, transfer_id = ids
    config = get_default_config(ProtocolType.SELECTIVE_REPEAT)
    config.sender_window_size = 4
    config.receiver_window_size = 4

    chunks = [b"Data 0", b"Data 1", b"Data 2"]
    sender = SelectiveRepeatSender(session_id, transfer_id, config, chunks)
    receiver = SelectiveRepeatReceiver(session_id, transfer_id, config, len(chunks))

    # Drop ACK for frame index 0 once
    sim = NetworkSimulator(sender, receiver, drop_ack_indices={0})
    status = sim.run()

    assert status == TransferStatus.COMPLETED
    assert receiver.get_reconstructed_data() == b"".join(chunks)
    assert sender.stats.total_retransmissions == 1
    assert receiver.stats.discarded_frames >= 1


def test_selective_repeat_max_retries_exceeded(ids: tuple[uuid.UUID, uuid.UUID]) -> None:
    """Transfer fails when frame exceeds maximum retry count."""
    session_id, transfer_id = ids
    config = get_default_config(ProtocolType.SELECTIVE_REPEAT)
    config.max_retries = 2

    chunks = [b"Block A", b"Block B"]
    sender = SelectiveRepeatSender(session_id, transfer_id, config, chunks)
    receiver = SelectiveRepeatReceiver(session_id, transfer_id, config, len(chunks))

    sim = NetworkSimulator(sender, receiver, loss_rate=100.0)
    status = sim.run()

    assert status == TransferStatus.FAILED


def test_selective_repeat_probabilistic_loss_30_percent(ids: tuple[uuid.UUID, uuid.UUID]) -> None:
    """Selective Repeat transfer succeeds under 30% loss with seeded RNG."""
    session_id, transfer_id = ids
    config = get_default_config(ProtocolType.SELECTIVE_REPEAT)
    config.max_retries = 15  # Recommended preset in AMENDMENTS.md for 30% loss

    chunks = [f"SR chunk {i} with some extra padding text".encode() for i in range(25)]
    sender = SelectiveRepeatSender(session_id, transfer_id, config, chunks)
    receiver = SelectiveRepeatReceiver(session_id, transfer_id, config, len(chunks))

    sim = NetworkSimulator(sender, receiver, loss_rate=30.0, loss_seed=424242)
    status = sim.run()

    assert status == TransferStatus.COMPLETED
    assert receiver.get_reconstructed_data() == b"".join(chunks)
    assert sender.stats.total_retransmissions > 0

