"""Transfer state models."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional
import uuid

from app.protocol.config import ProtocolConfig
from app.protocol.constants import ProtocolType, TransferStatus
from app.protocol.stats import TransferStatistics


@dataclass
class Transfer:
    """Represents a file transfer instance between Sender and Receiver."""
    transfer_id: uuid.UUID
    session_id: uuid.UUID
    file_id: uuid.UUID
    file_name: str
    file_size: int
    file_sha256: str
    protocol: ProtocolType
    configuration: ProtocolConfig
    total_frames: int
    status: TransferStatus = TransferStatus.PENDING
    total_transmissions: int = 0
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    failure_reason: Optional[str] = None
    integrity_verified: bool = False
    reconstructed_path: Optional[str] = None
    local_udp_port: Optional[int] = None
    stats: Optional[TransferStatistics] = None

    def mark_started(self) -> None:
        """Mark transfer as in progress."""
        self.status = TransferStatus.TRANSFERRING
        self.started_at = datetime.now(timezone.utc)

    def mark_completed(
        self,
        reconstructed_path: Optional[str] = None,
        stats: Optional[TransferStatistics] = None,
    ) -> None:
        """Mark transfer as successfully completed."""
        self.status = TransferStatus.COMPLETED
        self.completed_at = datetime.now(timezone.utc)
        self.integrity_verified = True
        if reconstructed_path is not None:
            self.reconstructed_path = reconstructed_path
        if stats is not None:
            self.stats = stats

    def mark_failed(
        self,
        reason: str,
        stats: Optional[TransferStatistics] = None,
    ) -> None:
        """Mark transfer as failed with reason."""
        self.status = TransferStatus.FAILED
        self.completed_at = datetime.now(timezone.utc)
        self.failure_reason = reason
        self.integrity_verified = False
        if stats is not None:
            self.stats = stats

