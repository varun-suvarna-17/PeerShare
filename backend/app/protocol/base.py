"""Base classes and interfaces for ARQ senders and receivers."""

from abc import ABC, abstractmethod
from typing import Optional
import uuid

from app.protocol.config import ProtocolConfig
from app.protocol.constants import FrameType, TransferStatus
from app.protocol.frame import AckFrame, DataFrame
from app.protocol.stats import TransferStatistics


class BaseSender(ABC):
    """Abstract base class for protocol senders."""

    def __init__(
        self,
        session_id: uuid.UUID,
        transfer_id: uuid.UUID,
        config: ProtocolConfig,
        chunks: list[bytes],
    ) -> None:
        self.session_id = session_id
        self.transfer_id = transfer_id
        self.config = config
        self.chunks = chunks
        self.total_frames = len(chunks)

        self.base_frame_index = 0
        self.next_frame_index = 0
        self.status = TransferStatus.TRANSFERRING
        self.stats = TransferStatistics(total_frames=self.total_frames)

        self.fin_sent = False
        self.fin_ack_received = False
        self.fin_timer: Optional[float] = None
        self.fin_retries = 0

    @abstractmethod
    def get_frames_to_send(self, now: float) -> list[DataFrame]:
        """Return frames ready for initial transmission."""
        pass

    @abstractmethod
    def handle_ack(self, ack: AckFrame, now: float) -> bool:
        """Process an incoming ACK frame. Return True if valid and processed."""
        pass

    @abstractmethod
    def check_timeouts(self, now: float) -> list[DataFrame]:
        """Check retransmission timers and return frames to retransmit."""
        pass

    def is_finished(self) -> bool:
        """Check if all data frames and the FIN handshake are completed."""
        return self.status in (TransferStatus.COMPLETED, TransferStatus.FAILED, TransferStatus.CANCELLED)

    def is_data_acknowledged(self) -> bool:
        """Check if all data chunks have been acknowledged."""
        return self.base_frame_index >= self.total_frames

    def get_fin_frame(self, now: float) -> Optional[DataFrame]:
        """Generate FIN frame when all data frames have been acknowledged."""
        if not self.is_data_acknowledged():
            return None
        if self.fin_ack_received:
            return None

        # Check if we should send or retransmit FIN
        if not self.fin_sent:
            self.fin_sent = True
            self.fin_timer = now
            return DataFrame(
                session_id=self.session_id,
                transfer_id=self.transfer_id,
                sequence_number=self.total_frames % (1 << self.config.sequence_number_bits),
                frame_index=self.total_frames,
                payload=b"",
                frame_type=FrameType.FIN,
            )

        # Retransmit FIN if timeout
        if self.fin_timer is not None and (now - self.fin_timer) * 1000.0 >= self.config.timeout_ms:
            if self.fin_retries >= self.config.max_retries:
                self.status = TransferStatus.FAILED
                return None
            self.fin_retries += 1
            self.fin_timer = now
            return DataFrame(
                session_id=self.session_id,
                transfer_id=self.transfer_id,
                sequence_number=self.total_frames % (1 << self.config.sequence_number_bits),
                frame_index=self.total_frames,
                payload=b"",
                frame_type=FrameType.FIN,
            )

        return None

    def handle_fin_ack(self, ack: AckFrame) -> bool:
        """Handle incoming FIN_ACK."""
        if ack.frame_type == FrameType.FIN_ACK:
            self.fin_ack_received = True
            self.status = TransferStatus.COMPLETED
            return True
        return False


class BaseReceiver(ABC):
    """Abstract base class for protocol receivers."""

    def __init__(
        self,
        session_id: uuid.UUID,
        transfer_id: uuid.UUID,
        config: ProtocolConfig,
        total_frames: int,
    ) -> None:
        self.session_id = session_id
        self.transfer_id = transfer_id
        self.config = config
        self.total_frames = total_frames

        self.base_frame_index = 0
        self.status = TransferStatus.TRANSFERRING
        self.stats = TransferStatistics(total_frames=total_frames)

        self.delivered_chunks: list[bytes] = []
        self.fin_received = False

    @abstractmethod
    def handle_data_frame(self, frame: DataFrame, now: float) -> Optional[AckFrame]:
        """Process incoming DATA or FIN frame and return ACK datagram if appropriate."""
        pass

    def is_finished(self) -> bool:
        """Check if all data has been received and FIN processed."""
        return self.status in (TransferStatus.COMPLETED, TransferStatus.FAILED, TransferStatus.CANCELLED)

    def get_reconstructed_data(self) -> bytes:
        """Return full reconstructed payload bytes."""
        return b"".join(self.delivered_chunks)
