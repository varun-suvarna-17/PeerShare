"""Session Manager for PeerShare connection and session lifecycle."""

from datetime import datetime, timezone
import hashlib
import hmac
import logging
import secrets
from typing import Dict, List, Optional, Tuple
import uuid

from app.discovery.device import DeviceRole, DiscoveryMethod
from app.session.models import (
    ConnectionRequest,
    ConnectionStatus,
    Session,
    SessionStatus,
)

logger = logging.getLogger(__name__)


def hash_token(raw_token: str) -> str:
    """Hash raw session token using SHA-256 for secure storage."""
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


class SessionManager:
    """Manages connection approval, session tokens, UDP port coordination, and session states."""

    def __init__(self, local_device_id: uuid.UUID) -> None:
        self.local_device_id = local_device_id
        self.connection_requests: Dict[uuid.UUID, ConnectionRequest] = {}
        self.active_session: Optional[Session] = None
        self._raw_session_token_for_peer: Optional[str] = None  # Temporary until returned to peer

    # -----------------------------------------------------------------------
    # Connection Requests & Approval
    # -----------------------------------------------------------------------

    def create_connection_request(
        self,
        sender_device_id: uuid.UUID,
        sender_device_name: str,
        sender_ip: str,
        discovery_method: DiscoveryMethod = DiscoveryMethod.ZEROCONF,
    ) -> ConnectionRequest:
        """Create an incoming connection request on the Receiver."""
        req_id = uuid.uuid4()
        req = ConnectionRequest(
            connection_id=req_id,
            sender_device_id=sender_device_id,
            sender_device_name=sender_device_name,
            sender_ip=sender_ip,
            receiver_device_id=self.local_device_id,
            discovery_method=discovery_method,
            status=ConnectionStatus.PENDING_APPROVAL,
        )
        self.connection_requests[req_id] = req
        return req

    def get_pending_requests(self) -> List[ConnectionRequest]:
        """Return list of active, unexpired pending connection requests."""
        now = datetime.now(timezone.utc)
        pending = []
        for req in self.connection_requests.values():
            if req.status == ConnectionStatus.PENDING_APPROVAL:
                if req.is_expired():
                    req.status = ConnectionStatus.EXPIRED
                else:
                    pending.append(req)
        return pending

    def get_connection_request(self, connection_id: uuid.UUID) -> Optional[ConnectionRequest]:
        """Retrieve connection request by ID."""
        return self.connection_requests.get(connection_id)

    def approve_connection(self, connection_id: uuid.UUID) -> Tuple[bool, str]:
        """Approve an incoming connection request."""
        req = self.connection_requests.get(connection_id)
        if req is None:
            return False, "REQUEST_NOT_FOUND"

        if req.is_expired():
            req.status = ConnectionStatus.EXPIRED
            return False, "REQUEST_EXPIRED"

        if req.status != ConnectionStatus.PENDING_APPROVAL:
            return False, f"CANNOT_APPROVE_{req.status.value}"

        req.status = ConnectionStatus.APPROVED
        return True, "APPROVED"

    def reject_connection(self, connection_id: uuid.UUID) -> Tuple[bool, str]:
        """Reject an incoming connection request."""
        req = self.connection_requests.get(connection_id)
        if req is None:
            return False, "REQUEST_NOT_FOUND"

        if req.status != ConnectionStatus.PENDING_APPROVAL:
            return False, f"CANNOT_REJECT_{req.status.value}"

        req.status = ConnectionStatus.REJECTED
        return True, "REJECTED"

    # -----------------------------------------------------------------------
    # Session Establishment & Token Management
    # -----------------------------------------------------------------------

    def establish_session(
        self,
        session_id: uuid.UUID,
        peer_device_id: uuid.UUID,
        local_role: DeviceRole,
        local_ip: str,
        peer_ip: str,
        local_api_port: int,
        peer_api_port: int,
        local_udp_port: int = 0,
        peer_udp_port: int = 0,
        raw_token: Optional[str] = None,
    ) -> Tuple[Session, str]:
        """Establish a new session and generate a secure session token.

        Returns:
            Tuple of (Session, raw_token_string)
        """
        # Close any existing session
        if self.active_session is not None:
            self.close_session()

        # Generate or use provided token
        token = raw_token or secrets.token_urlsafe(32)
        token_hash = hash_token(token)

        session = Session(
            session_id=session_id,
            local_device_id=self.local_device_id,
            peer_device_id=peer_device_id,
            local_role=local_role,
            local_ip=local_ip,
            peer_ip=peer_ip,
            local_api_port=local_api_port,
            peer_api_port=peer_api_port,
            local_udp_port=local_udp_port,
            peer_udp_port=peer_udp_port,
            session_token_hash=token_hash,
            status=SessionStatus.ESTABLISHED,
        )
        self.active_session = session
        return session, token

    def validate_session_token(self, token: str) -> bool:
        """Validate candidate token against the active session's token hash in constant time."""
        if self.active_session is None or self.active_session.status != SessionStatus.ESTABLISHED:
            return False

        candidate_hash = hash_token(token)
        return hmac.compare_digest(
            self.active_session.session_token_hash.encode("ascii"),
            candidate_hash.encode("ascii"),
        )

    def set_udp_ports(self, local_udp_port: int, peer_udp_port: int) -> None:
        """Update negotiated UDP communication ports."""
        if self.active_session is not None:
            self.active_session.local_udp_port = local_udp_port
            self.active_session.peer_udp_port = peer_udp_port
            self.active_session.update_timestamp()

    def set_receiver_ready(self, ready: bool = True) -> None:
        """Signal that receiver's UDP socket is open and ready to receive frames."""
        if self.active_session is not None:
            self.active_session.receiver_ready = ready
            self.active_session.update_timestamp()

    def touch_session(self) -> None:
        """Update last seen activity on active session."""
        if self.active_session is not None:
            self.active_session.update_timestamp()

    def is_session_expired(self, max_idle_seconds: float = 120.0) -> bool:
        """Check whether the active session has timed out due to inactivity."""
        if self.active_session is None:
            return True
        now = datetime.now(timezone.utc)
        elapsed = (now - self.active_session.updated_at).total_seconds()
        return elapsed > max_idle_seconds

    def close_session(self) -> None:
        """Close and terminate the active session."""
        if self.active_session is not None:
            self.active_session.status = SessionStatus.CLOSED
            self.active_session.update_timestamp()
            self.active_session = None

