"""Unit tests for Go-Back-N ARQ protocol."""

import uuid
import pytest

from app.protocol.config import get_default_config
from app.protocol.constants import ProtocolType, TransferStatus
from app.protocol.simulator import NetworkSimulator
from app.protocol.go_back_n import GoBackNReceiver, GoBackNSender


@pytest.fixture
def ids() -> tuple[uuid.UUID, uuid.UUID]:
    return uuid.uuid4(), uuid.uuid4()


def test_go_back_n_clean_transfer(ids: tuple[uuid.UUID, uuid.UUID]) -> None:
    """Normal Go-Back-N transfer with window size 4 and 10 frames."""
    session_id, transfer_id = ids
    config = get_default_config(ProtocolType.GO_BACK_N)
    config.sender_window_size = 4

    chunks = [f"GBN chunk {i}".encode() for i in range(10)]
    sender = GoBackNSender(session_id, transfer_id, config, chunks)
    receiver = GoBackNReceiver(session_id, transfer_id, config, len(chunks))

    sim = NetworkSimulator(sender, receiver, loss_rate=0.0)
    status = sim.run()

    assert status == TransferStatus.COMPLETED
    assert receiver.status == TransferStatus.COMPLETED
    assert receiver.get_reconstructed_data() == b"".join(chunks)
    assert sender.stats.total_frames == 10
    assert sender.stats.total_retransmissions == 0
    assert receiver.stats.unique_frames_received == 10


def test_go_back_n_cumulative_ack_absorbs_lost_ack(ids: tuple[uuid.UUID, uuid.UUID]) -> None:
    """When ACK 1 is lost but ACK 2 arrives, both frame 0 and 1 are acknowledged."""
    session_id, transfer_id = ids
    config = get_default_config(ProtocolType.GO_BACK_N)
    config.sender_window_size = 4

    chunks = [b"Chunk 0", b"Chunk 1", b"Chunk 2", b"Chunk 3"]
    sender = GoBackNSender(session_id, transfer_id, config, chunks)
    receiver = GoBackNReceiver(session_id, transfer_id, config, len(chunks))

    # Drop ACK corresponding to frame 0 acceptance (which carries expected_frame_index 1)
    sim = NetworkSimulator(sender, receiver, drop_ack_indices={1})
    status = sim.run()

    assert status == TransferStatus.COMPLETED
    assert receiver.get_reconstructed_data() == b"".join(chunks)
    # Because subsequent cumulative ACK arrived before timeout, no retransmissions were needed!
    assert sender.stats.total_retransmissions == 0


def test_go_back_n_data_loss_retransmits_entire_window(ids: tuple[uuid.UUID, uuid.UUID]) -> None:
    """If frame 1 is lost, receiver discards frames 2 and 3; sender retransmits 1, 2, and 3."""
    session_id, transfer_id = ids
    config = get_default_config(ProtocolType.GO_BACK_N)
    config.sender_window_size = 4

    chunks = [b"Frame 0", b"Frame 1", b"Frame 2", b"Frame 3"]
    sender = GoBackNSender(session_id, transfer_id, config, chunks)
    receiver = GoBackNReceiver(session_id, transfer_id, config, len(chunks))

    # Drop frame index 1 once
    sim = NetworkSimulator(sender, receiver, drop_data_indices={1})
    status = sim.run()

    assert status == TransferStatus.COMPLETED
    assert receiver.get_reconstructed_data() == b"".join(chunks)
    # Receiver should have discarded out-of-order frames 2 and 3
    assert receiver.stats.discarded_frames >= 2
    # Sender retransmitted outstanding frames (1, 2, 3)
    assert sender.stats.total_retransmissions >= 3


def test_go_back_n_window_size_limit(ids: tuple[uuid.UUID, uuid.UUID]) -> None:
    """Sender window cannot exceed configured window_size."""
    session_id, transfer_id = ids
    config = get_default_config(ProtocolType.GO_BACK_N)
    config.sender_window_size = 3

    chunks = [f"Data {i}".encode() for i in range(8)]
    sender = GoBackNSender(session_id, transfer_id, config, chunks)

    # Initial transmission at time 0.0
    initial_frames = sender.get_frames_to_send(now=0.0)
    assert len(initial_frames) == 3
    assert [f.frame_index for f in initial_frames] == [0, 1, 2]

    # Calling again without ACKs yields no new frames
    more_frames = sender.get_frames_to_send(now=0.1)
    assert len(more_frames) == 0


def test_go_back_n_max_retries_exceeded(ids: tuple[uuid.UUID, uuid.UUID]) -> None:
    """Continuous loss causes transfer failure after max_retries."""
    session_id, transfer_id = ids
    config = get_default_config(ProtocolType.GO_BACK_N)
    config.max_retries = 2

    chunks = [b"Data A", b"Data B"]
    sender = GoBackNSender(session_id, transfer_id, config, chunks)
    receiver = GoBackNReceiver(session_id, transfer_id, config, len(chunks))

    sim = NetworkSimulator(sender, receiver, loss_rate=100.0)
    status = sim.run()

    assert status == TransferStatus.FAILED


def test_go_back_n_probabilistic_loss(ids: tuple[uuid.UUID, uuid.UUID]) -> None:
    """Go-Back-N succeeds under 15% packet loss with seeded RNG."""
    session_id, transfer_id = ids
    config = get_default_config(ProtocolType.GO_BACK_N)
    config.max_retries = 15

    chunks = [f"GBN payload {i}".encode() for i in range(20)]
    sender = GoBackNSender(session_id, transfer_id, config, chunks)
    receiver = GoBackNReceiver(session_id, transfer_id, config, len(chunks))

    sim = NetworkSimulator(sender, receiver, loss_rate=15.0, loss_seed=9876)
    status = sim.run()

    assert status == TransferStatus.COMPLETED
    assert receiver.get_reconstructed_data() == b"".join(chunks)
    assert sender.stats.total_retransmissions > 0

