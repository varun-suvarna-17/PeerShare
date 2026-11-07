"""Frontend-facing local REST API endpoints (/api/*)."""

import os
import tempfile
from typing import Any, Dict, List
import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
import httpx

from app.api.context import AppContext, get_app_context
from app.api.models import (
    ApiResponse,
    ConfigUpdateRequest,
    ConnectDeviceRequest,
    EstablishSessionRequest,
    RoleRequest,
    TransferCancelRequest,
    TransferCreateRequest,
    TransferRejectRequest,
)
from app.discovery.device import DeviceRole, DiscoveryMethod
from app.discovery.zeroconf_service import get_local_ip
from app.events.models import EventType
from app.file.models import MAX_FILE_SIZE
from app.protocol.config import ProtocolConfig
from app.protocol.constants import ProtocolType, TransferStatus
from app.session.models import ConnectionStatus, SessionStatus
from app.transfer.models import Transfer

router = APIRouter(prefix="/api", tags=["Local API"])


# ---------------------------------------------------------------------------
# Device & Network APIs
# ---------------------------------------------------------------------------

@router.post("/role", response_model=ApiResponse)
async def set_role(
    req: RoleRequest,
    ctx: AppContext = Depends(get_app_context),
) -> ApiResponse:
    """Set device role to SENDER or RECEIVER."""
    ctx.role = req.role
    if ctx.role == DeviceRole.RECEIVER:
        await ctx.discovery_manager.start_advertising(
            device_id=ctx.device_id,
            device_name=ctx.device_name,
            api_port=ctx.api_port,
            udp_port=ctx.udp_port,
        )
    else:
        await ctx.discovery_manager.stop_advertising()

    return ApiResponse(
        success=True,
        message=f"Role set to {req.role.value}",
        data={"role": req.role.value, "device_id": str(ctx.device_id)},
    )


@router.get("/network/status", response_model=ApiResponse)
def get_network_status(ctx: AppContext = Depends(get_app_context)) -> ApiResponse:
    """Get local IP address and connectivity status."""
    local_ip = get_local_ip()
    return ApiResponse(
        success=True,
        data={
            "local_ip": local_ip,
            "api_port": ctx.api_port,
            "udp_port": ctx.udp_port,
            "device_id": str(ctx.device_id),
            "device_name": ctx.device_name,
            "role": ctx.role.value,
        },
    )


@router.get("/devices", response_model=ApiResponse)
def get_discovered_devices(ctx: AppContext = Depends(get_app_context)) -> ApiResponse:
    """List all currently discovered receiver devices."""
    devices = ctx.discovery_manager.get_discovered_devices()
    data = [
        {
            "device_id": str(d.device_id),
            "device_name": d.device_name,
            "ip_address": d.ip_address,
            "api_port": d.api_port,
            "udp_port": d.udp_port,
            "status": d.status.value,
            "discovery_method": d.discovery_method.value,
        }
        for d in devices
    ]
    return ApiResponse(success=True, data={"devices": data})


@router.post("/devices/discover", response_model=ApiResponse)
async def start_discovery(ctx: AppContext = Depends(get_app_context)) -> ApiResponse:
    """Trigger or refresh Zeroconf device discovery."""
    await ctx.discovery_manager.start_discovery()
    return ApiResponse(success=True, message="Discovery started")


@router.post("/devices/pin", response_model=ApiResponse)
def generate_pin(ctx: AppContext = Depends(get_app_context)) -> ApiResponse:
    """Generate temporary 6-digit connection PIN on the Receiver."""
    pin, expires_in = ctx.pin_manager.generate_pin()
    return ApiResponse(
        success=True,
        message="PIN generated successfully",
        data={
            "pin": pin,
            "ip_address": get_local_ip(),
            "expires_in": expires_in,
        },
    )


@router.post("/devices/connect", response_model=ApiResponse)
async def connect_device(
    req: ConnectDeviceRequest,
    ctx: AppContext = Depends(get_app_context),
) -> ApiResponse:
    """Initiate connection to receiver via discovered device_id or manual IP + PIN."""
    target_ip = req.ip_address
    target_port = req.api_port or 8000
    pin = req.pin

    if req.device_id:
        devices = ctx.discovery_manager.get_discovered_devices()
        matching = [d for d in devices if d.device_id == req.device_id]
        if not matching:
            raise HTTPException(status_code=404, detail="Device not found in discovery list")
        target_ip = matching[0].ip_address
        target_port = req.api_port or matching[0].api_port

    if not target_ip:
        raise HTTPException(status_code=400, detail="Must provide device_id or ip_address")

    # Call peer receiver endpoint: POST http://<target_ip>:<target_port>/peer/connect
    peer_url = f"http://{target_ip}:{target_port}/peer/connect"
    payload = {
        "sender_name": ctx.device_name,
        "sender_ip": get_local_ip(),
        "sender_device_id": str(ctx.device_id),
        "pin": pin,
        "api_version": "1.0.0",
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(peer_url, json=payload)
            resp_data = resp.json()
            if not resp_data.get("success"):
                raise HTTPException(status_code=resp.status_code, detail=resp_data.get("message", "Connection failed"))
            return ApiResponse(success=True, data=resp_data.get("data"), message=resp_data.get("message"))
    except httpx.RequestError as exc:
        raise HTTPException(status_code=502, detail=f"Failed to reach peer: {exc}")


# ---------------------------------------------------------------------------
# Connection Approvals (Receiver-side)
# ---------------------------------------------------------------------------

@router.get("/connections/pending", response_model=ApiResponse)
def get_pending_connections(ctx: AppContext = Depends(get_app_context)) -> ApiResponse:
    """Retrieve connection requests awaiting receiver approval."""
    pending = ctx.session_manager.get_pending_requests()
    data = [
        {
            "connection_id": str(r.connection_id),
            "sender_device_id": str(r.sender_device_id),
            "sender_device_name": r.sender_device_name,
            "sender_ip": r.sender_ip,
            "discovery_method": r.discovery_method.value,
            "requested_at": r.requested_at.isoformat(),
            "expires_at": r.expires_at.isoformat(),
        }
        for r in pending
    ]
    return ApiResponse(success=True, data={"connections": data})


@router.post("/connections/{connection_id}/approve", response_model=ApiResponse)
def approve_connection(
    connection_id: uuid.UUID,
    ctx: AppContext = Depends(get_app_context),
) -> ApiResponse:
    """Approve incoming connection request."""
    ok, msg = ctx.session_manager.approve_connection(connection_id)
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    ctx.event_manager.emit_event(
        EventType.CONNECTION_APPROVED,
        data={"connection_id": str(connection_id)},
    )
    return ApiResponse(success=True, message="Connection approved")


@router.post("/connections/{connection_id}/reject", response_model=ApiResponse)
def reject_connection(
    connection_id: uuid.UUID,
    ctx: AppContext = Depends(get_app_context),
) -> ApiResponse:
    """Reject incoming connection request."""
    ok, msg = ctx.session_manager.reject_connection(connection_id)
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    ctx.event_manager.emit_event(
        EventType.CONNECTION_REJECTED,
        data={"connection_id": str(connection_id)},
    )
    return ApiResponse(success=True, message="Connection rejected")


# ---------------------------------------------------------------------------
# Session APIs
# ---------------------------------------------------------------------------

@router.get("/session", response_model=ApiResponse)
def get_session(ctx: AppContext = Depends(get_app_context)) -> ApiResponse:
    """Retrieve current session information."""
    sess = ctx.session_manager.active_session
    if sess is None:
        return ApiResponse(success=True, data=None, message="No active session")
    return ApiResponse(
        success=True,
        data={
            "session_id": str(sess.session_id),
            "status": sess.status.value,
            "local_role": sess.local_role.value,
            "peer_ip": sess.peer_ip,
            "peer_api_port": sess.peer_api_port,
            "local_udp_port": sess.local_udp_port,
            "peer_udp_port": sess.peer_udp_port,
            "receiver_ready": sess.receiver_ready,
        },
    )


@router.delete("/session", response_model=ApiResponse)
def delete_session(ctx: AppContext = Depends(get_app_context)) -> ApiResponse:
    """End and disconnect current session."""
    ctx.session_manager.close_session()
    ctx.event_manager.emit_event(EventType.SESSION_ENDED)
    return ApiResponse(success=True, message="Session ended")


@router.post("/session/establish", response_model=ApiResponse)
async def establish_session_with_peer(
    req: EstablishSessionRequest,
    ctx: AppContext = Depends(get_app_context),
) -> ApiResponse:
    """Sender establishes mutual session with peer receiver after connection is approved."""
    target_ip = req.target_ip
    target_port = req.target_port or 8000

    if req.device_id:
        devices = ctx.discovery_manager.get_discovered_devices()
        matching = [d for d in devices if d.device_id == req.device_id]
        if matching:
            target_ip = matching[0].ip_address
            target_port = req.target_port or matching[0].api_port

    if not target_ip:
        raise HTTPException(status_code=400, detail="Must provide target_ip or device_id")

    session_id = uuid.uuid4()
    payload = {
        "session_id": str(session_id),
        "sender_device_id": str(ctx.device_id),
        "sender_ip": get_local_ip(),
        "sender_udp_port": ctx.udp_port,
        "sender_api_port": ctx.api_port,
    }

    peer_url = f"http://{target_ip}:{target_port}/peer/session"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(peer_url, json=payload)
            resp_data = resp.json()
            if not resp_data.get("success"):
                raise HTTPException(status_code=resp.status_code, detail=resp_data.get("message", "Session establishment failed"))
            data = resp_data.get("data", {})
            token = data.get("session_token")
            peer_udp_port = int(data.get("receiver_udp_port", 5001))
            peer_ip = str(data.get("receiver_ip", target_ip))

            # Establish locally on sender
            session, _ = ctx.session_manager.establish_session(
                session_id=session_id,
                peer_device_id=req.device_id or uuid.uuid4(),
                local_role=DeviceRole.SENDER,
                local_ip=get_local_ip(),
                peer_ip=peer_ip,
                local_api_port=ctx.api_port,
                peer_api_port=target_port,
                local_udp_port=ctx.udp_port,
                peer_udp_port=peer_udp_port,
            )
            ctx.session_manager._session_token = token

            ctx.event_manager.emit_event(
                EventType.SESSION_ESTABLISHED,
                session_id=session_id,
                data={"peer_ip": peer_ip, "peer_udp_port": peer_udp_port},
            )

            return ApiResponse(
                success=True,
                message="Session established successfully",
                data={
                    "session_id": str(session_id),
                    "status": "connected",
                    "peer_ip": peer_ip,
                    "peer_api_port": target_port,
                    "peer_udp_port": peer_udp_port,
                    "session_token": token,
                },
            )
    except httpx.RequestError as exc:
        raise HTTPException(status_code=502, detail=f"Failed to communicate with peer: {exc}")



# ---------------------------------------------------------------------------
# File Selection APIs
# ---------------------------------------------------------------------------

@router.post("/files/select", response_model=ApiResponse)
async def select_file(
    file: UploadFile = File(...),
    ctx: AppContext = Depends(get_app_context),
) -> ApiResponse:
    """Upload/select a local file on the sender, enforcing the 5 MB limit."""
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="File too large (exceeds 5 MB limit)")

    # Save to temp file
    temp_dir = tempfile.gettempdir()
    safe_name = file.filename or "uploaded_file"
    temp_path = os.path.join(temp_dir, f"peershare_{uuid.uuid4()}_{safe_name}")
    with open(temp_path, "wb") as f:
        f.write(content)

    meta = ctx.file_manager.register_file(temp_path, custom_name=safe_name)

    return ApiResponse(
        success=True,
        message="File selected successfully",
        data={
            "file_id": str(meta.file_id),
            "file_name": meta.file_name,
            "file_size": meta.file_size,
            "file_type": meta.file_type,
            "file_sha256": meta.sha256_hash,
            "total_frames": meta.total_frames,
        },
    )


@router.get("/files/{file_id}", response_model=ApiResponse)
def get_file_info(file_id: uuid.UUID, ctx: AppContext = Depends(get_app_context)) -> ApiResponse:
    """Retrieve metadata of registered file."""
    meta = ctx.file_manager.registered_files.get(file_id)
    if not meta:
        raise HTTPException(status_code=404, detail="File not found")
    return ApiResponse(
        success=True,
        data={
            "file_id": str(meta.file_id),
            "file_name": meta.file_name,
            "file_size": meta.file_size,
            "file_type": meta.file_type,
            "file_sha256": meta.sha256_hash,
            "total_frames": meta.total_frames,
        },
    )


# ---------------------------------------------------------------------------
# Protocol Configuration APIs
# ---------------------------------------------------------------------------

@router.get("/protocols", response_model=ApiResponse)
def get_supported_protocols() -> ApiResponse:
    """Get list of supported ARQ protocols."""
    return ApiResponse(
        success=True,
        data={
            "protocols": [
                {"id": "stop_and_wait", "name": "Stop-and-Wait (One-Bit)"},
                {"id": "go_back_n", "name": "Go-Back-N"},
                {"id": "selective_repeat", "name": "Selective Repeat"},
            ]
        },
    )


@router.get("/config", response_model=ApiResponse)
def get_config(
    protocol: ProtocolType = ProtocolType.SELECTIVE_REPEAT,
    ctx: AppContext = Depends(get_app_context),
) -> ApiResponse:
    """Retrieve transfer configuration for protocol."""
    cfg = ctx.protocol_configs.get(protocol)
    if not cfg:
        raise HTTPException(status_code=404, detail="Configuration not found")
    return ApiResponse(
        success=True,
        data={
            "protocol": cfg.protocol.value,
            "sender_window_size": cfg.sender_window_size,
            "receiver_window_size": cfg.receiver_window_size,
            "timeout_ms": cfg.timeout_ms,
            "max_retries": cfg.max_retries,
            "packet_loss_percentage": cfg.packet_loss_percentage,
            "frame_delay_ms": cfg.frame_delay_ms,
        },
    )


@router.put("/config", response_model=ApiResponse)
def update_config(
    req: ConfigUpdateRequest,
    protocol: ProtocolType = ProtocolType.SELECTIVE_REPEAT,
    ctx: AppContext = Depends(get_app_context),
) -> ApiResponse:
    """Update transfer configuration."""
    cfg = ctx.protocol_configs.get(protocol)
    if not cfg:
        raise HTTPException(status_code=404, detail="Configuration not found")

    if req.window_size is not None:
        cfg.sender_window_size = req.window_size
        if protocol == ProtocolType.SELECTIVE_REPEAT:
            cfg.receiver_window_size = req.window_size
    if req.timeout_ms is not None:
        cfg.timeout_ms = req.timeout_ms
    if req.max_retries is not None:
        cfg.max_retries = req.max_retries
    if req.packet_loss_percentage is not None:
        cfg.packet_loss_percentage = req.packet_loss_percentage
    if req.frame_delay_ms is not None:
        cfg.frame_delay_ms = req.frame_delay_ms

    return ApiResponse(success=True, message="Configuration updated")


# ---------------------------------------------------------------------------
# Transfer Lifecycle APIs
# ---------------------------------------------------------------------------

@router.post("/transfers/request", response_model=ApiResponse)
async def request_transfer(
    req: TransferCreateRequest,
    ctx: AppContext = Depends(get_app_context),
) -> ApiResponse:
    """Sender sends transfer request to connected peer receiver."""
    sess = ctx.session_manager.active_session
    if not sess or sess.status != SessionStatus.ESTABLISHED:
        raise HTTPException(status_code=400, detail="No established session with peer")

    meta = ctx.file_manager.registered_files.get(req.file_id)
    if not meta:
        raise HTTPException(status_code=404, detail="Selected file not found")

    transfer_id = uuid.uuid4()
    cfg = ctx.protocol_configs.get(req.protocol)
    assert cfg is not None

    transfer = Transfer(
        transfer_id=transfer_id,
        session_id=sess.session_id,
        file_id=meta.file_id,
        file_name=meta.file_name,
        file_size=meta.file_size,
        file_sha256=meta.sha256_hash,
        protocol=req.protocol,
        configuration=cfg,
        total_frames=meta.total_frames,
    )
    ctx.transfer_coordinator.register_transfer(transfer)

    # Call peer /peer/transfers/request
    peer_url = f"http://{sess.peer_ip}:{sess.peer_api_port}/peer/transfers/request"
    peer_payload = {
        "session_id": str(sess.session_id),
        "transfer_id": str(transfer_id),
        "file_name": meta.file_name,
        "file_size": meta.file_size,
        "file_sha256": meta.sha256_hash,
        "protocol": req.protocol.value,
        "configuration": {
            "window_size": cfg.sender_window_size,
            "timeout_ms": cfg.timeout_ms,
            "max_retries": cfg.max_retries,
            "packet_loss_percentage": cfg.packet_loss_percentage,
            "frame_delay_ms": cfg.frame_delay_ms,
        },
        "chunk_size": meta.chunk_size,
        "total_frames": meta.total_frames,
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(peer_url, json=peer_payload)
            resp_data = resp.json()
            if not resp_data.get("success"):
                raise HTTPException(status_code=resp.status_code, detail=resp_data.get("message"))
    except httpx.RequestError as exc:
        raise HTTPException(status_code=502, detail=f"Failed to communicate with peer receiver: {exc}")

    ctx.event_manager.emit_event(
        EventType.TRANSFER_REQUEST,
        session_id=sess.session_id,
        transfer_id=transfer_id,
        data={"file_name": meta.file_name, "file_size": meta.file_size},
    )

    return ApiResponse(
        success=True,
        message="Transfer request sent to peer",
        data={"transfer_id": str(transfer_id), "status": "pending_acceptance"},
    )


@router.get("/transfers/pending", response_model=ApiResponse)
def get_pending_transfers(ctx: AppContext = Depends(get_app_context)) -> ApiResponse:
    """Retrieve pending incoming transfers on receiver."""
    pending = [
        {
            "transfer_id": str(t.transfer_id),
            "file_name": t.file_name,
            "file_size": t.file_size,
            "protocol": t.protocol.value,
            "status": t.status.value,
        }
        for t in ctx.transfer_coordinator.active_transfers.values()
        if t.status == TransferStatus.PENDING
    ]
    return ApiResponse(success=True, data={"transfers": pending})


@router.post("/transfers/{transfer_id}/accept", response_model=ApiResponse)
async def accept_transfer(
    transfer_id: uuid.UUID,
    ctx: AppContext = Depends(get_app_context),
) -> ApiResponse:
    """Receiver accepts transfer request, opens UDP socket, notifies sender."""
    transfer = ctx.transfer_coordinator.get_transfer(transfer_id)
    if not transfer:
        raise HTTPException(status_code=404, detail="Transfer not found")

    sess = ctx.session_manager.active_session
    ready_event = asyncio.Event()

    # Launch receiver UDP task
    asyncio.create_task(
        ctx.transfer_coordinator.run_receiver_transfer(
            transfer=transfer,
            local_udp_port=ctx.udp_port,
            linger_seconds=1.0,
            ready_event=ready_event,
        )
    )

    try:
        await asyncio.wait_for(ready_event.wait(), timeout=3.0)
    except asyncio.TimeoutError:
        raise HTTPException(status_code=500, detail="Failed to initialize receiver UDP socket")

    ctx.event_manager.emit_event(
        EventType.TRANSFER_ACCEPTED,
        session_id=transfer.session_id,
        transfer_id=transfer.transfer_id,
    )

    # Signal peer sender ready if connected
    if sess and sess.peer_ip and sess.peer_api_port:
        peer_url = f"http://{sess.peer_ip}:{sess.peer_api_port}/peer/transfers/{transfer_id}/ready"
        headers = {"X-Session-Token": ctx.session_manager._session_token or ""}
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                await client.post(peer_url, headers=headers)
        except Exception:
            pass

    return ApiResponse(success=True, message="Transfer accepted", data={"transfer_id": str(transfer_id)})


@router.post("/transfers/{transfer_id}/start", response_model=ApiResponse)
async def start_transfer(
    transfer_id: uuid.UUID,
    ctx: AppContext = Depends(get_app_context),
) -> ApiResponse:
    """Sender starts an accepted transfer."""
    transfer = ctx.transfer_coordinator.get_transfer(transfer_id)
    if not transfer:
        raise HTTPException(status_code=404, detail="Transfer not found")

    sess = ctx.session_manager.active_session
    if not sess:
        raise HTTPException(status_code=400, detail="No active session to start transfer")

    peer_host = sess.peer_ip
    peer_port = sess.peer_udp_port

    # Run sender transfer in background
    asyncio.create_task(
        ctx.transfer_coordinator.run_sender_transfer(
            transfer=transfer,
            peer_udp_host=peer_host,
            peer_udp_port=peer_port,
        )
    )

    ctx.event_manager.emit_event(
        EventType.TRANSFER_STARTED,
        session_id=transfer.session_id,
        transfer_id=transfer.transfer_id,
        data={"protocol": transfer.protocol.value, "total_frames": transfer.total_frames},
    )

    return ApiResponse(
        success=True,
        message="Transfer started",
        data={
            "transfer_id": str(transfer_id),
            "status": "transferring",
            "protocol": transfer.protocol.value,
        },
    )


@router.post("/transfers/{transfer_id}/cancel", response_model=ApiResponse)
async def cancel_transfer(
    transfer_id: uuid.UUID,
    req: Optional[TransferCancelRequest] = None,
    ctx: AppContext = Depends(get_app_context),
) -> ApiResponse:
    """Cancel an ongoing transfer."""
    transfer = ctx.transfer_coordinator.get_transfer(transfer_id)
    if not transfer:
        raise HTTPException(status_code=404, detail="Transfer not found")

    reason = req.reason if req else "Transfer cancelled by user"
    transfer.status = TransferStatus.CANCELLED
    transfer.failure_reason = reason

    ctx.event_manager.emit_event(
        EventType.TRANSFER_CANCELLED,
        session_id=transfer.session_id,
        transfer_id=transfer.transfer_id,
        data={"reason": reason},
    )

    return ApiResponse(
        success=True,
        message="Transfer cancellation initiated",
        data={"transfer_id": str(transfer_id), "status": "cancelled"},
    )



@router.post("/transfers/{transfer_id}/reject", response_model=ApiResponse)
async def reject_transfer(
    transfer_id: uuid.UUID,
    req: TransferRejectRequest,
    ctx: AppContext = Depends(get_app_context),
) -> ApiResponse:
    """Receiver rejects transfer request."""
    transfer = ctx.transfer_coordinator.get_transfer(transfer_id)
    if not transfer:
        raise HTTPException(status_code=404, detail="Transfer not found")

    transfer.status = TransferStatus.CANCELLED
    ctx.event_manager.emit_event(
        EventType.TRANSFER_REJECTED,
        session_id=transfer.session_id,
        transfer_id=transfer.transfer_id,
        data={"reason": req.reason},
    )
    return ApiResponse(success=True, message="Transfer rejected")


@router.get("/transfers/{transfer_id}", response_model=ApiResponse)
def get_transfer_status(
    transfer_id: uuid.UUID,
    ctx: AppContext = Depends(get_app_context),
) -> ApiResponse:
    """Get active transfer progress and status."""
    transfer = ctx.transfer_coordinator.get_transfer(transfer_id)
    if not transfer:
        raise HTTPException(status_code=404, detail="Transfer not found")

    return ApiResponse(
        success=True,
        data={
            "transfer_id": str(transfer.transfer_id),
            "file_name": transfer.file_name,
            "file_size": transfer.file_size,
            "protocol": transfer.protocol.value,
            "status": transfer.status.value,
            "integrity_verified": transfer.integrity_verified,
        },
    )


@router.get("/transfers/{transfer_id}/report", response_model=ApiResponse)
def get_transfer_report(
    transfer_id: uuid.UUID,
    ctx: AppContext = Depends(get_app_context),
) -> ApiResponse:
    """Retrieve final transfer statistics report."""
    transfer = ctx.transfer_coordinator.get_transfer(transfer_id)
    if not transfer:
        raise HTTPException(status_code=404, detail="Transfer not found")

    return ApiResponse(
        success=True,
        data={
            "transfer_id": str(transfer.transfer_id),
            "status": transfer.status.value,
            "protocol": transfer.protocol.value,
            "total_frames": transfer.total_frames,
            "total_transmissions": transfer.total_transmissions,
            "integrity_verified": transfer.integrity_verified,
            "reconstructed_path": transfer.reconstructed_path,
        },
    )

