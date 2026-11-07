"""Go-Back-N ARQ Protocol implementation."""

from typing import Optional
import uuid

from app.protocol.base import BaseReceiver, BaseSender
from app.protocol.config import ProtocolConfig
from app.protocol.constants import (
    SEQ_NUM_16BIT_MODULO,
    AckType,
    FrameType,
    TransferStatus,
)
from app.protocol.frame import AckFrame, DataFrame
from app.protocol.sequence import sequence_from_index
from app.protocol.timer import Timer


class GoBackNSender(BaseSender):
    """Go-Back-N ARQ sender with sliding window and cumulative acknowledgements."""

    def __init__(
        self,
        session_id: uuid.UUID,
        transfer_id: uuid.UUID,
        config: ProtocolConfig,
        chunks: list[bytes],
    ) -> None:
        super().__init__(session_id, transfer_id, config, chunks)
        self.outstanding_frames: dict[int, DataFrame] = {}
        self.timer: Optional[Timer] = None

    def get_frames_to_send(self, now: float) -> list[DataFrame]:
        """Send new frames within the sender sliding window."""
        if self.status != TransferStatus.TRANSFERRING:
            return []

        # If all data acknowledged, handle FIN
        if self.is_data_acknowledged():
            fin = self.get_fin_frame(now)
            return [fin] if fin is not None else []

        new_frames: list[DataFrame] = []
        while (
            (self.next_frame_index - self.base_frame_index) < self.config.sender_window_size
            and self.next_frame_index < self.total_frames
        ):
            seq = sequence_from_index(self.next_frame_index, SEQ_NUM_16BIT_MODULO)
            frame = DataFrame(
                session_id=self.session_id,
                transfer_id=self.transfer_id,
                sequence_number=seq,
                frame_index=self.next_frame_index,
                payload=self.chunks[self.next_frame_index],
                frame_type=FrameType.DATA,
            )
            self.outstanding_frames[self.next_frame_index] = frame

            # Start timer if no timer running (base frame)
            if self.timer is None or self.timer.status != "running":
                self.timer = Timer(
                    frame_index=self.base_frame_index,
                    started_at=now,
                    timeout_ms=self.config.timeout_ms,
                )

            self.next_frame_index += 1
            self.stats.total_transmissions += 1
            new_frames.append(frame)

        return new_frames

    def handle_ack(self, ack: AckFrame, now: float) -> bool:
        """Process cumulative ACK frame."""
        if ack.frame_type == FrameType.FIN_ACK:
            return self.handle_fin_ack(ack)

        if ack.frame_type != FrameType.ACK:
            return False

        # In Go-Back-N, ack.frame_index is the next expected frame index (cumulative ACK)
        if ack.frame_index > self.base_frame_index:
            acked_up_to = min(ack.frame_index, self.next_frame_index)
            for idx in range(self.base_frame_index, acked_up_to):
                self.outstanding_frames.pop(idx, None)

            self.base_frame_index = ack.frame_index
            self.stats.total_acks_received += 1

            if self.base_frame_index == self.next_frame_index:
                # All outstanding frames acknowledged
                if self.timer:
                    self.timer.stop()
                self.timer = None
            else:
                # Restart timer for the oldest unacknowledged frame
                self.timer = Timer(
                    frame_index=self.base_frame_index,
                    started_at=now,
                    timeout_ms=self.config.timeout_ms,
                )
            return True

        return False

    def check_timeouts(self, now: float) -> list[DataFrame]:
        """Check the window timer. On timeout, retransmit all outstanding frames."""
        if self.status != TransferStatus.TRANSFERRING:
            return []

        if self.is_data_acknowledged() and not self.fin_ack_received:
            fin = self.get_fin_frame(now)
            return [fin] if fin is not None else []

        if self.timer is not None and self.timer.is_expired(now):
            if self.timer.retry_count >= self.config.max_retries:
                self.status = TransferStatus.FAILED
                return []

            self.timer.restart(now, increment_retries=True)

            retransmissions: list[DataFrame] = []
            for idx in sorted(self.outstanding_frames.keys()):
                frame = self.outstanding_frames[idx]
                retransmissions.append(frame)
                self.stats.total_transmissions += 1
                self.stats.total_retransmissions += 1

            return retransmissions

        return []


class GoBackNReceiver(BaseReceiver):
    """Go-Back-N ARQ receiver with window size 1 and cumulative ACKs."""

    def __init__(
        self,
        session_id: uuid.UUID,
        transfer_id: uuid.UUID,
        config: ProtocolConfig,
        total_frames: int,
    ) -> None:
        super().__init__(session_id, transfer_id, config, total_frames)
        self.expected_frame_index = 0
        self.expected_seq = 0

    def handle_data_frame(self, frame: DataFrame, now: float) -> Optional[AckFrame]:
        """Process incoming DATA or FIN frame."""
        if frame.frame_type == FrameType.FIN:
            if self.expected_frame_index >= self.total_frames:
                self.fin_received = True
                self.status = TransferStatus.COMPLETED
                self.stats.total_acks_sent += 1
                return AckFrame(
                    session_id=self.session_id,
                    transfer_id=self.transfer_id,
                    ack_number=frame.sequence_number,
                    frame_index=frame.frame_index,
                    ack_type=AckType.CUMULATIVE,
                    frame_type=FrameType.FIN_ACK,
                )
            return None

        if frame.frame_type != FrameType.DATA:
            return None

        if frame.frame_index == self.expected_frame_index and frame.sequence_number == self.expected_seq:
            # In-order expected frame
            self.delivered_chunks.append(frame.payload)
            self.stats.unique_frames_received += 1
            self.stats.total_bytes += len(frame.payload)
            self.base_frame_index += 1

            self.expected_frame_index += 1
            self.expected_seq = sequence_from_index(self.expected_frame_index, SEQ_NUM_16BIT_MODULO)

            ack = AckFrame(
                session_id=self.session_id,
                transfer_id=self.transfer_id,
                ack_number=self.expected_seq,
                frame_index=self.expected_frame_index,
                ack_type=AckType.CUMULATIVE,
                frame_type=FrameType.ACK,
            )
            self.stats.total_acks_sent += 1
            return ack
        else:
            # Out-of-order or duplicate frame discarded
            self.stats.discarded_frames += 1
            # Re-send cumulative ACK for currently expected sequence
            ack = AckFrame(
                session_id=self.session_id,
                transfer_id=self.transfer_id,
                ack_number=self.expected_seq,
                frame_index=self.expected_frame_index,
                ack_type=AckType.CUMULATIVE,
                frame_type=FrameType.ACK,
            )
            self.stats.total_acks_sent += 1
            return ack

