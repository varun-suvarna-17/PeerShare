"""Transfer Coordinator bridging FileManager, ARQ Protocol, and UDP transport."""

import asyncio
import logging
from typing import Optional, Tuple
import uuid

from app.events.models import EventType
from app.file.manager import FileManager
from app.network.loss import PacketLossSimulator
from app.network.receiver import UdpReceiver
from app.network.sender import UdpSender
from app.protocol.base import BaseReceiver, BaseSender
from app.protocol.config import ProtocolConfig
from app.protocol.constants import ProtocolType, TransferStatus
from app.protocol.go_back_n import GoBackNReceiver, GoBackNSender
from app.protocol.selective_repeat import SelectiveRepeatReceiver, SelectiveRepeatSender
from app.protocol.stop_and_wait import StopAndWaitReceiver, StopAndWaitSender
from app.transfer.models import Transfer

logger = logging.getLogger(__name__)


def create_arq_sender(
    protocol: ProtocolType,
    session_id: uuid.UUID,
    transfer_id: uuid.UUID,
    config: ProtocolConfig,
    chunks: list[bytes],
) -> BaseSender:
    """Factory creating appropriate ARQ sender instance."""
    if protocol == ProtocolType.STOP_AND_WAIT:
        return StopAndWaitSender(session_id, transfer_id, config, chunks)
    elif protocol == ProtocolType.GO_BACK_N:
        return GoBackNSender(session_id, transfer_id, config, chunks)
    elif protocol == ProtocolType.SELECTIVE_REPEAT:
        return SelectiveRepeatSender(session_id, transfer_id, config, chunks)
    raise ValueError(f"Unsupported ARQ protocol: {protocol}")


def create_arq_receiver(
    protocol: ProtocolType,
    session_id: uuid.UUID,
    transfer_id: uuid.UUID,
    config: ProtocolConfig,
    total_frames: int,
) -> BaseReceiver:
    """Factory creating appropriate ARQ receiver instance."""
    if protocol == ProtocolType.STOP_AND_WAIT:
        return StopAndWaitReceiver(session_id, transfer_id, config, total_frames)
    elif protocol == ProtocolType.GO_BACK_N:
        return GoBackNReceiver(session_id, transfer_id, config, total_frames)
    elif protocol == ProtocolType.SELECTIVE_REPEAT:
        return SelectiveRepeatReceiver(session_id, transfer_id, config, total_frames)
    raise ValueError(f"Unsupported ARQ protocol: {protocol}")


class TransferCoordinator:
    """Coordinates high-level file transfer, combining ARQ, UDP sockets, and file integrity."""

    def __init__(self, file_manager: FileManager, event_manager: Optional[object] = None) -> None:
        self.file_manager = file_manager
        self.event_manager = event_manager
        self.active_transfers: dict[uuid.UUID, Transfer] = {}

    def register_transfer(self, transfer: Transfer) -> None:
        """Register a new transfer record."""
        self.active_transfers[transfer.transfer_id] = transfer

    def get_transfer(self, transfer_id: uuid.UUID) -> Optional[Transfer]:
        """Retrieve transfer record by ID."""
        return self.active_transfers.get(transfer_id)

    async def run_sender_transfer(
        self,
        transfer: Transfer,
        peer_udp_host: str,
        peer_udp_port: int,
        local_udp_port: int = 0,
        loss_simulator: Optional[PacketLossSimulator] = None,
        timeout: Optional[float] = None,
    ) -> bool:
        """Execute sender-side UDP file transfer."""
        import time
        start_mono = time.monotonic()
        chunks = self.file_manager.get_chunks(transfer.file_id)
        arq_sender = create_arq_sender(
            protocol=transfer.protocol,
            session_id=transfer.session_id,
            transfer_id=transfer.transfer_id,
            config=transfer.configuration,
            chunks=chunks,
        )

        udp_sender = UdpSender(
            peer_host=peer_udp_host,
            peer_port=peer_udp_port,
            arq_sender=arq_sender,
            local_port=local_udp_port,
            loss_simulator=loss_simulator,
            event_manager=self.event_manager,
        )

        transfer.mark_started()
        try:
            await udp_sender.start()
            transfer.local_udp_port = udp_sender.local_port
            completed = await udp_sender.wait_complete(timeout=timeout)
            duration = max(0.001, time.monotonic() - start_mono)
            arq_sender.stats.finalize(duration)
            transfer.total_transmissions = arq_sender.stats.total_transmissions

            if completed:
                transfer.mark_completed(stats=arq_sender.stats)
                if self.event_manager is not None:
                    self.event_manager.emit_event(
                        EventType.TRANSFER_COMPLETED,
                        session_id=transfer.session_id,
                        transfer_id=transfer.transfer_id,
                        data={"total_frames": transfer.total_frames, "duration_seconds": duration},
                    )
                return True
            else:
                transfer.mark_failed("Sender timeout or retry limit exceeded", stats=arq_sender.stats)
                if self.event_manager is not None:
                    self.event_manager.emit_event(
                        EventType.TRANSFER_FAILED,
                        session_id=transfer.session_id,
                        transfer_id=transfer.transfer_id,
                        data={"reason": "Sender timeout or retry limit exceeded"},
                    )
                return False
        except Exception as exc:
            duration = max(0.001, time.monotonic() - start_mono)
            arq_sender.stats.finalize(duration)
            transfer.mark_failed(str(exc), stats=arq_sender.stats)
            if self.event_manager is not None:
                self.event_manager.emit_event(
                    EventType.TRANSFER_FAILED,
                    session_id=transfer.session_id,
                    transfer_id=transfer.transfer_id,
                    data={"reason": str(exc)},
                )
            return False
        finally:
            await udp_sender.close()

    async def run_receiver_transfer(
        self,
        transfer: Transfer,
        local_udp_port: int = 0,
        loss_simulator: Optional[PacketLossSimulator] = None,
        timeout: Optional[float] = None,
        dest_dir: Optional[str] = None,
        linger_seconds: float = 0.0,
        ready_event: Optional[asyncio.Event] = None,
    ) -> Tuple[bool, Optional[str]]:
        """Execute receiver-side UDP file transfer and reconstruct file with SHA-256 verification."""
        import time
        start_mono = time.monotonic()
        arq_receiver = create_arq_receiver(
            protocol=transfer.protocol,
            session_id=transfer.session_id,
            transfer_id=transfer.transfer_id,
            config=transfer.configuration,
            total_frames=transfer.total_frames,
        )

        udp_receiver = UdpReceiver(
            arq_receiver=arq_receiver,
            port=local_udp_port,
            loss_simulator=loss_simulator,
            event_manager=self.event_manager,
        )

        transfer.mark_started()
        try:
            await udp_receiver.start()
            transfer.local_udp_port = udp_receiver.local_port
            if ready_event is not None:
                ready_event.set()

            completed = await udp_receiver.wait_complete(timeout=timeout)
            duration = max(0.001, time.monotonic() - start_mono)
            arq_receiver.stats.finalize(duration)

            if not completed:
                transfer.mark_failed("Receiver timed out waiting for file frames", stats=arq_receiver.stats)
                if self.event_manager is not None:
                    self.event_manager.emit_event(
                        EventType.TRANSFER_FAILED,
                        session_id=transfer.session_id,
                        transfer_id=transfer.transfer_id,
                        data={"reason": "Receiver timed out waiting for file frames"},
                    )
                return False, None

            # Reconstruct file
            if self.event_manager is not None:
                self.event_manager.emit_event(
                    EventType.FILE_RECONSTRUCTION_STARTED,
                    session_id=transfer.session_id,
                    transfer_id=transfer.transfer_id,
                )

            reconstructed_bytes = arq_receiver.get_reconstructed_data()

            if self.event_manager is not None:
                self.event_manager.emit_event(
                    EventType.FILE_RECONSTRUCTION_COMPLETED,
                    session_id=transfer.session_id,
                    transfer_id=transfer.transfer_id,
                )
                self.event_manager.emit_event(
                    EventType.INTEGRITY_CHECK_STARTED,
                    session_id=transfer.session_id,
                    transfer_id=transfer.transfer_id,
                )

            saved_path, verified = self.file_manager.save_reconstructed_file(
                file_name=transfer.file_name,
                data=reconstructed_bytes,
                expected_sha256=transfer.file_sha256,
                dest_dir=dest_dir,
            )

            if verified:
                arq_receiver.stats.integrity_verified = True
                transfer.mark_completed(reconstructed_path=saved_path, stats=arq_receiver.stats)
                if self.event_manager is not None:
                    self.event_manager.emit_event(
                        EventType.INTEGRITY_CHECK_COMPLETED,
                        session_id=transfer.session_id,
                        transfer_id=transfer.transfer_id,
                        data={"sha256_hash": transfer.file_sha256},
                    )
                    self.event_manager.emit_event(
                        EventType.TRANSFER_COMPLETED,
                        session_id=transfer.session_id,
                        transfer_id=transfer.transfer_id,
                        data={"saved_path": saved_path, "duration_seconds": duration},
                    )
                if linger_seconds > 0:
                    await asyncio.sleep(linger_seconds)
                return True, saved_path
            else:
                transfer.mark_failed("SHA-256 integrity verification failed", stats=arq_receiver.stats)
                if self.event_manager is not None:
                    self.event_manager.emit_event(
                        EventType.INTEGRITY_CHECK_FAILED,
                        session_id=transfer.session_id,
                        transfer_id=transfer.transfer_id,
                    )
                    self.event_manager.emit_event(
                        EventType.TRANSFER_FAILED,
                        session_id=transfer.session_id,
                        transfer_id=transfer.transfer_id,
                        data={"reason": "SHA-256 integrity verification failed"},
                    )
                return False, None

        except Exception as exc:
            duration = max(0.001, time.monotonic() - start_mono)
            arq_receiver.stats.finalize(duration)
            transfer.mark_failed(str(exc), stats=arq_receiver.stats)
            if self.event_manager is not None:
                self.event_manager.emit_event(
                    EventType.TRANSFER_FAILED,
                    session_id=transfer.session_id,
                    transfer_id=transfer.transfer_id,
                    data={"reason": str(exc)},
                )
            return False, None
        finally:
            await udp_receiver.close()


