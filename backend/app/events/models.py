"""Visualization Event data models for real-time frontend WebSocket updates."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional
import uuid


class EventType(str, Enum):
    """Event names for all stages of transfer and network operations."""

    # Connection events
    DEVICE_DISCOVERED = "DEVICE_DISCOVERED"
    CONNECTION_REQUEST = "CONNECTION_REQUEST"
    CONNECTION_APPROVED = "CONNECTION_APPROVED"
    CONNECTION_REJECTED = "CONNECTION_REJECTED"
    SESSION_ESTABLISHED = "SESSION_ESTABLISHED"
    SESSION_ENDED = "SESSION_ENDED"

    # Transfer lifecycle events
    TRANSFER_REQUEST = "TRANSFER_REQUEST"
    TRANSFER_ACCEPTED = "TRANSFER_ACCEPTED"
    TRANSFER_REJECTED = "TRANSFER_REJECTED"
    TRANSFER_STARTED = "TRANSFER_STARTED"
    TRANSFER_PROGRESS = "TRANSFER_PROGRESS"
    TRANSFER_COMPLETED = "TRANSFER_COMPLETED"
    TRANSFER_FAILED = "TRANSFER_FAILED"
    TRANSFER_CANCELLED = "TRANSFER_CANCELLED"

    # ARQ and Network events
    FRAME_SENT = "FRAME_SENT"
    FRAME_RECEIVED = "FRAME_RECEIVED"
    ACK_SENT = "ACK_SENT"
    ACK_RECEIVED = "ACK_RECEIVED"
    FRAME_LOST = "FRAME_LOST"
    ACK_LOST = "ACK_LOST"
    FRAME_CORRUPTED = "FRAME_CORRUPTED"
    TIMEOUT = "TIMEOUT"
    FRAME_RETRANSMITTED = "FRAME_RETRANSMITTED"
    FRAME_BUFFERED = "FRAME_BUFFERED"
    FRAME_DISCARDED = "FRAME_DISCARDED"
    WINDOW_UPDATED = "WINDOW_UPDATED"

    # Integrity events
    FILE_RECONSTRUCTION_STARTED = "FILE_RECONSTRUCTION_STARTED"
    FILE_RECONSTRUCTION_COMPLETED = "FILE_RECONSTRUCTION_COMPLETED"
    INTEGRITY_CHECK_STARTED = "INTEGRITY_CHECK_STARTED"
    INTEGRITY_CHECK_COMPLETED = "INTEGRITY_CHECK_COMPLETED"
    INTEGRITY_CHECK_FAILED = "INTEGRITY_CHECK_FAILED"


@dataclass
class VisualizationEvent:
    """Structure of an event pushed to the local frontend."""
    event_id: str
    event_seq: int
    device_id: uuid.UUID
    event: EventType
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    session_id: Optional[uuid.UUID] = None
    transfer_id: Optional[uuid.UUID] = None
    data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize event to a JSON-compatible dictionary."""
        return {
            "event_id": self.event_id,
            "event_seq": self.event_seq,
            "device_id": str(self.device_id),
            "event": self.event.value,
            "timestamp": self.timestamp.isoformat(),
            "session_id": str(self.session_id) if self.session_id else None,
            "transfer_id": str(self.transfer_id) if self.transfer_id else None,
            "data": self.data,
        }

