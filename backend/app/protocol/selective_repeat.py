"""Selective Repeat ARQ Protocol implementation."""

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


class SelectiveRepeatSender(BaseSender):
    """Selective Repeat ARQ sender with individual timers and acknowledgements."""

    def __init__(
        self,
        session_id: uuid.UUID,
        transfer_id: uuid.UUID,
        config: ProtocolConfig,
        chunks: list[bytes],
    ) -> None:
        super().__init__(session_id, transfer_id, config, chunks)
        self.outstanding_frames: dict[int, DataFrame] = {}
        self.timers: dict[int, Timer] = {}
        self.acknowledged_indices: set[int] = set()

    def get_frames_to_send(self, now: float) -> list[DataFrame]:
        """Send new frames within the sender sliding window."""
        if self.status != TransferStatus.TRANSFERRING:
            return []

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
            self.timers[self.next_frame_index] = Timer(
                frame_index=self.next_frame_index,
                started_at=now,
                timeout_ms=self.config.timeout_ms,
            )
            self.next_frame_index += 1
            self.stats.total_transmissions += 1
            new_frames.append(frame)

        return new_frames

    def handle_ack(self, ack: AckFrame, now: float) -> bool:
        """Process individual ACK frame."""
        if ack.frame_type == FrameType.FIN_ACK:
            return self.handle_fin_ack(ack)

        if ack.frame_type != FrameType.ACK:
            return False

        idx = ack.frame_index
        # Validate that the ACK pertains to a frame that was sent
        if self.base_frame_index <= idx < self.next_frame_index:
            if idx not in self.acknowledged_indices:
                self.acknowledged_indices.add(idx)
                self.stats.total_acks_received += 1

                if idx in self.timers:
                    self.timers[idx].stop()

                # Slide window forward if base frame index is acknowledged
                while self.base_frame_index in self.acknowledged_indices:
                    self.outstanding_frames.pop(self.base_frame_index, None)
                    self.timers.pop(self.base_frame_index, None)
                    self.base_frame_index += 1

                return True

        return False

    def check_timeouts(self, now: float) -> list[DataFrame]:
        """Check individual timers. Retransmit only timed-out frames."""
        if self.status != TransferStatus.TRANSFERRING:
            return []

        if self.is_data_acknowledged() and not self.fin_ack_received:
            fin = self.get_fin_frame(now)
            return [fin] if fin is not None else []

        retransmissions: list[DataFrame] = []
        for idx in sorted(self.outstanding_frames.keys()):
            if idx in self.acknowledged_indices:
                continue

            t = self.timers.get(idx)
            if t is not None and t.is_expired(now):
                if t.retry_count >= self.config.max_retries:
                    self.status = TransferStatus.FAILED
                    return []

                t.restart(now, increment_retries=True)
                frame = self.outstanding_frames[idx]
                retransmissions.append(frame)
                self.stats.total_transmissions += 1
                self.stats.total_retransmissions += 1

        return retransmissions


class SelectiveRepeatReceiver(BaseReceiver):
    """Selective Repeat ARQ receiver with out-of-order frame buffering and individual ACKs."""

    def __init__(
        self,
        session_id: uuid.UUID,
        transfer_id: uuid.UUID,
        config: ProtocolConfig,
        total_frames: int,
    ) -> None:
        super().__init__(session_id, transfer_id, config, total_frames)
        self.buffered_frames: dict[int, bytes] = {}
        self.received_indices: set[int] = set()

    def handle_data_frame(self, frame: DataFrame, now: float) -> Optional[AckFrame]:
        """Process incoming DATA or FIN frame."""
        if frame.frame_type == FrameType.FIN:
            if self.base_frame_index >= self.total_frames:
                self.fin_received = True
                self.status = TransferStatus.COMPLETED
                self.stats.total_acks_sent += 1
                return AckFrame(
                    session_id=self.session_id,
                    transfer_id=self.transfer_id,
                    ack_number=frame.sequence_number,
                    frame_index=frame.frame_index,
                    ack_type=AckType.INDIVIDUAL,
                    frame_type=FrameType.FIN_ACK,
                )
            return None

        if frame.frame_type != FrameType.DATA:
            return None

        idx = frame.frame_index

        # Prepare individual ACK
        ack = AckFrame(
            session_id=self.session_id,
            transfer_id=self.transfer_id,
            ack_number=frame.sequence_number,
            frame_index=idx,
            ack_type=AckType.INDIVIDUAL,
            frame_type=FrameType.ACK,
        )

        if idx == self.base_frame_index:
            # In-order frame received
            self.delivered_chunks.append(frame.payload)
            self.stats.unique_frames_received += 1
            self.stats.total_bytes += len(frame.payload)
            self.received_indices.add(idx)
            self.base_frame_index += 1

            # Deliver any consecutively buffered frames
            while self.base_frame_index in self.buffered_frames:
                chunk = self.buffered_frames.pop(self.base_frame_index)
                self.delivered_chunks.append(chunk)
                self.stats.unique_frames_received += 1
                self.stats.total_bytes += len(chunk)
                self.received_indices.add(self.base_frame_index)
                self.base_frame_index += 1

            self.stats.total_acks_sent += 1
            return ack

        elif self.base_frame_index < idx < (self.base_frame_index + self.config.receiver_window_size):
            # Out-of-order frame inside receiver window
            if idx not in self.buffered_frames and idx not in self.received_indices:
                self.buffered_frames[idx] = frame.payload
                self.stats.buffered_frames += 1
            else:
                self.stats.discarded_frames += 1

            self.stats.total_acks_sent += 1
            return ack

        elif idx < self.base_frame_index:
            # Duplicate frame behind base window - acknowledge so sender can advance
            self.stats.discarded_frames += 1
            self.stats.total_acks_sent += 1
            return ack

        else:
            # Beyond receiver window
            self.stats.discarded_frames += 1
            return None

