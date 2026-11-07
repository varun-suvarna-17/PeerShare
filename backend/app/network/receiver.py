"""Asynchronous UDP Receiver handler for PeerShare."""

import asyncio
import logging
import time
from typing import Optional, Set, Tuple

from app.events.models import EventType
from app.protocol.base import BaseReceiver
from app.protocol.constants import TransferStatus
from app.protocol.exceptions import CorruptedFrameError, FrameDecodeError
from app.protocol.frame import AckFrame, DataFrame, decode_frame
from app.network.loss import PacketLossSimulator
from app.network.protocol import PeerShareDatagramProtocol

logger = logging.getLogger(__name__)


class UdpReceiver:
    """Asynchronous UDP Receiver integrating ARQ protocol logic with UDP transport."""

    def __init__(
        self,
        arq_receiver: BaseReceiver,
        host: str = "127.0.0.1",
        port: int = 0,
        loss_simulator: Optional[PacketLossSimulator] = None,
        corrupt_indices: Optional[Set[int]] = None,
        event_manager: Optional[object] = None,
    ) -> None:
        self.arq_receiver = arq_receiver
        self._bind_host = host
        self._bind_port = port
        self.loss_simulator = loss_simulator
        self.corrupt_indices = corrupt_indices or set()
        self.event_manager = event_manager

        self.transport: Optional[asyncio.DatagramTransport] = None
        self.protocol: Optional[PeerShareDatagramProtocol] = None
        self._finished_event = asyncio.Event()
        self._is_closed = False

    async def start(self) -> None:
        """Bind the UDP socket and start receiving datagrams."""
        loop = asyncio.get_running_loop()
        transport, protocol = await loop.create_datagram_endpoint(
            lambda: PeerShareDatagramProtocol(
                on_datagram_received=self._on_datagram_received,
                on_error=self._on_socket_error,
            ),
            local_addr=(self._bind_host, self._bind_port),
        )
        self.transport = transport
        self.protocol = protocol
        await protocol.wait_connected()
        logger.debug("UdpReceiver bound to %s", self.local_addr)

    def _on_datagram_received(self, data: bytes, addr: Tuple[str, int]) -> None:
        """Handle incoming raw UDP datagram from peer."""
        if self._is_closed:
            return

        # Attempt to decode frame
        try:
            frame = decode_frame(data)
        except CorruptedFrameError:
            self.arq_receiver.stats.corrupted_frames += 1
            logger.debug("Received corrupted frame from %s (CRC failure)", addr)
            if self.event_manager is not None:
                self.event_manager.emit_event(
                    EventType.FRAME_CORRUPTED,
                    session_id=self.arq_receiver.session_id,
                    transfer_id=self.arq_receiver.transfer_id,
                    data={"reason": "CRC32 checksum mismatch"},
                )
            return
        except FrameDecodeError as exc:
            logger.debug("Received invalid frame from %s: %s", addr, exc)
            return

        if not isinstance(frame, DataFrame):
            logger.debug("Expected DataFrame, got %s from %s", type(frame).__name__, addr)
            return

        if self.event_manager is not None:
            self.event_manager.emit_event(
                EventType.FRAME_RECEIVED,
                session_id=self.arq_receiver.session_id,
                transfer_id=self.arq_receiver.transfer_id,
                data={
                    "sequence_number": frame.sequence_number,
                    "frame_index": frame.frame_index,
                    "payload_length": len(frame.payload),
                    "frame_type": frame.frame_type.name,
                },
            )

        # Check for simulated corruption before processing
        if frame.frame_index in self.corrupt_indices:
            self.corrupt_indices.remove(frame.frame_index)
            self.arq_receiver.stats.corrupted_frames += 1
            logger.debug("Simulated corruption for frame_index %d", frame.frame_index)
            return

        # Pass valid frame to the ARQ protocol receiver
        now = time.monotonic()
        prev_discarded = self.arq_receiver.stats.discarded_frames
        ack = self.arq_receiver.handle_data_frame(frame, now)

        if self.arq_receiver.stats.discarded_frames > prev_discarded and self.event_manager is not None:
            self.event_manager.emit_event(
                EventType.FRAME_DISCARDED,
                session_id=self.arq_receiver.session_id,
                transfer_id=self.arq_receiver.transfer_id,
                data={
                    "frame_index": frame.frame_index,
                    "sequence_number": frame.sequence_number,
                    "reason": "duplicate",
                },
            )

        if hasattr(self.arq_receiver, "buffered_frames") and frame.frame_index in getattr(self.arq_receiver, "buffered_frames", {}) and self.event_manager is not None:
            self.event_manager.emit_event(
                EventType.FRAME_BUFFERED,
                session_id=self.arq_receiver.session_id,
                transfer_id=self.arq_receiver.transfer_id,
                data={
                    "frame_index": frame.frame_index,
                    "sequence_number": frame.sequence_number,
                    "buffered_count": len(getattr(self.arq_receiver, "buffered_frames", {})),
                },
            )

        if ack is not None and self.transport is not None:
            # Check for simulated ACK drop
            if self.loss_simulator and self.loss_simulator.should_drop(ack.frame_index):
                self.arq_receiver.stats.dropped_ack_frames += 1
                logger.debug("Simulated drop for ACK of frame_index %d", ack.frame_index)
                if self.event_manager is not None:
                    self.event_manager.emit_event(
                        EventType.ACK_LOST,
                        session_id=self.arq_receiver.session_id,
                        transfer_id=self.arq_receiver.transfer_id,
                        data={"frame_index": ack.frame_index, "ack_number": ack.ack_number},
                    )
            else:
                ack_bytes = ack.encode()
                self.transport.sendto(ack_bytes, addr)
                if self.event_manager is not None:
                    self.event_manager.emit_event(
                        EventType.ACK_SENT,
                        session_id=self.arq_receiver.session_id,
                        transfer_id=self.arq_receiver.transfer_id,
                        data={
                            "ack_number": ack.ack_number,
                            "frame_index": ack.frame_index,
                            "ack_type": ack.ack_type.name,
                        },
                    )

        if self.arq_receiver.is_finished():
            self._finished_event.set()

    def _on_socket_error(self, exc: Exception) -> None:
        logger.warning("UdpReceiver socket error: %s", exc)

    @property
    def local_addr(self) -> Optional[Tuple[str, int]]:
        """Return the local socket address."""
        if self.protocol:
            return self.protocol.local_addr
        return None

    @property
    def local_port(self) -> int:
        """Return the bound local UDP port."""
        addr = self.local_addr
        if addr is not None:
            return addr[1]
        raise RuntimeError("Receiver socket is not bound")

    async def wait_complete(self, timeout: Optional[float] = None) -> bool:
        """Wait until file transfer completion or timeout."""
        try:
            if timeout is not None:
                await asyncio.wait_for(self._finished_event.wait(), timeout=timeout)
            else:
                await self._finished_event.wait()
        except asyncio.TimeoutError:
            return False
        return self.arq_receiver.status == TransferStatus.COMPLETED

    async def linger(self, duration: float) -> None:
        """Keep listening for retransmitted frames or FINs for a linger duration."""
        if duration > 0 and not self._is_closed:
            await asyncio.sleep(duration)

    async def close(self) -> None:
        """Gracefully close the UDP socket."""
        self._is_closed = True
        if self.transport is not None and not self.transport.is_closing():
            self.transport.close()
        self.transport = None
        self.protocol = None
