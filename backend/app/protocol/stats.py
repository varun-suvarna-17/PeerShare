"""Transfer statistics model."""

from dataclasses import dataclass


@dataclass
class TransferStatistics:
    """Stores operational statistics generated during file transfer."""
    total_frames: int = 0
    total_transmissions: int = 0
    unique_frames_received: int = 0
    total_acks_sent: int = 0
    total_acks_received: int = 0
    total_retransmissions: int = 0
    dropped_data_frames: int = 0
    dropped_ack_frames: int = 0
    corrupted_frames: int = 0
    discarded_frames: int = 0
    buffered_frames: int = 0
    total_bytes: int = 0
    duration_seconds: float = 0.0
    throughput_kbps: float = 0.0
    integrity_verified: bool = False

    def finalize(self, duration_seconds: float) -> None:
        """Finalize duration and calculate effective throughput in kbps."""
        self.duration_seconds = max(0.0, duration_seconds)
        if self.duration_seconds > 0:
            # (total_bytes * 8 bits) / (duration_seconds * 1000)
            self.throughput_kbps = round((self.total_bytes * 8.0) / (self.duration_seconds * 1000.0), 2)
        else:
            self.throughput_kbps = 0.0

