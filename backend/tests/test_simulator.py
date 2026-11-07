"""Unit tests for the NetworkSimulator itself."""

import uuid
import pytest

from app.protocol.config import get_default_config
from app.protocol.constants import ProtocolType, TransferStatus
from app.protocol.selective_repeat import SelectiveRepeatReceiver, SelectiveRepeatSender
from app.protocol.simulator import NetworkSimulator


def test_seeded_loss_reproducibility() -> None:
    """AMENDMENTS.md Acceptance Criterion: With a fixed seed, the same loss pattern reproduces the same retransmission count."""
    config = get_default_config(ProtocolType.SELECTIVE_REPEAT)
    config.max_retries = 20
    chunks = [f"Deterministic block {i}".encode() for i in range(20)]
    seed = 88888

    # Run 1
    s_id_1, t_id_1 = uuid.uuid4(), uuid.uuid4()
    sender_1 = SelectiveRepeatSender(s_id_1, t_id_1, config, chunks)
    receiver_1 = SelectiveRepeatReceiver(s_id_1, t_id_1, config, len(chunks))
    sim_1 = NetworkSimulator(sender_1, receiver_1, loss_rate=25.0, loss_seed=seed)
    status_1 = sim_1.run()

    # Run 2
    s_id_2, t_id_2 = uuid.uuid4(), uuid.uuid4()
    sender_2 = SelectiveRepeatSender(s_id_2, t_id_2, config, chunks)
    receiver_2 = SelectiveRepeatReceiver(s_id_2, t_id_2, config, len(chunks))
    sim_2 = NetworkSimulator(sender_2, receiver_2, loss_rate=25.0, loss_seed=seed)
    status_2 = sim_2.run()

    assert status_1 == TransferStatus.COMPLETED
    assert status_2 == TransferStatus.COMPLETED
    # Exactly matching retransmission count
    assert sender_1.stats.total_retransmissions == sender_2.stats.total_retransmissions
    assert sender_1.stats.total_transmissions == sender_2.stats.total_transmissions
    assert receiver_1.get_reconstructed_data() == receiver_2.get_reconstructed_data() == b"".join(chunks)


def test_simulator_data_duplication() -> None:
    """Duplicate data frames are safely processed and discarded by the receiver."""
    session_id, transfer_id = uuid.uuid4(), uuid.uuid4()
    config = get_default_config(ProtocolType.SELECTIVE_REPEAT)
    chunks = [b"Chunk 0", b"Chunk 1"]

    sender = SelectiveRepeatSender(session_id, transfer_id, config, chunks)
    receiver = SelectiveRepeatReceiver(session_id, transfer_id, config, len(chunks))

    sim = NetworkSimulator(sender, receiver, duplicate_data_indices={0})
    status = sim.run()

    assert status == TransferStatus.COMPLETED
    assert receiver.get_reconstructed_data() == b"".join(chunks)
    assert receiver.stats.discarded_frames >= 1

