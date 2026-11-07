"""Visualization Event Manager handling monotonic sequence numbers, ring replay buffers, and WebSocket broadcasts."""

import asyncio
from collections import deque
from datetime import datetime, timezone
import json
import logging
from typing import Any, Dict, List, Optional, Set
import uuid

from fastapi import WebSocket

from app.events.models import EventType, VisualizationEvent

logger = logging.getLogger(__name__)


class EventManager:
    """Central event hub: assigns monotonic sequence IDs, retains replay buffer, and pushes live updates to WebSockets."""

    def __init__(self, device_id: uuid.UUID, max_buffer_size: int = 1000) -> None:
        self.device_id = device_id
        self._current_seq = 0
        self.max_buffer_size = max_buffer_size
        self._event_buffer: deque[VisualizationEvent] = deque(maxlen=max_buffer_size)

        # Active WebSockets
        self._global_subscribers: Set[WebSocket] = set()
        self._transfer_subscribers: Dict[uuid.UUID, Set[WebSocket]] = {}
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    def set_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        """Set active event loop for threadsafe dispatch."""
        self._loop = loop

    def emit_event(
        self,
        event_type: EventType,
        session_id: Optional[uuid.UUID] = None,
        transfer_id: Optional[uuid.UUID] = None,
        data: Optional[Dict[str, Any]] = None,
    ) -> VisualizationEvent:
        """Create and publish an event derived from actual backend operations."""
        self._current_seq += 1
        seq = self._current_seq
        event_id = f"{str(self.device_id)[:8]}-{seq}"

        event = VisualizationEvent(
            event_id=event_id,
            event_seq=seq,
            device_id=self.device_id,
            session_id=session_id,
            transfer_id=transfer_id,
            event=event_type,
            timestamp=datetime.now(timezone.utc),
            data=data or {},
        )

        self._event_buffer.append(event)
        # Safely schedule broadcast to connected websockets
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self._broadcast(event))
        except RuntimeError:
            if self._loop is not None and self._loop.is_running():
                asyncio.run_coroutine_threadsafe(self._broadcast(event), self._loop)

        return event

    async def _broadcast(self, event: VisualizationEvent) -> None:
        """Broadcast serialized event to matching active WebSocket connections."""
        payload_str = json.dumps(event.to_dict())

        # Collect targets
        targets: List[WebSocket] = list(self._global_subscribers)
        if event.transfer_id and event.transfer_id in self._transfer_subscribers:
            targets.extend(self._transfer_subscribers[event.transfer_id])

        disconnected: List[WebSocket] = []
        for ws in set(targets):
            try:
                await ws.send_text(payload_str)
            except Exception:
                disconnected.append(ws)

        for ws in disconnected:
            self._global_subscribers.discard(ws)
            for subs in self._transfer_subscribers.values():
                subs.discard(ws)

    # -----------------------------------------------------------------------
    # Subscription Management
    # -----------------------------------------------------------------------

    def register_global_subscriber(self, ws: WebSocket) -> None:
        """Register a client on ws://localhost:8000/ws/events."""
        self._global_subscribers.add(ws)
        if self._loop is None:
            try:
                self._loop = asyncio.get_running_loop()
            except RuntimeError:
                pass

    def unregister_global_subscriber(self, ws: WebSocket) -> None:
        """Unregister client from global channel."""
        self._global_subscribers.discard(ws)

    def register_transfer_subscriber(self, transfer_id: uuid.UUID, ws: WebSocket) -> None:
        """Register client on ws://localhost:8000/ws/transfers/{transfer_id}."""
        if transfer_id not in self._transfer_subscribers:
            self._transfer_subscribers[transfer_id] = set()
        self._transfer_subscribers[transfer_id].add(ws)
        if self._loop is None:
            try:
                self._loop = asyncio.get_running_loop()
            except RuntimeError:
                pass

    def unregister_transfer_subscriber(self, transfer_id: uuid.UUID, ws: WebSocket) -> None:
        """Unregister client from transfer channel."""
        if transfer_id in self._transfer_subscribers:
            self._transfer_subscribers[transfer_id].discard(ws)
            if not self._transfer_subscribers[transfer_id]:
                del self._transfer_subscribers[transfer_id]

    # -----------------------------------------------------------------------
    # Replay Buffer
    # -----------------------------------------------------------------------

    def get_events_after(
        self,
        last_event_seq: int,
        transfer_id: Optional[uuid.UUID] = None,
    ) -> List[VisualizationEvent]:
        """Return buffered events with sequence numbers strictly greater than last_event_seq."""
        replays: List[VisualizationEvent] = []
        for ev in self._event_buffer:
            if ev.event_seq > last_event_seq:
                if transfer_id is None or ev.transfer_id == transfer_id:
                    replays.append(ev)
        return replays

