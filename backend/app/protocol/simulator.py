"""In-memory network simulator for ARQ protocol testing."""

from dataclasses import dataclass, field
import random
from typing import Optional, Union

from app.protocol.base import BaseReceiver, BaseSender
from app.protocol.constants import FrameType, TransferStatus
from app.protocol.frame import AckFrame, DataFrame, decode_ack_frame, decode_data_frame


@dataclass
class NetworkSimulator:
    """Simulates an in-memory lossy channel connecting an ARQ Sender and Receiver."""

    sender: BaseSender
    receiver: BaseReceiver
    loss_rate: float = 0.0  # Percentage [0.0, 100.0]
    loss_seed: Optional[int] = None

    # Deterministic control sets
    drop_data_indices: set[int] = field(default_factory=set)
    drop_ack_indices: set[int] = field(default_factory=set)
    corrupt_data_indices: set[int] = field(default_factory=set)
    duplicate_data_indices: set[int] = field(default_factory=set)

    def __post_init__(self) -> None:
        self.rng = random.Random(self.loss_seed)
        self.virtual_time: float = 0.0

        # Queues for in-transit frames
        self.data_queue: list[DataFrame] = []
        self.ack_queue: list[AckFrame] = []

    def should_drop(self) -> bool:
        """Probabilistically decide whether to drop a packet."""
        if self.loss_rate <= 0.0:
            return False
        if self.loss_rate >= 100.0:
            return True
        return self.rng.random() * 100.0 < self.loss_rate

    def step(self, now: float) -> bool:
        """Perform a single discrete simulation step."""
        activity = False

        # 1. Sender timeout checks (and retransmissions)
        timeout_frames = self.sender.check_timeouts(now)
        for frame in timeout_frames:
            self.data_queue.append(frame)
            activity = True

        # 2. Sender new frame transmissions
        new_frames = self.sender.get_frames_to_send(now)
        for frame in new_frames:
            self.data_queue.append(frame)
            activity = True

        # 3. Process data queue (Sender -> Receiver)
        in_flight_data = list(self.data_queue)
        self.data_queue.clear()

        for frame in in_flight_data:
            # Deterministic or probabilistic drop
            if frame.frame_index in self.drop_data_indices:
                self.drop_data_indices.remove(frame.frame_index)
                self.sender.stats.dropped_data_frames += 1
                continue
            if self.should_drop():
                self.sender.stats.dropped_data_frames += 1
                continue

            # Deterministic duplication
            frames_to_deliver = [frame]
            if frame.frame_index in self.duplicate_data_indices:
                self.duplicate_data_indices.remove(frame.frame_index)
                frames_to_deliver.append(frame)

            for f in frames_to_deliver:
                # Deterministic corruption (simulate CRC mismatch)
                if f.frame_index in self.corrupt_data_indices:
                    self.corrupt_data_indices.remove(f.frame_index)
                    self.receiver.stats.corrupted_frames += 1
                    # Receiver discards corrupted frames without acknowledging
                    continue

                ack = self.receiver.handle_data_frame(f, now)
                if ack is not None:
                    self.ack_queue.append(ack)
                    activity = True

        # 4. Process ACK queue (Receiver -> Sender)
        in_flight_acks = list(self.ack_queue)
        self.ack_queue.clear()

        for ack in in_flight_acks:
            # Deterministic or probabilistic drop
            if ack.frame_index in self.drop_ack_indices:
                self.drop_ack_indices.remove(ack.frame_index)
                self.receiver.stats.dropped_ack_frames += 1
                continue
            if self.should_drop():
                self.receiver.stats.dropped_ack_frames += 1
                continue

            processed = self.sender.handle_ack(ack, now)
            if processed:
                activity = True

        return activity

    def run(self, max_steps: int = 5000, tick_ms: float = 100.0) -> TransferStatus:
        """Run the simulation loop until completion, failure, or max_steps reached."""
        step_count = 0
        tick_sec = tick_ms / 1000.0

        while step_count < max_steps:
            step_count += 1
            self.step(self.virtual_time)

            if self.sender.is_finished() and self.receiver.is_finished():
                break
            if self.sender.status == TransferStatus.FAILED or self.receiver.status == TransferStatus.FAILED:
                break

            self.virtual_time += tick_sec

        self.sender.stats.finalize(self.virtual_time)
        self.receiver.stats.finalize(self.virtual_time)
        return self.sender.status

