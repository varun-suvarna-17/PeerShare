"""Basic tests for UDP socket creation, DatagramProtocol, and PacketLossSimulator."""

import asyncio
import pytest

from app.network.loss import PacketLossSimulator
from app.network.protocol import PeerShareDatagramProtocol


@pytest.mark.asyncio
async def test_datagram_protocol_echo() -> None:
    """Test raw datagram send and receive between two bound UDP endpoints."""
    received = asyncio.Event()
    received_data = []
    received_addr = []

    def on_received(data: bytes, addr: tuple[str, int]) -> None:
        received_data.append(data)
        received_addr.append(addr)
        received.set()

    loop = asyncio.get_running_loop()

    # Receiver
    recv_transport, recv_protocol = await loop.create_datagram_endpoint(
        lambda: PeerShareDatagramProtocol(on_datagram_received=on_received),
        local_addr=("127.0.0.1", 0),
    )
    await recv_protocol.wait_connected()
    recv_port = recv_protocol.local_addr[1]

    # Sender
    send_transport, send_protocol = await loop.create_datagram_endpoint(
        lambda: PeerShareDatagramProtocol(on_datagram_received=lambda d, a: None),
        local_addr=("127.0.0.1", 0),
    )
    await send_protocol.wait_connected()

    # Transmit test payload
    message = b"PeerShare UDP Ping"
    send_transport.sendto(message, ("127.0.0.1", recv_port))

    await asyncio.wait_for(received.wait(), timeout=1.0)
    assert len(received_data) == 1
    assert received_data[0] == message

    # Cleanup
    send_transport.close()
    recv_transport.close()


def test_packet_loss_simulator() -> None:
    """Verify deterministic and probabilistic loss simulator."""
    # 0% loss
    sim_zero = PacketLossSimulator(loss_percentage=0.0)
    assert not sim_zero.should_drop(1)

    # 100% loss
    sim_full = PacketLossSimulator(loss_percentage=100.0)
    assert sim_full.should_drop(1)

    # Deterministic drop indices
    sim_det = PacketLossSimulator(loss_percentage=0.0, drop_indices={3, 7})
    assert not sim_det.should_drop(1)
    assert sim_det.should_drop(3)
    assert not sim_det.should_drop(3)  # Consumed
    assert sim_det.should_drop(7)

    # Seeded reproducibility
    sim_seed1 = PacketLossSimulator(loss_percentage=30.0, seed=12345)
    sim_seed2 = PacketLossSimulator(loss_percentage=30.0, seed=12345)

    results1 = [sim_seed1.should_drop() for _ in range(50)]
    results2 = [sim_seed2.should_drop() for _ in range(50)]
    assert results1 == results2
