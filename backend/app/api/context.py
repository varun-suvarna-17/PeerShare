"""Global Application Context providing access to subsystem managers."""

from dataclasses import dataclass, field
import os
import uuid
from typing import Dict, Optional

from app.discovery.device import DeviceRole
from app.discovery.pin import PinManager
from app.discovery.zeroconf_service import DeviceDiscoveryManager, get_local_ip
from app.events.manager import EventManager
from app.file.manager import FileManager
from app.protocol.config import ProtocolConfig, get_default_config
from app.protocol.constants import ProtocolType
from app.session.manager import SessionManager
from app.transfer.coordinator import TransferCoordinator


@dataclass
class AppContext:
    """Singleton context container holding all backend service instances."""
    device_id: uuid.UUID
    device_name: str
    api_port: int = 8000
    udp_port: int = 5001
    role: DeviceRole = DeviceRole.RECEIVER

    discovery_manager: DeviceDiscoveryManager = field(init=False)
    pin_manager: PinManager = field(default_factory=PinManager)
    session_manager: SessionManager = field(init=False)
    file_manager: FileManager = field(default_factory=FileManager)
    event_manager: EventManager = field(init=False)
    transfer_coordinator: TransferCoordinator = field(init=False)

    protocol_configs: Dict[ProtocolType, ProtocolConfig] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.session_manager = SessionManager(local_device_id=self.device_id)
        self.event_manager = EventManager(device_id=self.device_id)
        self.transfer_coordinator = TransferCoordinator(
            file_manager=self.file_manager,
            event_manager=self.event_manager,
        )
        self.discovery_manager = DeviceDiscoveryManager()

        # Initialize default configs
        for proto in (ProtocolType.STOP_AND_WAIT, ProtocolType.GO_BACK_N, ProtocolType.SELECTIVE_REPEAT):
            self.protocol_configs[proto] = get_default_config(proto)


_context_instance: Optional[AppContext] = None


def get_app_context() -> AppContext:
    """Retrieve the global AppContext singleton, populated from env vars if present."""
    global _context_instance
    if _context_instance is None:
        device_id = uuid.uuid4()
        api_port = int(os.environ.get("PEERSHARE_API_PORT", "8000"))
        udp_port = int(os.environ.get("PEERSHARE_UDP_PORT", "5001"))
        role_str = os.environ.get("PEERSHARE_ROLE", "RECEIVER").upper()
        role = DeviceRole.SENDER if role_str == "SENDER" else DeviceRole.RECEIVER
        device_name = os.environ.get("PEERSHARE_DEVICE_NAME", f"PeerShare-{str(device_id)[:6]}")
        storage_dir = os.environ.get("PEERSHARE_STORAGE_DIR", "/tmp/peershare_files")

        _context_instance = AppContext(
            device_id=device_id,
            device_name=device_name,
            api_port=api_port,
            udp_port=udp_port,
            role=role,
        )
        _context_instance.file_manager.storage_dir = storage_dir
        os.makedirs(storage_dir, exist_ok=True)
    return _context_instance


def set_app_context(ctx: AppContext) -> None:
    """Set global AppContext (primarily for testing)."""
    global _context_instance
    _context_instance = ctx

