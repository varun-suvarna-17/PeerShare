"""Stop-and-Wait (One-Bit) ARQ Protocol implementation."""

from typing import Optional
import uuid

from app.protocol.base import BaseReceiver, BaseSender
from app.protocol.config import ProtocolConfig
from app.protocol.constants import (
    STOP_AND_WAIT_MODULO,
    AckType,
    FrameType,
    TransferStatus,
)
from app.protocol.frame import AckFrame, DataFrame
from app.protocol.sequence import stop_and_wait_seq_from_index
from app.protocol.timer import Timer


class StopAndWaitSender(BaseSender):
    """Stop-and-Wait ARQ sender."""

    def __init__(
        self,
        session_id: uuid.UUID,
        transfer_id: uuid.UUID,
        config: ProtocolConfig,
        chunks: list[bytes],
    ) -> None:
        super().__init__(session_id, transfer_id, config, chunks)
        self.timer: Optional[Timer] = None
        self.outstanding_frame: Optional[DataFrame] = None

    def get_frames_to_send(self, now: float) -> list[DataFrame]:
        """Send next frame if no frame is currently outstanding."""
        if self.status != TransferStatus.TRANSFERRING:
            return []

        # If data is done, check for FIN
        if self.is_data_acknowledged():
            fin = self.get_fin_frame(now)
            return [fin] if fin is not None else []

        if self.outstanding_frame is not None:
            return []

        if self.next_frame_index < self.total_frames:
            seq = stop_and_wait_seq_from_index(self.next_frame_index)
            frame = DataFrame(
                session_id=self.session_id,
                transfer_id=self.transfer_id,
                sequence_number=seq,
                frame_index=self.next_frame_index,
                payload=self.chunks[self.next_frame_index],
                frame_type=FrameType.DATA,
            )
            self.outstanding_frame = frame
            self.timer = Timer(
                frame_index=self.next_frame_index,
                started_at=now,
                timeout_ms=self.config.timeout_ms,
            )
            self.next_frame_index += 1
            self.stats.total_transmissions += 1
            return [frame]

        return []

    def handle_ack(self, ack: AckFrame, now: float) -> bool:
        """Process ACK datagram."""
        if ack.frame_type == FrameType.FIN_ACK:
            return self.handle_fin_ack(ack)

        if ack.frame_type != FrameType.ACK:
            return False

        if self.outstanding_frame is None:
            return False

        expected_seq = stop_and_wait_seq_from_index(self.base_frame_index)
        if ack.frame_index == self.base_frame_index and ack.ack_number == expected_seq:
            self.stats.total_acks_received += 1
            self.outstanding_frame = None
            if self.timer:
                self.timer.stop()
            self.timer = None
            self.base_frame_index += 1
            return True

        return False

    def check_timeouts(self, now: float) -> list[DataFrame]:
        """Check timer for timeout and return retransmitted frame if expired."""
        if self.status != TransferStatus.TRANSFERRING:
            return []

        # If waiting on FIN
        if self.is_data_acknowledged() and not self.fin_ack_received:
            fin = self.get_fin_frame(now)
            return [fin] if fin is not None else []

        if self.outstanding_frame is not None and self.timer is not None:
            if self.timer.is_expired(now):
                if self.timer.retry_count >= self.config.max_retries:
                    self.status = TransferStatus.FAILED
                    return []
                self.timer.restart(now, increment_retries=True)
                self.stats.total_retransmissions += 1
                self.stats.total_transmissions += 1
                return [self.outstanding_frame]

        return []


class StopAndWaitReceiver(BaseReceiver):
    """Stop-and-Wait ARQ receiver."""

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
                    ack_type=AckType.INDIVIDUAL,
                    frame_type=FrameType.FIN_ACK,
                )
            return None

        if frame.frame_type != FrameType.DATA:
            return None

        if frame.frame_index == self.expected_frame_index and frame.sequence_number == self.expected_seq:
            # Expected in-order frame
            self.delivered_chunks.append(frame.payload)
            self.stats.unique_frames_received += 1
            self.stats.total_bytes += len(frame.payload)
            self.base_frame_index += 1

            ack = AckFrame(
                session_id=self.session_id,
                transfer_id=self.transfer_id,
                ack_number=frame.sequence_number,
                frame_index=frame.frame_index,
                ack_type=AckType.INDIVIDUAL,
                frame_type=FrameType.ACK,
            )
            self.expected_frame_index += 1
            self.expected_seq = stop_and_wait_seq_from_index(self.expected_frame_index)
            self.stats.total_acks_sent += 1
            return ack

        elif frame.frame_index < self.expected_frame_index:
            # Duplicate frame received
            self.stats.discarded_frames += 1
            ack = AckFrame(
                session_id=self.session_id,
                transfer_id=self.transfer_id,
                ack_number=frame.sequence_number,
                frame_index=frame.frame_index,
                ack_type=AckType.INDIVIDUAL,
                frame_type=FrameType.ACK,
            )
            self.stats.total_acks_sent += 1
            return ack

        else:
          # Future frame, discard
          self.stats.discarded_frames += 1
          if self.expected_frame_index > 0:
              last_idx = self.expected_frame_index - 1
              ack = AckFrame(
                  session_id=self.session_id,
                  transfer_id=self.transfer_id,
                  ack_number=stop_and_wait_seq_from_index(last_idx),
                  frame_index=last_idx,
                  ack_type=AckType.INDIVIDUAL,
                  frame_type=FrameType.ACK,
              )
              self.stats.total_acks_sent += 1
              return ack
          return None

