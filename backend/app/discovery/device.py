"""Device data models for discovery and pairing."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional
import uuid


class DeviceRole(str, Enum):
    """Device role in the application."""
    SENDER = "SENDER"
    RECEIVER = "RECEIVER"


class DiscoveryMethod(str, Enum):
    """How the peer device was discovered."""
    ZEROCONF = "ZEROCONF"
    MANUAL = "MANUAL"


class DeviceStatus(str, Enum):
    """Current device status."""
    ONLINE = "ONLINE"
    OFFLINE = "OFFLINE"
    CONNECTED = "CONNECTED"


@dataclass
class Device:
    """Represents a device discovered or running on the local network."""
    device_id: uuid.UUID
    device_name: str
    ip_address: str
    api_port: int
    udp_port: int = 0
    api_version: str = "1.0.0"
    role: DeviceRole = DeviceRole.RECEIVER
    discovery_method: DiscoveryMethod = DiscoveryMethod.ZEROCONF
    status: DeviceStatus = DeviceStatus.ONLINE
    last_seen: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def update_last_seen(self) -> None:
        """Refresh last seen timestamp."""
        self.last_seen = datetime.now(timezone.utc)

