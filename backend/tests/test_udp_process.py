"""Test UDP communication between two independent operating system processes."""

import asyncio
import hashlib
import multiprocessing as mp
import time
import uuid

import pytest

from app.protocol.config import get_default_config
from app.protocol.constants import ProtocolType, TransferStatus
from app.protocol.selective_repeat import SelectiveRepeatReceiver, SelectiveRepeatSender
from app.network.receiver import UdpReceiver
from app.network.sender import UdpSender


def _run_receiver_process(
    session_id: uuid.UUID,
    transfer_id: uuid.UUID,
    total_frames: int,
    port_queue: mp.Queue,
    result_queue: mp.Queue,
) -> None:
    """Target function for independent receiver process."""
    async def _async_receiver() -> None:
        config = get_default_config(ProtocolType.SELECTIVE_REPEAT)
        config.sender_window_size = 4
        config.receiver_window_size = 4
        config.timeout_ms = 150
        config.frame_delay_ms = 0

        arq_receiver = SelectiveRepeatReceiver(session_id, transfer_id, config, total_frames)
        udp_receiver = UdpReceiver(arq_receiver=arq_receiver, host="127.0.0.1", port=0)
        await udp_receiver.start()

        # Report bound ephemeral port back to parent process
        port_queue.put(udp_receiver.local_port)

        # Wait for transfer completion
        success = await udp_receiver.wait_complete(timeout=5.0)

        data = arq_receiver.get_reconstructed_data()
        sha256 = hashlib.sha256(data).hexdigest()
        result_queue.put({
            "success": success,
            "status": arq_receiver.status.value,
            "sha256": sha256,
            "data_len": len(data),
            "unique_frames": arq_receiver.stats.unique_frames_received,
        })
        await udp_receiver.close()

    asyncio.run(_async_receiver())


@pytest.mark.asyncio
async def test_inter_process_udp_communication() -> None:
    """Verify UDP communication between two independent OS processes."""
    session_id = uuid.uuid4()
    transfer_id = uuid.uuid4()

    chunks = [f"Inter-process UDP chunk {i:03d} content".encode() for i in range(16)]
    expected_data = b"".join(chunks)
    expected_sha256 = hashlib.sha256(expected_data).hexdigest()

    ctx = mp.get_context("spawn")
    port_queue = ctx.Queue()
    result_queue = ctx.Queue()

    proc = ctx.Process(
        target=_run_receiver_process,
        args=(session_id, transfer_id, len(chunks), port_queue, result_queue),
    )
    proc.start()

    try:
        # Wait for receiver process to bind and report its port
        receiver_port = await asyncio.to_thread(port_queue.get, timeout=5.0)
        assert receiver_port > 0

        # Run sender in this process
        config = get_default_config(ProtocolType.SELECTIVE_REPEAT)
        config.sender_window_size = 4
        config.receiver_window_size = 4
        config.timeout_ms = 150
        config.frame_delay_ms = 0

        arq_sender = SelectiveRepeatSender(session_id, transfer_id, config, chunks)
        udp_sender = UdpSender(
            peer_host="127.0.0.1",
            peer_port=receiver_port,
            arq_sender=arq_sender,
        )
        await udp_sender.start()

        send_success = await udp_sender.wait_complete(timeout=5.0)
        assert send_success is True
        assert arq_sender.status == TransferStatus.COMPLETED

        # Collect receiver process results
        res = await asyncio.to_thread(result_queue.get, timeout=5.0)
        assert res["success"] is True
        assert res["status"] == TransferStatus.COMPLETED.value
        assert res["sha256"] == expected_sha256
        assert res["data_len"] == len(expected_data)
        assert res["unique_frames"] == 16

        await udp_sender.close()

    finally:
        proc.join(timeout=2.0)
        if proc.is_alive():
            proc.terminate()
            proc.join()
