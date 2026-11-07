"""Asynchronous UDP Sender handler for PeerShare."""

import asyncio
import logging
import time
from typing import Optional, Set, Tuple

from app.events.models import EventType
from app.protocol.base import BaseSender
from app.protocol.constants import TransferStatus
from app.protocol.exceptions import CorruptedFrameError, FrameDecodeError
from app.protocol.frame import AckFrame, DataFrame, decode_frame
from app.network.loss import PacketLossSimulator
from app.network.protocol import PeerShareDatagramProtocol

logger = logging.getLogger(__name__)


class UdpSender:
    """Asynchronous UDP Sender integrating ARQ protocol logic with UDP transport."""

    def __init__(
        self,
        peer_host: str,
        peer_port: int,
        arq_sender: BaseSender,
        local_host: str = "127.0.0.1",
        local_port: int = 0,
        loss_simulator: Optional[PacketLossSimulator] = None,
        corrupt_indices: Optional[Set[int]] = None,
        event_manager: Optional[object] = None,
    ) -> None:
        self.peer_host = peer_host
        self.peer_port = peer_port
        self.arq_sender = arq_sender
        self._bind_host = local_host
        self._bind_port = local_port
        self.loss_simulator = loss_simulator
        self.corrupt_indices = corrupt_indices or set()
        self.event_manager = event_manager

        self.transport: Optional[asyncio.DatagramTransport] = None
        self.protocol: Optional[PeerShareDatagramProtocol] = None
        self._transmit_task: Optional[asyncio.Task] = None
        self._wake_event = asyncio.Event()
        self._finished_event = asyncio.Event()
        self._is_closed = False

    async def start(self) -> None:
        """Bind the local UDP socket and start the transmission loop."""
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
        logger.debug("UdpSender bound to %s, sending to %s:%d", self.local_addr, self.peer_host, self.peer_port)

        self._transmit_task = asyncio.create_task(self._run_transmit_loop())

    def _on_datagram_received(self, data: bytes, addr: Tuple[str, int]) -> None:
        """Handle incoming ACK datagram from receiver."""
        if self._is_closed:
            return

        try:
            ack = decode_frame(data)
        except CorruptedFrameError:
            self.arq_sender.stats.corrupted_frames += 1
            logger.debug("Received corrupted ACK from %s (CRC failure)", addr)
            return
        except FrameDecodeError as exc:
            logger.debug("Received invalid datagram from %s: %s", addr, exc)
            return

        if not isinstance(ack, AckFrame):
            logger.debug("Expected AckFrame, got %s from %s", type(ack).__name__, addr)
            return

        now = time.monotonic()
        prev_base = self.arq_sender.base_frame_index
        processed = self.arq_sender.handle_ack(ack, now)
        if self.event_manager is not None:
            self.event_manager.emit_event(
                EventType.ACK_RECEIVED,
                session_id=self.arq_sender.session_id,
                transfer_id=self.arq_sender.transfer_id,
                data={
                    "ack_number": ack.ack_number,
                    "frame_index": ack.frame_index,
                    "ack_type": ack.ack_type.name,
                    "window_base": self.arq_sender.base_frame_index,
                },
            )
        if processed:
            if self.event_manager is not None and self.arq_sender.base_frame_index != prev_base:
                self.event_manager.emit_event(
                    EventType.WINDOW_UPDATED,
                    session_id=self.arq_sender.session_id,
                    transfer_id=self.arq_sender.transfer_id,
                    data={
                        "window_base": self.arq_sender.base_frame_index,
                        "window_size": self.arq_sender.config.sender_window_size,
                    },
                )
                self.event_manager.emit_event(
                    EventType.TRANSFER_PROGRESS,
                    session_id=self.arq_sender.session_id,
                    transfer_id=self.arq_sender.transfer_id,
                    data={
                        "acknowledged_frames": self.arq_sender.base_frame_index,
                        "total_frames": self.arq_sender.total_frames,
                        "progress_percentage": round(
                            (self.arq_sender.base_frame_index / max(1, self.arq_sender.total_frames)) * 100,
                            1,
                        ),
                        "bytes_sent": self.arq_sender.stats.total_bytes,
                    },
                )
            # Wake up the transmission loop to advance window
            self._wake_event.set()

        if self.arq_sender.is_finished():
            self._finished_event.set()

    def _on_socket_error(self, exc: Exception) -> None:
        logger.warning("UdpSender socket error: %s", exc)

    async def _send_single_frame(self, frame: DataFrame, is_retransmit: bool = False) -> None:
        """Encode and transmit a single frame, honoring loss and delay."""
        if self.transport is None or self.transport.is_closing():
            return

        peer_target = (self.peer_host, self.peer_port)

        # Check for simulated corruption (transmit with modified payload/header so CRC fails)
        if frame.frame_index in self.corrupt_indices:
            self.corrupt_indices.remove(frame.frame_index)
            encoded = bytearray(frame.encode())
            # Invert bit in sequence number or payload
            encoded[37] ^= 0x01
            self.transport.sendto(bytes(encoded), peer_target)
            logger.debug("Transmitted simulated corrupted frame_index %d", frame.frame_index)
            if self.event_manager is not None:
                self.event_manager.emit_event(
                    EventType.FRAME_CORRUPTED,
                    session_id=self.arq_sender.session_id,
                    transfer_id=self.arq_sender.transfer_id,
                    data={"frame_index": frame.frame_index, "sequence_number": frame.sequence_number},
                )
            if self.arq_sender.config.frame_delay_ms > 0:
                await asyncio.sleep(self.arq_sender.config.frame_delay_ms / 1000.0)
            return

        # Check for simulated loss
        if self.loss_simulator and self.loss_simulator.should_drop(frame.frame_index):
            self.arq_sender.stats.dropped_data_frames += 1
            logger.debug("Simulated drop for data frame_index %d", frame.frame_index)
            if self.event_manager is not None:
                self.event_manager.emit_event(
                    EventType.FRAME_LOST,
                    session_id=self.arq_sender.session_id,
                    transfer_id=self.arq_sender.transfer_id,
                    data={"frame_index": frame.frame_index, "sequence_number": frame.sequence_number},
                )
            return

        encoded = frame.encode()
        self.transport.sendto(encoded, peer_target)

        if self.event_manager is not None:
            ev_type = EventType.FRAME_RETRANSMITTED if is_retransmit else EventType.FRAME_SENT
            self.event_manager.emit_event(
                ev_type,
                session_id=self.arq_sender.session_id,
                transfer_id=self.arq_sender.transfer_id,
                data={
                    "sequence_number": frame.sequence_number,
                    "frame_index": frame.frame_index,
                    "payload_length": len(frame.payload),
                    "frame_type": frame.frame_type.name,
                    "window_base": self.arq_sender.base_frame_index,
                    "window_size": self.arq_sender.config.sender_window_size,
                },
            )

        # Apply configurable per-frame delay pacing
        if self.arq_sender.config.frame_delay_ms > 0:
            await asyncio.sleep(self.arq_sender.config.frame_delay_ms / 1000.0)

    async def _run_transmit_loop(self) -> None:
        """Main asynchronous transmission and retransmission loop."""
        try:
            while not self.arq_sender.is_finished() and not self._is_closed:
                now = time.monotonic()

                # 1. Check for timeouts and retransmit
                retransmissions = self.arq_sender.check_timeouts(now)
                if retransmissions and self.event_manager is not None:
                    self.event_manager.emit_event(
                        EventType.TIMEOUT,
                        session_id=self.arq_sender.session_id,
                        transfer_id=self.arq_sender.transfer_id,
                        data={
                            "timeout_ms": self.arq_sender.config.timeout_ms,
                            "timed_out_frames": [f.frame_index for f in retransmissions],
                        },
                    )
                for frame in retransmissions:
                    await self._send_single_frame(frame, is_retransmit=True)

                if self.arq_sender.status == TransferStatus.FAILED:
                    break

                # 2. Transmit new frames within window
                now = time.monotonic()
                new_frames = self.arq_sender.get_frames_to_send(now)
                for frame in new_frames:
                    await self._send_single_frame(frame, is_retransmit=False)

                if self.arq_sender.is_finished():
                    break

                # 3. Wait for ACK wake-up or timeout check interval
                self._wake_event.clear()
                # Dynamically calculate sleep: at most 20ms or half of timeout
                sleep_interval = min(0.020, max(0.005, (self.arq_sender.config.timeout_ms / 1000.0) / 4.0))
                try:
                    await asyncio.wait_for(self._wake_event.wait(), timeout=sleep_interval)
                except asyncio.TimeoutError:
                    pass

        except asyncio.CancelledError:
            pass
        except Exception as exc:
            logger.error("Error in transmission loop: %s", exc, exc_info=True)
            self.arq_sender.status = TransferStatus.FAILED
        finally:
            self._finished_event.set()

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
        raise RuntimeError("Sender socket is not bound")

    async def wait_complete(self, timeout: Optional[float] = None) -> bool:
        """Wait until file transfer completion or timeout."""
        try:
            if timeout is not None:
                await asyncio.wait_for(self._finished_event.wait(), timeout=timeout)
            else:
                await self._finished_event.wait()
        except asyncio.TimeoutError:
            return False
        return self.arq_sender.status == TransferStatus.COMPLETED

    async def close(self) -> None:
        """Gracefully close the transmission task and UDP socket."""
        self._is_closed = True
        if self._transmit_task is not None and not self._transmit_task.done():
            self._transmit_task.cancel()
            try:
                await self._transmit_task
            except asyncio.CancelledError:
                pass

        if self.transport is not None and not self.transport.is_closing():
            self.transport.close()

        self.transport = None
        self.protocol = None
        self._transmit_task = None
