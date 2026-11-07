"""Retransmission timer models."""

from dataclasses import dataclass
from enum import Enum
import time


class TimerStatus(str, Enum):
    """Timer state."""
    RUNNING = "running"
    EXPIRED = "expired"
    STOPPED = "stopped"


@dataclass
class Timer:
    """Maintains retransmission timing state for a single frame or window."""
    frame_index: int
    started_at: float
    timeout_ms: int
    retry_count: int = 0
    status: TimerStatus = TimerStatus.RUNNING

    def is_expired(self, now: float) -> bool:
        """Check if timer has expired relative to reference timestamp."""
        if self.status != TimerStatus.RUNNING:
            return False
        return (now - self.started_at) * 1000.0 >= self.timeout_ms

    def restart(self, now: float, increment_retries: bool = True) -> None:
        """Restart the timer at the specified reference timestamp."""
        self.started_at = now
        self.status = TimerStatus.RUNNING
        if increment_retries:
            self.retry_count += 1

    def stop(self) -> None:
        """Stop the timer."""
        self.status = TimerStatus.STOPPED


def get_current_time() -> float:
    """Helper to return current monotonic timestamp."""
    return time.monotonic()

