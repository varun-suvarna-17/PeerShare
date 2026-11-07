"""WebSocket endpoints for real-time visualization events and event replay."""

import json
import logging
import uuid
from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect

from app.api.context import AppContext, get_app_context

logger = logging.getLogger(__name__)

router = APIRouter(tags=["WebSocket"])


@router.websocket("/ws/events")
async def websocket_global_events(
    websocket: WebSocket,
    ctx: AppContext = Depends(get_app_context),
) -> None:
    """Global WebSocket delivering connection and transfer setup events to the local frontend."""
    await websocket.accept()
    ctx.event_manager.register_global_subscriber(websocket)
    try:
        while True:
            # Receive client messages (e.g. replay request on reconnect)
            text = await websocket.receive_text()
            try:
                msg = json.loads(text)
                if msg.get("type") == "replay":
                    last_seq = int(msg.get("last_event_seq", 0))
                    missed = ctx.event_manager.get_events_after(last_seq)
                    for ev in missed:
                        await websocket.send_text(json.dumps(ev.to_dict()))
            except Exception:
                pass
    except WebSocketDisconnect:
        pass
    finally:
        ctx.event_manager.unregister_global_subscriber(websocket)


@router.websocket("/ws/transfers/{transfer_id}")
async def websocket_transfer_events(
    websocket: WebSocket,
    transfer_id: uuid.UUID,
    ctx: AppContext = Depends(get_app_context),
) -> None:
    """Per-transfer WebSocket delivering frame transmissions, ACKs, timeouts and progress events."""
    await websocket.accept()
    ctx.event_manager.register_transfer_subscriber(transfer_id, websocket)
    try:
        while True:
            text = await websocket.receive_text()
            try:
                msg = json.loads(text)
                if msg.get("type") == "replay":
                    last_seq = int(msg.get("last_event_seq", 0))
                    missed = ctx.event_manager.get_events_after(last_seq, transfer_id=transfer_id)
                    for ev in missed:
                        await websocket.send_text(json.dumps(ev.to_dict()))
            except Exception:
                pass
    except WebSocketDisconnect:
        pass
    finally:
        ctx.event_manager.unregister_transfer_subscriber(transfer_id, websocket)

