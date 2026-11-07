"""Peer-to-peer inter-laptop control REST API endpoints (/peer/*)."""

import logging
from typing import Optional
import uuid

from fastapi import APIRouter, Depends, Header, HTTPException, Request

from app.api.context import AppContext, get_app_context
from app.api.models import (
    ApiResponse,
    PeerConnectRequest,
    PeerSessionRequest,
    PeerTransferCompleteRequest,
    PeerTransferRequest,
)
from app.discovery.device import DeviceRole, DiscoveryMethod
from app.events.models import EventType
from app.protocol.config import ProtocolConfig
from app.protocol.constants import ProtocolType, TransferStatus
from app.session.models import ConnectionStatus, SessionStatus
from app.transfer.models import Transfer

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/peer", tags=["Peer API"])


def verify_session_token(
    x_session_token: Optional[str] = Header(None, alias="X-Session-Token"),
    ctx: AppContext = Depends(get_app_context),
) -> str:
    """Validate incoming X-Session-Token header for peer transfer endpoints."""
    if not x_session_token:
        raise HTTPException(status_code=401, detail="Missing X-Session-Token header")
    if not ctx.session_manager.validate_session_token(x_session_token):
        raise HTTPException(status_code=403, detail="Invalid or expired session token")
    return x_session_token


@router.get("/health", response_model=ApiResponse)
def peer_health(ctx: AppContext = Depends(get_app_context)) -> ApiResponse:
    """Heartbeat check returning API version and role."""
    ctx.session_manager.touch_session()
    return ApiResponse(
        success=True,
        data={
            "api_version": "1.0.0",
            "device_id": str(ctx.device_id),
            "device_name": ctx.device_name,
            "role": ctx.role.value,
        },
    )


@router.post("/connect", response_model=ApiResponse)
def peer_connect(
    req: PeerConnectRequest,
    request: Request,
    ctx: AppContext = Depends(get_app_context),
) -> ApiResponse:
    """Process incoming connection request from a sender on the local network."""
    client_ip = request.client.host if request.client else req.sender_ip
    discovery_method = DiscoveryMethod.MANUAL if req.pin else DiscoveryMethod.ZEROCONF

    # Validate PIN if manual connection method
    if req.pin:
        ok, reason = ctx.pin_manager.verify_pin(req.pin)
        if not ok:
            raise HTTPException(status_code=401, detail=f"PIN validation failed: {reason}")

    connection_req = ctx.session_manager.create_connection_request(
        sender_device_id=req.sender_device_id,
        sender_device_name=req.sender_name,
        sender_ip=client_ip,
        discovery_method=discovery_method,
    )

    ctx.event_manager.emit_event(
        EventType.CONNECTION_REQUEST,
        data={
            "connection_id": str(connection_req.connection_id),
            "sender_device_id": str(req.sender_device_id),
            "sender_name": req.sender_name,
            "sender_ip": client_ip,
            "discovery_method": discovery_method.value,
        },
    )

    return ApiResponse(
        success=True,
        message="Connection request submitted for approval",
        data={
            "connection_id": str(connection_req.connection_id),
            "status": ConnectionStatus.PENDING_APPROVAL.value,
            "receiver_name": ctx.device_name,
        },
    )


@router.get("/connect/{connection_id}/status", response_model=ApiResponse)
def check_connect_status(
    connection_id: uuid.UUID,
    ctx: AppContext = Depends(get_app_context),
) -> ApiResponse:
    """Check approval status of connection request."""
    req = ctx.session_manager.get_connection_request(connection_id)
    if not req:
        raise HTTPException(status_code=404, detail="Connection request not found")

    return ApiResponse(
        success=True,
        data={
            "connection_id": str(connection_id),
            "status": req.status.value,
        },
    )


@router.post("/session", response_model=ApiResponse)
def establish_peer_session(
    req: PeerSessionRequest,
    request: Request,
    ctx: AppContext = Depends(get_app_context),
) -> ApiResponse:
    """Establish common session, exchange UDP ports, and issue session token."""
    client_ip = request.client.host if request.client else req.sender_ip

    session, token = ctx.session_manager.establish_session(
        session_id=req.session_id,
        peer_device_id=req.sender_device_id,
        local_role=DeviceRole.RECEIVER,
        local_ip=request.headers.get("host", "127.0.0.1").split(":")[0],
        peer_ip=client_ip,
        local_api_port=ctx.api_port,
        peer_api_port=req.sender_api_port,
        local_udp_port=ctx.udp_port,
        peer_udp_port=req.sender_udp_port,
    )

    ctx.event_manager.emit_event(
        EventType.SESSION_ESTABLISHED,
        session_id=session.session_id,
        data={"peer_device_id": str(req.sender_device_id), "peer_ip": client_ip},
    )

    return ApiResponse(
        success=True,
        message="Session established successfully",
        data={
            "session_id": str(session.session_id),
            "session_token": token,
            "receiver_udp_port": ctx.udp_port,
            "receiver_ip": session.local_ip,
            "status": session.status.value,
        },
    )


@router.post("/transfers/request", response_model=ApiResponse)
def peer_transfer_request(
    req: PeerTransferRequest,
    ctx: AppContext = Depends(get_app_context),
) -> ApiResponse:
    """Receiver receives transfer request from sender."""
    sess = ctx.session_manager.active_session
    if not sess or sess.session_id != req.session_id:
        raise HTTPException(status_code=400, detail="Invalid session ID")

    cfg = ProtocolConfig(
        protocol=req.protocol,
        sender_window_size=req.configuration.get("window_size", 4),
        receiver_window_size=req.configuration.get("window_size", 4) if req.protocol == ProtocolType.SELECTIVE_REPEAT else 1,
        timeout_ms=req.configuration.get("timeout_ms", 1000),
        max_retries=req.configuration.get("max_retries", 5),
        packet_loss_percentage=req.configuration.get("packet_loss_percentage", 0.0),
        frame_delay_ms=req.configuration.get("frame_delay_ms", 100),
    )

    transfer = Transfer(
        transfer_id=req.transfer_id,
        session_id=req.session_id,
        file_id=uuid.uuid4(),
        file_name=req.file_name,
        file_size=req.file_size,
        file_sha256=req.file_sha256,
        protocol=req.protocol,
        configuration=cfg,
        total_frames=req.total_frames,
        status=TransferStatus.PENDING,
    )
    ctx.transfer_coordinator.register_transfer(transfer)

    ctx.event_manager.emit_event(
        EventType.TRANSFER_REQUEST,
        session_id=req.session_id,
        transfer_id=req.transfer_id,
        data={
            "file_name": req.file_name,
            "file_size": req.file_size,
            "protocol": req.protocol.value,
        },
    )

    return ApiResponse(
        success=True,
        message="Transfer request recorded",
        data={"transfer_id": str(req.transfer_id), "status": "pending_acceptance"},
    )


@router.post("/transfers/{transfer_id}/ready", response_model=ApiResponse)
def peer_receiver_ready(
    transfer_id: uuid.UUID,
    token: str = Depends(verify_session_token),
    ctx: AppContext = Depends(get_app_context),
) -> ApiResponse:
    """Signal receiver UDP port is open and ready."""
    ctx.session_manager.set_receiver_ready(True)
    return ApiResponse(success=True, message="Receiver confirmed ready")


@router.post("/transfers/{transfer_id}/start", response_model=ApiResponse)
def peer_transfer_start(
    transfer_id: uuid.UUID,
    token: str = Depends(verify_session_token),
    ctx: AppContext = Depends(get_app_context),
) -> ApiResponse:
    """Peer informs transfer started."""
    ctx.event_manager.emit_event(
        EventType.TRANSFER_STARTED,
        session_id=ctx.session_manager.active_session.session_id if ctx.session_manager.active_session else None,
        transfer_id=transfer_id,
    )
    return ApiResponse(success=True, message="Transfer start acknowledged")


@router.post("/transfers/{transfer_id}/accept", response_model=ApiResponse)
def peer_transfer_accept(
    transfer_id: uuid.UUID,
    token: str = Depends(verify_session_token),
    ctx: AppContext = Depends(get_app_context),
) -> ApiResponse:
    """Receiver informs sender transfer was accepted."""
    transfer = ctx.transfer_coordinator.get_transfer(transfer_id)
    if transfer:
        transfer.status = TransferStatus.TRANSFERRING
    ctx.event_manager.emit_event(
        EventType.TRANSFER_ACCEPTED,
        session_id=ctx.session_manager.active_session.session_id if ctx.session_manager.active_session else None,
        transfer_id=transfer_id,
    )
    return ApiResponse(success=True, message="Transfer accepted notification recorded")


@router.post("/transfers/{transfer_id}/reject", response_model=ApiResponse)
def peer_transfer_reject(
    transfer_id: uuid.UUID,
    token: str = Depends(verify_session_token),
    ctx: AppContext = Depends(get_app_context),
) -> ApiResponse:
    """Receiver informs sender transfer was rejected."""
    transfer = ctx.transfer_coordinator.get_transfer(transfer_id)
    if transfer:
        transfer.status = TransferStatus.CANCELLED
    ctx.event_manager.emit_event(
        EventType.TRANSFER_REJECTED,
        session_id=ctx.session_manager.active_session.session_id if ctx.session_manager.active_session else None,
        transfer_id=transfer_id,
    )
    return ApiResponse(success=True, message="Transfer rejected notification recorded")


@router.post("/transfers/{transfer_id}/cancel", response_model=ApiResponse)
def peer_transfer_cancel(
    transfer_id: uuid.UUID,
    token: str = Depends(verify_session_token),
    ctx: AppContext = Depends(get_app_context),
) -> ApiResponse:
    """Peer informs transfer cancelled."""
    transfer = ctx.transfer_coordinator.get_transfer(transfer_id)
    if transfer:
        transfer.status = TransferStatus.CANCELLED
    ctx.event_manager.emit_event(
        EventType.TRANSFER_CANCELLED,
        session_id=ctx.session_manager.active_session.session_id if ctx.session_manager.active_session else None,
        transfer_id=transfer_id,
    )
    return ApiResponse(success=True, message="Transfer cancelled notification recorded")



@router.post("/transfers/{transfer_id}/complete", response_model=ApiResponse)
def peer_transfer_complete(
    transfer_id: uuid.UUID,
    req: PeerTransferCompleteRequest,
    token: str = Depends(verify_session_token),
    ctx: AppContext = Depends(get_app_context),
) -> ApiResponse:
    """Receiver sends final SHA-256 integrity verification result back to sender."""
    transfer = ctx.transfer_coordinator.get_transfer(transfer_id)
    if transfer:
        transfer.integrity_verified = req.integrity_verified
        transfer.status = TransferStatus.COMPLETED if req.integrity_verified else TransferStatus.FAILED

    ctx.event_manager.emit_event(
        EventType.TRANSFER_COMPLETED if req.integrity_verified else EventType.TRANSFER_FAILED,
        session_id=ctx.session_manager.active_session.session_id if ctx.session_manager.active_session else None,
        transfer_id=transfer_id,
        data={"integrity_verified": req.integrity_verified, "sha256_hash": req.sha256_hash},
    )

    return ApiResponse(success=True, message="Completion status received")


@router.delete("/session", response_model=ApiResponse)
def peer_close_session(
    token: str = Depends(verify_session_token),
    ctx: AppContext = Depends(get_app_context),
) -> ApiResponse:
    """Peer session teardown."""
    ctx.session_manager.close_session()
    ctx.event_manager.emit_event(EventType.SESSION_ENDED)
    return ApiResponse(success=True, message="Session closed")

