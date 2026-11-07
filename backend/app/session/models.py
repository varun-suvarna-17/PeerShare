"""Session and Connection data models."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional
import uuid

from app.discovery.device import DeviceRole, DiscoveryMethod


class ConnectionStatus(str, Enum):
    """Status of an incoming connection request."""
    PENDING_APPROVAL = "PENDING_APPROVAL"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"


class SessionStatus(str, Enum):
    """Status of an established peer-to-peer session."""
    CONNECTING = "CONNECTING"
    ESTABLISHED = "ESTABLISHED"
    DISCONNECTED = "DISCONNECTED"
    CLOSED = "CLOSED"


@dataclass
class ConnectionRequest:
    """Incoming connection request requiring receiver user approval."""
    connection_id: uuid.UUID
    sender_device_id: uuid.UUID
    sender_device_name: str
    sender_ip: str
    receiver_device_id: uuid.UUID
    discovery_method: DiscoveryMethod
    status: ConnectionStatus = ConnectionStatus.PENDING_APPROVAL
    requested_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: datetime = field(
        default_factory=lambda: datetime.fromtimestamp(
            datetime.now(timezone.utc).timestamp() + 120, tz=timezone.utc
        )
    )

    def is_expired(self) -> bool:
        """Check whether the connection request has expired."""
        return datetime.now(timezone.utc) > self.expires_at


@dataclass
class Session:
    """Represents an established communication session between Sender and Receiver."""
    session_id: uuid.UUID
    local_device_id: uuid.UUID
    peer_device_id: uuid.UUID
    local_role: DeviceRole
    local_ip: str
    peer_ip: str
    local_api_port: int
    peer_api_port: int
    session_token_hash: str
    local_udp_port: int = 0
    peer_udp_port: int = 0
    status: SessionStatus = SessionStatus.CONNECTING
    receiver_ready: bool = False
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def update_timestamp(self) -> None:
        """Refresh updated_at timestamp."""
        self.updated_at = datetime.now(timezone.utc)

