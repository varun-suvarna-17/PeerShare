"""PIN management for manual IP fallback connection."""

from dataclasses import dataclass
from datetime import datetime, timezone
import hmac
import secrets
from typing import Optional, Tuple


@dataclass
class PinState:
    """Stores the active temporary PIN and attempt counter."""
    pin: str
    created_at: datetime
    expires_at: datetime
    attempts: int = 0
    locked: bool = False
    used: bool = False


class PinManager:
    """Manages generation, expiration, and constant-time verification of temporary 6-digit connection PINs."""

    PIN_EXPIRY_SECONDS: int = 120
    MAX_ATTEMPTS: int = 5

    def __init__(self) -> None:
        self._current_pin_state: Optional[PinState] = None

    def generate_pin(self) -> Tuple[str, int]:
        """Generate a new temporary 6-digit PIN expiring in 120 seconds.

        Returns:
            Tuple of (pin_string, expires_in_seconds)
        """
        now = datetime.now(timezone.utc)
        expires_at = datetime.fromtimestamp(now.timestamp() + self.PIN_EXPIRY_SECONDS, tz=timezone.utc)
        pin_code = f"{secrets.randbelow(1_000_000):06d}"

        self._current_pin_state = PinState(
            pin=pin_code,
            created_at=now,
            expires_at=expires_at,
            attempts=0,
            locked=False,
            used=False,
        )
        return pin_code, self.PIN_EXPIRY_SECONDS

    def get_active_pin(self) -> Optional[str]:
        """Return the active PIN if valid and not expired."""
        if self._current_pin_state is None:
            return None
        if self.is_expired() or self._current_pin_state.locked or self._current_pin_state.used:
            return None
        return self._current_pin_state.pin

    def is_expired(self) -> bool:
        """Check whether the active PIN has expired."""
        if self._current_pin_state is None:
            return True
        now = datetime.now(timezone.utc)
        return now > self._current_pin_state.expires_at

    def is_locked(self) -> bool:
        """Check whether PIN attempts are locked."""
        if self._current_pin_state is None:
            return False
        return self._current_pin_state.locked

    def verify_pin(self, candidate_pin: str) -> Tuple[bool, str]:
        """Verify candidate PIN using constant-time comparison.

        Returns:
            Tuple of (success: bool, message: str)
        """
        if self._current_pin_state is None:
            return False, "NO_PIN_GENERATED"

        if self._current_pin_state.locked:
            return False, "PIN_LOCKED"

        if self._current_pin_state.used:
            return False, "PIN_ALREADY_USED"

        if self.is_expired():
            return False, "PIN_EXPIRED"

        # Increment attempt counter
        self._current_pin_state.attempts += 1

        # Check maximum failed attempts
        if self._current_pin_state.attempts > self.MAX_ATTEMPTS:
            self._current_pin_state.locked = True
            return False, "PIN_LOCKED"

        # Constant-time comparison
        is_valid = hmac.compare_digest(
            self._current_pin_state.pin.encode("ascii"),
            candidate_pin.encode("ascii"),
        )

        if is_valid:
            self._current_pin_state.used = True
            return True, "SUCCESS"
        else:
            if self._current_pin_state.attempts >= self.MAX_ATTEMPTS:
                self._current_pin_state.locked = True
                return False, "PIN_LOCKED"
            return False, "INVALID_PIN"

    def clear(self) -> None:
        """Clear the current PIN state."""
        self._current_pin_state = None

