"""Unit and integration tests for Phase 5: Device Discovery and Session Management."""

import asyncio
from datetime import datetime, timezone
import time
import uuid

import pytest
from zeroconf import IPVersion
from zeroconf.asyncio import AsyncZeroconf

from app.discovery.device import DeviceRole, DiscoveryMethod
from app.discovery.pin import PinManager
from app.discovery.zeroconf_service import DeviceDiscoveryManager
from app.session.manager import SessionManager, hash_token
from app.session.models import ConnectionStatus, SessionStatus


# ---------------------------------------------------------------------------
# PIN Manager Tests
# ---------------------------------------------------------------------------

def test_pin_generation_and_valid_verification() -> None:
    """Generate 6-digit PIN and verify single-use valid verification."""
    pm = PinManager()
    pin, expires_in = pm.generate_pin()

    assert len(pin) == 6
    assert pin.isdigit()
    assert expires_in == 120
    assert not pm.is_expired()
    assert not pm.is_locked()

    # First attempt: success
    success, msg = pm.verify_pin(pin)
    assert success is True
    assert msg == "SUCCESS"

    # Second attempt: rejected because PIN is single-use
    success2, msg2 = pm.verify_pin(pin)
    assert success2 is False
    assert msg2 == "PIN_ALREADY_USED"


def test_pin_invalid_attempts_and_lockout() -> None:
    """Five failed attempts must trigger lockout."""
    pm = PinManager()
    pin, _ = pm.generate_pin()

    # 4 invalid attempts
    for _ in range(4):
        success, msg = pm.verify_pin("000000" if pin != "000000" else "111111")
        assert success is False
        assert msg == "INVALID_PIN"
        assert not pm.is_locked()

    # 5th invalid attempt triggers lockout
    success5, msg5 = pm.verify_pin("000000" if pin != "000000" else "111111")
    assert success5 is False
    assert msg5 == "PIN_LOCKED"
    assert pm.is_locked() is True

    # Even the correct PIN is now rejected due to lockout
    success_locked, msg_locked = pm.verify_pin(pin)
    assert success_locked is False
    assert msg_locked == "PIN_LOCKED"


def test_pin_expiry() -> None:
    """Expired PINs are rejected."""
    pm = PinManager()
    pin, _ = pm.generate_pin()

    # Artificially expire the PIN
    assert pm._current_pin_state is not None
    pm._current_pin_state.expires_at = datetime.fromtimestamp(100.0, tz=timezone.utc)
    assert pm.is_expired() is True

    success, msg = pm.verify_pin(pin)
    assert success is False
    assert msg == "PIN_EXPIRED"


# ---------------------------------------------------------------------------
# Session Manager Tests
# ---------------------------------------------------------------------------

def test_connection_request_and_approval() -> None:
    """Receiver receives connection request, user approves, session established."""
    receiver_id = uuid.uuid4()
    sm = SessionManager(local_device_id=receiver_id)

    sender_id = uuid.uuid4()
    req = sm.create_connection_request(
        sender_device_id=sender_id,
        sender_device_name="Laptop A",
        sender_ip="192.168.1.50",
        discovery_method=DiscoveryMethod.ZEROCONF,
    )

    assert req.status == ConnectionStatus.PENDING_APPROVAL
    pending = sm.get_pending_requests()
    assert len(pending) == 1
    assert pending[0].connection_id == req.connection_id

    # Approve request
    approved, msg = sm.approve_connection(req.connection_id)
    assert approved is True
    assert msg == "APPROVED"
    assert req.status == ConnectionStatus.APPROVED

    # Now no more pending requests
    assert len(sm.get_pending_requests()) == 0


def test_connection_request_rejection() -> None:
    """Receiver rejects incoming connection request."""
    receiver_id = uuid.uuid4()
    sm = SessionManager(local_device_id=receiver_id)

    sender_id = uuid.uuid4()
    req = sm.create_connection_request(
        sender_device_id=sender_id,
        sender_device_name="Laptop A",
        sender_ip="192.168.1.50",
    )

    rejected, msg = sm.reject_connection(req.connection_id)
    assert rejected is True
    assert msg == "REJECTED"
    assert req.status == ConnectionStatus.REJECTED


def test_session_lifecycle_and_token_validation() -> None:
    """Establish session, validate secure tokens, update UDP ports, handle expiry."""
    receiver_id = uuid.uuid4()
    sender_id = uuid.uuid4()
    session_id = uuid.uuid4()

    sm = SessionManager(local_device_id=receiver_id)
    session, raw_token = sm.establish_session(
        session_id=session_id,
        peer_device_id=sender_id,
        local_role=DeviceRole.RECEIVER,
        local_ip="192.168.1.100",
        peer_ip="192.168.1.50",
        local_api_port=8000,
        peer_api_port=8000,
        local_udp_port=5001,
        peer_udp_port=5002,
    )

    assert session.status == SessionStatus.ESTABLISHED
    assert session.session_token_hash == hash_token(raw_token)
    assert session.session_token_hash != raw_token  # Stored hash, not plain token

    # Token validation
    assert sm.validate_session_token(raw_token) is True
    assert sm.validate_session_token("wrong_token_value") is False

    # UDP ports and receiver ready
    sm.set_receiver_ready(True)
    assert session.receiver_ready is True

    # Inactivity / Expiry check
    assert sm.is_session_expired(max_idle_seconds=60) is False
    session.updated_at = datetime.fromtimestamp(100.0, tz=timezone.utc)
    assert sm.is_session_expired(max_idle_seconds=60) is True

    # Close session
    sm.close_session()
    assert sm.active_session is None
    assert sm.validate_session_token(raw_token) is False


# ---------------------------------------------------------------------------
# Zeroconf Discovery Integration Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_zeroconf_receiver_advertisement_and_discovery() -> None:
    """Two independent discovery managers: one advertises as Receiver, other discovers it."""
    # Shared AsyncZeroconf instance over loopback to avoid network collisions
    aiozc = AsyncZeroconf(ip_version=IPVersion.V4Only)

    receiver_id = uuid.uuid4()
    sender_id = uuid.uuid4()

    receiver_mgr = DeviceDiscoveryManager(aiozc=aiozc)
    sender_mgr = DeviceDiscoveryManager(aiozc=aiozc)

    try:
        # Receiver advertises availability
        await receiver_mgr.start_advertising(
            device_id=receiver_id,
            device_name="TestReceiverLaptop",
            api_port=8001,
            udp_port=5001,
            ip_address="127.0.0.1",
        )

        # Sender starts discovery
        discovered_event = asyncio.Event()

        def on_discovered(device) -> None:
            if device.device_id == receiver_id:
                discovered_event.set()

        sender_mgr.on_device_discovered = on_discovered
        await sender_mgr.start_discovery()

        # Wait for sender to discover receiver via mDNS
        await asyncio.wait_for(discovered_event.wait(), timeout=6.0)

        devices = sender_mgr.get_discovered_devices()
        matching = [d for d in devices if d.device_id == receiver_id]
        assert len(matching) == 1
        assert matching[0].device_name == "TestReceiverLaptop"
        assert matching[0].api_port == 8001
        assert matching[0].udp_port == 5001
        assert matching[0].role == DeviceRole.RECEIVER

    finally:
        await sender_mgr.close()
        await receiver_mgr.close()
        await aiozc.async_close()

