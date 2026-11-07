"""Pydantic schemas for REST API request and response contracts."""

from typing import Any, Dict, List, Optional
import uuid
from pydantic import BaseModel, Field

from app.discovery.device import DeviceRole
from app.protocol.constants import ProtocolType


class ApiResponse(BaseModel):
    """Standard API response envelope."""
    success: bool
    message: str = "Operation successful"
    data: Optional[Dict[str, Any]] = None
    error_code: Optional[str] = None


class RoleRequest(BaseModel):
    role: DeviceRole


class ConnectDeviceRequest(BaseModel):
    device_id: Optional[uuid.UUID] = None
    ip_address: Optional[str] = None
    pin: Optional[str] = None
    api_port: Optional[int] = None


class EstablishSessionRequest(BaseModel):
    target_ip: Optional[str] = None
    target_port: Optional[int] = None
    device_id: Optional[uuid.UUID] = None


class ConfigUpdateRequest(BaseModel):
    window_size: Optional[int] = None
    timeout_ms: Optional[int] = None
    max_retries: Optional[int] = None
    packet_loss_percentage: Optional[float] = None
    frame_delay_ms: Optional[int] = None


class TransferCreateRequest(BaseModel):
    file_id: uuid.UUID
    protocol: ProtocolType
    configuration: Optional[Dict[str, Any]] = None


class TransferRejectRequest(BaseModel):
    reason: str = "Receiver rejected the transfer"


class TransferCancelRequest(BaseModel):
    reason: str = "User cancelled the transfer"


# ---------------------------------------------------------------------------
# Peer-to-Peer API Models
# ---------------------------------------------------------------------------

class PeerConnectRequest(BaseModel):
    sender_name: str
    sender_ip: str
    sender_device_id: uuid.UUID
    pin: Optional[str] = None
    api_version: str = "1.0.0"


class PeerSessionRequest(BaseModel):
    session_id: uuid.UUID
    sender_device_id: uuid.UUID
    sender_ip: str
    sender_udp_port: int
    sender_api_port: int


class PeerTransferRequest(BaseModel):
    session_id: uuid.UUID
    transfer_id: uuid.UUID
    file_name: str
    file_size: int
    file_sha256: str
    protocol: ProtocolType
    configuration: Dict[str, Any]
    chunk_size: int = 1024
    total_frames: int


class PeerTransferCompleteRequest(BaseModel):
    transfer_id: uuid.UUID
    integrity_verified: bool
    sha256_hash: str

