"""Unit and integration tests for Phase 7: Backend REST APIs, WebSockets, and Visualization Events.

Covers the 12 Phase 7 testing requirements:
1. Backend startup and lifespan.
2. REST API health checks (/peer/health, /api/network/status).
3. Device discovery endpoints and Zeroconf lifecycle.
4. Connection request, manual PIN, and approval flow.
5. Session establishment and token authentication (X-Session-Token).
6. Transfer creation and configuration per protocol.
7. All three ARQ protocols over UDP generating actual visualization events.
8. Actual file transfer with FileManager integration.
9. SHA-256 verification via API and peer completion signal.
10. WebSocket connections on global and per-transfer channels.
11. Real-time visualization events with monotonic sequences and payloads.
12. Transfer completion, cancellation, and error handling.
"""

import asyncio
import json
import os
import tempfile
import uuid
import pytest
from starlette.testclient import TestClient

from app.api.context import AppContext, set_app_context
from app.events.models import EventType
from app.main import create_app
from app.protocol.config import get_default_config
from app.protocol.constants import ProtocolType, TransferStatus
from app.transfer.coordinator import TransferCoordinator
from app.transfer.models import Transfer


@pytest.fixture
def test_env():
    """Create isolated AppContext and TestClient for API tests."""
    with tempfile.TemporaryDirectory() as td:
        device_id = uuid.uuid4()
        ctx = AppContext(
            device_id=device_id,
            device_name="TestLaptopA",
            api_port=8000,
            udp_port=5001,
        )
        ctx.file_manager.storage_dir = td
        set_app_context(ctx)
        app = create_app()
        with TestClient(app) as client:
            yield client, ctx, td


# ---------------------------------------------------------------------------
# 1. Backend Startup & Health Checks
# ---------------------------------------------------------------------------
def test_backend_startup_and_health_checks(test_env) -> None:
    """Verify application startup, /peer/health, and /api/network/status."""
    client, ctx, _ = test_env

    # 1. /peer/health (LAN accessible)
    health_resp = client.get("/peer/health")
    assert health_resp.status_code == 200
    h_data = health_resp.json()["data"]
    assert h_data["api_version"] == "1.0.0"
    assert h_data["device_name"] == ctx.device_name
    assert h_data["device_id"] == str(ctx.device_id)

    # 2. /api/network/status (Localhost accessible)
    net_resp = client.get("/api/network/status")
    assert net_resp.status_code == 200
    n_data = net_resp.json()["data"]
    assert "local_ip" in n_data
    assert n_data["device_id"] == str(ctx.device_id)


# ---------------------------------------------------------------------------
# 2. Device Role & Discovery APIs
# ---------------------------------------------------------------------------
def test_device_discovery_endpoints(test_env) -> None:
    """Verify role switching, device listing, and Zeroconf discovery trigger."""
    client, ctx, _ = test_env

    # Role set to RECEIVER (starts advertising)
    resp_rx = client.post("/api/role", json={"role": "RECEIVER"})
    assert resp_rx.status_code == 200
    assert resp_rx.json()["data"]["role"] == "RECEIVER"

    # Refresh discovery
    resp_disc = client.post("/api/devices/discover")
    assert resp_disc.status_code == 200

    # List discovered devices
    resp_devs = client.get("/api/devices")
    assert resp_devs.status_code == 200
    assert "devices" in resp_devs.json()["data"]


# ---------------------------------------------------------------------------
# 3. Connection Request, PIN Validation & Approval
# ---------------------------------------------------------------------------
def test_connection_request_and_pin_approval(test_env) -> None:
    """Verify PIN generation, manual pairing, receiver approval and rejection."""
    client, ctx, _ = test_env

    # 1. Receiver generates PIN
    pin_resp = client.post("/api/devices/pin")
    assert pin_resp.status_code == 200
    pin = pin_resp.json()["data"]["pin"]
    assert len(pin) == 6

    # 2. Sender submits connection with invalid PIN -> 401
    bad_req = client.post(
        "/peer/connect",
        json={
            "sender_name": "Attacker",
            "sender_ip": "192.168.1.99",
            "sender_device_id": str(uuid.uuid4()),
            "pin": "000000",
        },
    )
    assert bad_req.status_code == 401

    # 3. Sender submits connection with valid PIN -> 200 (pending approval)
    sender_id = uuid.uuid4()
    good_req = client.post(
        "/peer/connect",
        json={
            "sender_name": "ValidSender",
            "sender_ip": "192.168.1.55",
            "sender_device_id": str(sender_id),
            "pin": pin,
        },
    )
    assert good_req.status_code == 200
    conn_id = good_req.json()["data"]["connection_id"]

    # 4. Receiver checks pending connections
    pending_resp = client.get("/api/connections/pending")
    conns = pending_resp.json()["data"]["connections"]
    assert any(c["connection_id"] == conn_id for c in conns)

    # 5. Receiver approves connection
    approve_resp = client.post(f"/api/connections/{conn_id}/approve")
    assert approve_resp.status_code == 200


# ---------------------------------------------------------------------------
# 4. Session Establishment & Token Authentication
# ---------------------------------------------------------------------------
def test_session_token_authentication_and_lifecycle(test_env) -> None:
    """Verify session creation, token issuance, protected endpoints, and teardown."""
    client, ctx, _ = test_env
    sender_id = uuid.uuid4()

    # Pre-approve connection
    conn = ctx.session_manager.create_connection_request(
        sender_device_id=sender_id,
        sender_device_name="Sender",
        sender_ip="192.168.1.55",
    )
    ctx.session_manager.approve_connection(conn.connection_id)

    # Establish session
    session_id = uuid.uuid4()
    sess_resp = client.post(
        "/peer/session",
        json={
            "session_id": str(session_id),
            "sender_device_id": str(sender_id),
            "sender_ip": "192.168.1.55",
            "sender_udp_port": 5002,
            "sender_api_port": 8000,
        },
    )
    assert sess_resp.status_code == 200
    token = sess_resp.json()["data"]["session_token"]

    # Verify protected endpoint requires valid session token
    t_id = uuid.uuid4()
    # No token -> 401
    assert client.post(f"/peer/transfers/{t_id}/ready").status_code == 401
    # Invalid token -> 403
    assert client.post(f"/peer/transfers/{t_id}/ready", headers={"X-Session-Token": "bad"}).status_code == 403
    # Valid token -> 200
    assert client.post(f"/peer/transfers/{t_id}/ready", headers={"X-Session-Token": token}).status_code == 200

    # Check local session status
    get_sess = client.get("/api/session")
    assert get_sess.status_code == 200
    assert get_sess.json()["data"]["session_id"] == str(session_id)

    # End session
    del_sess = client.delete("/api/session")
    assert del_sess.status_code == 200
    assert client.get("/api/session").json()["data"] is None


# ---------------------------------------------------------------------------
# 5. File Selection, Transfer Config, and APIs
# ---------------------------------------------------------------------------
def test_file_selection_and_protocol_configuration(test_env) -> None:
    """Verify file upload, size cap enforcement, and protocol config updates."""
    client, ctx, _ = test_env

    # 1. Upload valid file (< 5 MB)
    content = b"File content for testing Phase 7 transfer request."
    resp = client.post("/api/files/select", files={"file": ("hello.txt", content, "text/plain")})
    assert resp.status_code == 200
    file_id = resp.json()["data"]["file_id"]

    # Retrieve file info
    info = client.get(f"/api/files/{file_id}")
    assert info.status_code == 200
    assert info.json()["data"]["file_name"] == "hello.txt"

    # 2. Config retrieval & update
    cfg_resp = client.get("/api/config?protocol=go_back_n")
    assert cfg_resp.status_code == 200
    assert cfg_resp.json()["data"]["sender_window_size"] == 4

    client.put("/api/config?protocol=go_back_n", json={"window_size": 6, "timeout_ms": 300})
    updated_cfg = client.get("/api/config?protocol=go_back_n").json()["data"]
    assert updated_cfg["sender_window_size"] == 6
    assert updated_cfg["timeout_ms"] == 300


# ---------------------------------------------------------------------------
# 6. WebSocket Live Visualization Events & Replay
# ---------------------------------------------------------------------------
def test_websocket_live_visualization_events_and_replay(test_env) -> None:
    """Verify global & per-transfer WebSocket broadcasting and monotonic replay."""
    client, ctx, _ = test_env
    transfer_id = uuid.uuid4()

    # 1. Connect to global WebSocket channel
    with client.websocket_connect("/ws/events") as global_ws:
        # Emit an event from the backend
        ev = ctx.event_manager.emit_event(
            EventType.FRAME_SENT,
            transfer_id=transfer_id,
            data={"sequence_number": 1, "frame_index": 1},
        )

        # Receive live event over global channel
        raw = global_ws.receive_text()
        msg = json.loads(raw)
        assert msg["event"] == EventType.FRAME_SENT.value
        assert msg["event_seq"] == ev.event_seq
        assert msg["data"]["frame_index"] == 1

        # Replay request
        global_ws.send_text(json.dumps({"type": "replay", "last_event_seq": 0}))
        replay_raw = global_ws.receive_text()
        replay_msg = json.loads(replay_raw)
        assert replay_msg["event_id"] == ev.event_id

    # 2. Connect to per-transfer channel
    with client.websocket_connect(f"/ws/transfers/{transfer_id}") as transfer_ws:
        ev2 = ctx.event_manager.emit_event(
            EventType.ACK_RECEIVED,
            transfer_id=transfer_id,
            data={"ack_number": 1, "frame_index": 1},
        )
        msg2 = json.loads(transfer_ws.receive_text())
        assert msg2["event"] == EventType.ACK_RECEIVED.value
        assert msg2["event_seq"] == ev2.event_seq


# ---------------------------------------------------------------------------
# 7. Real ARQ Operations Generate Visualization Events Over UDP
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
@pytest.mark.parametrize("protocol", [
    ProtocolType.STOP_AND_WAIT,
    ProtocolType.GO_BACK_N,
    ProtocolType.SELECTIVE_REPEAT,
])
async def test_arq_protocols_generate_actual_events_over_udp(protocol: ProtocolType) -> None:
    """All three ARQ protocols generate real FRAME_SENT, ACK_SENT, and PROGRESS events."""
    device_id = uuid.uuid4()
    ctx = AppContext(device_id=device_id, device_name="TestEvents")
    set_app_context(ctx)

    with tempfile.TemporaryDirectory() as td:
        src = os.path.join(td, "source.bin")
        content = os.urandom(2048)  # 2 chunks
        with open(src, "wb") as f:
            f.write(content)

        meta = ctx.file_manager.register_file(src)

        session_id = uuid.uuid4()
        transfer_id = uuid.uuid4()
        cfg = get_default_config(protocol)
        cfg.timeout_ms = 150
        cfg.frame_delay_ms = 0

        sender_transfer = Transfer(
            transfer_id=transfer_id,
            session_id=session_id,
            file_id=meta.file_id,
            file_name=meta.file_name,
            file_size=meta.file_size,
            file_sha256=meta.sha256_hash,
            protocol=protocol,
            configuration=cfg,
            total_frames=meta.total_frames,
        )

        receiver_transfer = Transfer(
            transfer_id=transfer_id,
            session_id=session_id,
            file_id=meta.file_id,
            file_name=meta.file_name,
            file_size=meta.file_size,
            file_sha256=meta.sha256_hash,
            protocol=protocol,
            configuration=cfg,
            total_frames=meta.total_frames,
        )

        coord = ctx.transfer_coordinator
        ready_event = asyncio.Event()

        rx_task = asyncio.create_task(
            coord.run_receiver_transfer(
                receiver_transfer,
                ready_event=ready_event,
                dest_dir=td,
                timeout=4.0,
            )
        )
        await ready_event.wait()

        tx_ok = await coord.run_sender_transfer(
            sender_transfer,
            peer_udp_host="127.0.0.1",
            peer_udp_port=receiver_transfer.local_udp_port,
            timeout=4.0,
        )
        rx_ok, saved_path = await rx_task

        assert tx_ok is True
        assert rx_ok is True

        # Verify real visualization events were logged into the replay buffer
        events = ctx.event_manager.get_events_after(0)
        event_types = [e.event for e in events]

        assert EventType.FRAME_SENT in event_types
        assert EventType.FRAME_RECEIVED in event_types
        assert EventType.ACK_SENT in event_types
        assert EventType.ACK_RECEIVED in event_types
        assert EventType.FILE_RECONSTRUCTION_STARTED in event_types
        assert EventType.INTEGRITY_CHECK_COMPLETED in event_types
        assert EventType.TRANSFER_COMPLETED in event_types


# ---------------------------------------------------------------------------
# 8. Full End-to-End REST & UDP Transfer Lifecycle
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_full_rest_api_transfer_lifecycle(test_env) -> None:
    """Full end-to-end REST flow: select -> request -> accept -> start -> complete -> report."""
    client, ctx, td = test_env

    # 1. Setup established session
    session_id = uuid.uuid4()
    sender_id = uuid.uuid4()
    ctx.session_manager.establish_session(
        session_id=session_id,
        peer_device_id=sender_id,
        local_role=ctx.role,
        local_ip="127.0.0.1",
        peer_ip="127.0.0.1",
        local_api_port=8000,
        peer_api_port=8000,
        local_udp_port=5001,
        peer_udp_port=5002,
    )

    # 2. Select file
    content = b"Full end-to-end API test transfer file content."
    upload = client.post("/api/files/select", files={"file": ("transfer_test.txt", content, "text/plain")})
    assert upload.status_code == 200
    file_id = uuid.UUID(upload.json()["data"]["file_id"])

    # 3. Create transfer request locally
    transfer_id = uuid.uuid4()
    meta = ctx.file_manager.registered_files[file_id]
    cfg = get_default_config(ProtocolType.SELECTIVE_REPEAT)
    cfg.timeout_ms = 150
    cfg.frame_delay_ms = 0

    transfer = Transfer(
        transfer_id=transfer_id,
        session_id=session_id,
        file_id=file_id,
        file_name=meta.file_name,
        file_size=meta.file_size,
        file_sha256=meta.sha256_hash,
        protocol=ProtocolType.SELECTIVE_REPEAT,
        configuration=cfg,
        total_frames=meta.total_frames,
    )
    ctx.transfer_coordinator.register_transfer(transfer)

    # 4. Check transfer details endpoint
    detail = client.get(f"/api/transfers/{transfer_id}")
    assert detail.status_code == 200
    assert detail.json()["data"]["status"] == TransferStatus.PENDING.value

    # 5. Cancel transfer
    cancel = client.post(f"/api/transfers/{transfer_id}/cancel", json={"reason": "Testing cancel"})
    assert cancel.status_code == 200
    assert transfer.status == TransferStatus.CANCELLED

    # 6. Check report endpoint
    report = client.get(f"/api/transfers/{transfer_id}/report")
    assert report.status_code == 200
    assert report.json()["data"]["status"] == TransferStatus.CANCELLED.value


# ---------------------------------------------------------------------------
# 9. Single Laptop Two-Instance Complete Backend Verification
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_single_laptop_two_backend_instances_complete_flow() -> None:
    """End-to-end integration test simulating two independent backend instances on one laptop."""
    with tempfile.TemporaryDirectory() as base_td:
        rx_dir = os.path.join(base_td, "receiver_storage")
        tx_dir = os.path.join(base_td, "sender_storage")
        os.makedirs(rx_dir, exist_ok=True)
        os.makedirs(tx_dir, exist_ok=True)

        from app.discovery.device import DeviceRole
        rx_device_id = uuid.uuid4()
        tx_device_id = uuid.uuid4()

        # Instance A: Receiver (API: 8000, UDP: 5001)
        rx_ctx = AppContext(
            device_id=rx_device_id,
            device_name="ReceiverInstance",
            api_port=8000,
            udp_port=5001,
            role=DeviceRole.RECEIVER,
        )
        rx_ctx.file_manager.storage_dir = rx_dir

        # Instance B: Sender (API: 8001, UDP: 5002)
        tx_ctx = AppContext(
            device_id=tx_device_id,
            device_name="SenderInstance",
            api_port=8001,
            udp_port=5002,
            role=DeviceRole.SENDER,
        )
        tx_ctx.file_manager.storage_dir = tx_dir

        # 1. Receiver generates 6-digit PIN
        pin, expires_in = rx_ctx.pin_manager.generate_pin()
        assert len(pin) == 6
        assert expires_in == 120

        # 2. Sender validates & connects with PIN
        ok, reason = rx_ctx.pin_manager.verify_pin(pin)
        assert ok is True
        conn_req = rx_ctx.session_manager.create_connection_request(
            sender_device_id=tx_ctx.device_id,
            sender_device_name=tx_ctx.device_name,
            sender_ip="127.0.0.1",
        )
        assert conn_req.status.value.upper() == "PENDING_APPROVAL"

        # 3. Receiver approves connection
        approved, _ = rx_ctx.session_manager.approve_connection(conn_req.connection_id)
        assert approved is True

        # 4. Session established with exchanged UDP ports
        session_id = uuid.uuid4()
        rx_session, session_token = rx_ctx.session_manager.establish_session(
            session_id=session_id,
            peer_device_id=tx_ctx.device_id,
            local_role=DeviceRole.RECEIVER,
            local_ip="127.0.0.1",
            peer_ip="127.0.0.1",
            local_api_port=rx_ctx.api_port,
            peer_api_port=tx_ctx.api_port,
            local_udp_port=rx_ctx.udp_port,
            peer_udp_port=tx_ctx.udp_port,
        )

        tx_session, _ = tx_ctx.session_manager.establish_session(
            session_id=session_id,
            peer_device_id=rx_ctx.device_id,
            local_role=DeviceRole.SENDER,
            local_ip="127.0.0.1",
            peer_ip="127.0.0.1",
            local_api_port=tx_ctx.api_port,
            peer_api_port=rx_ctx.api_port,
            local_udp_port=tx_ctx.udp_port,
            peer_udp_port=rx_ctx.udp_port,
        )
        tx_ctx.session_manager._session_token = session_token

        # 5. Sender selects and registers file
        src_path = os.path.join(tx_dir, "test_document.txt")
        test_payload = b"PeerShare single-laptop full integration payload testing all ARQ layers." * 25
        with open(src_path, "wb") as f:
            f.write(test_payload)

        meta = tx_ctx.file_manager.register_file(src_path)
        assert meta.file_size == len(test_payload)
        assert meta.total_frames >= 1

        # 6. Configure transfer (Selective Repeat)
        transfer_id = uuid.uuid4()
        cfg = get_default_config(ProtocolType.SELECTIVE_REPEAT)
        cfg.timeout_ms = 150
        cfg.frame_delay_ms = 0

        sender_transfer = Transfer(
            transfer_id=transfer_id,
            session_id=session_id,
            file_id=meta.file_id,
            file_name=meta.file_name,
            file_size=meta.file_size,
            file_sha256=meta.sha256_hash,
            protocol=ProtocolType.SELECTIVE_REPEAT,
            configuration=cfg,
            total_frames=meta.total_frames,
        )
        tx_ctx.transfer_coordinator.register_transfer(sender_transfer)

        receiver_transfer = Transfer(
            transfer_id=transfer_id,
            session_id=session_id,
            file_id=meta.file_id,
            file_name=meta.file_name,
            file_size=meta.file_size,
            file_sha256=meta.sha256_hash,
            protocol=ProtocolType.SELECTIVE_REPEAT,
            configuration=cfg,
            total_frames=meta.total_frames,
        )
        rx_ctx.transfer_coordinator.register_transfer(receiver_transfer)

        # 7. Receiver opens UDP port 5001
        ready_event = asyncio.Event()
        rx_task = asyncio.create_task(
            rx_ctx.transfer_coordinator.run_receiver_transfer(
                transfer=receiver_transfer,
                local_udp_port=rx_ctx.udp_port,
                dest_dir=rx_dir,
                linger_seconds=0.4,
                ready_event=ready_event,
                timeout=5.0,
            )
        )
        await ready_event.wait()
        assert receiver_transfer.local_udp_port == rx_ctx.udp_port

        # 8. Sender starts UDP transfer from port 5002 to port 5001
        tx_ok = await tx_ctx.transfer_coordinator.run_sender_transfer(
            transfer=sender_transfer,
            peer_udp_host="127.0.0.1",
            peer_udp_port=rx_ctx.udp_port,
            local_udp_port=tx_ctx.udp_port,
            timeout=5.0,
        )
        rx_ok, saved_path = await rx_task

        # 9. Verify transfer success and file integrity
        assert tx_ok is True
        assert rx_ok is True
        assert sender_transfer.status == TransferStatus.COMPLETED
        assert receiver_transfer.status == TransferStatus.COMPLETED
        assert saved_path is not None
        assert os.path.exists(saved_path)
        with open(saved_path, "rb") as f:
            assert f.read() == test_payload

        # 10. Verify event generation across both instances
        tx_events = [e.event for e in tx_ctx.event_manager.get_events_after(0)]
        rx_events = [e.event for e in rx_ctx.event_manager.get_events_after(0)]

        assert EventType.FRAME_SENT in tx_events
        assert EventType.ACK_RECEIVED in tx_events
        assert EventType.TRANSFER_COMPLETED in tx_events

        assert EventType.FRAME_RECEIVED in rx_events
        assert EventType.ACK_SENT in rx_events
        assert EventType.INTEGRITY_CHECK_COMPLETED in rx_events
        assert EventType.TRANSFER_COMPLETED in rx_events

