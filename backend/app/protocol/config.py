"""Configuration model for ARQ protocols."""

from dataclasses import dataclass
from typing import Optional, Union

from app.protocol.constants import (
    MAX_PAYLOAD_SIZE,
    SEQ_NUM_16BIT_MODULO,
    STOP_AND_WAIT_MODULO,
    ProtocolType,
)
from app.protocol.exceptions import ProtocolError
from app.protocol.sequence import validate_sr_window_sizes


class InvalidProtocolConfigError(ProtocolError):
    """Raised when protocol configuration parameters are invalid."""
    pass


@dataclass
class ProtocolConfig:
    """Stores configuration for the selected ARQ protocol."""
    protocol: ProtocolType
    sender_window_size: int = 1
    receiver_window_size: int = 1
    timeout_ms: int = 1000
    max_retries: int = 5
    packet_loss_percentage: float = 0.0
    frame_delay_ms: int = 100
    loss_seed: Optional[int] = None
    sequence_number_bits: int = 16
    payload_size: int = MAX_PAYLOAD_SIZE

    def __post_init__(self) -> None:
        if isinstance(self.protocol, str) and not isinstance(self.protocol, ProtocolType):
            try:
                self.protocol = ProtocolType(self.protocol)
            except ValueError:
                raise InvalidProtocolConfigError(f"Unknown protocol: {self.protocol}")

        if self.timeout_ms <= 0:
            raise InvalidProtocolConfigError(f"timeout_ms must be > 0, got {self.timeout_ms}")

        if self.max_retries < 0:
            raise InvalidProtocolConfigError(f"max_retries must be >= 0, got {self.max_retries}")

        if not (0.0 <= self.packet_loss_percentage <= 100.0):
            raise InvalidProtocolConfigError(
                f"packet_loss_percentage must be in [0.0, 100.0], got {self.packet_loss_percentage}"
            )

        if not (0 < self.payload_size <= MAX_PAYLOAD_SIZE):
            raise InvalidProtocolConfigError(
                f"payload_size must be in [1, {MAX_PAYLOAD_SIZE}], got {self.payload_size}"
            )

        # Validate protocol-specific window constraints
        if self.protocol == ProtocolType.STOP_AND_WAIT:
            if self.sender_window_size != 1 or self.receiver_window_size != 1:
                raise InvalidProtocolConfigError("Stop-and-Wait must use window sizes of 1")
            self.sequence_number_bits = 1

        elif self.protocol == ProtocolType.GO_BACK_N:
            if self.receiver_window_size != 1:
                raise InvalidProtocolConfigError("Go-Back-N receiver window size must be 1")
            if self.sender_window_size <= 0 or self.sender_window_size >= SEQ_NUM_16BIT_MODULO:
                raise InvalidProtocolConfigError(
                    f"Go-Back-N sender window size must be in [1, {SEQ_NUM_16BIT_MODULO - 1}]"
                )

        elif self.protocol == ProtocolType.SELECTIVE_REPEAT:
            modulo = 1 << self.sequence_number_bits
            if not validate_sr_window_sizes(self.sender_window_size, self.receiver_window_size, modulo):
                raise InvalidProtocolConfigError(
                    f"Selective Repeat window sizes ({self.sender_window_size} + {self.receiver_window_size}) "
                    f"must not exceed sequence space {modulo}"
                )


def get_default_config(protocol: Union[ProtocolType, str]) -> ProtocolConfig:
    """Generate default configuration for the specified ARQ protocol."""
    if isinstance(protocol, str):
        protocol = ProtocolType(protocol)

    if protocol == ProtocolType.STOP_AND_WAIT:
        return ProtocolConfig(
            protocol=ProtocolType.STOP_AND_WAIT,
            sender_window_size=1,
            receiver_window_size=1,
            timeout_ms=1000,
            max_retries=5,
            sequence_number_bits=1,
        )
    elif protocol == ProtocolType.GO_BACK_N:
        return ProtocolConfig(
            protocol=ProtocolType.GO_BACK_N,
            sender_window_size=4,
            receiver_window_size=1,
            timeout_ms=1000,
            max_retries=5,
            sequence_number_bits=16,
        )
    elif protocol == ProtocolType.SELECTIVE_REPEAT:
        return ProtocolConfig(
            protocol=ProtocolType.SELECTIVE_REPEAT,
            sender_window_size=4,
            receiver_window_size=4,
            timeout_ms=1000,
            max_retries=5,
            sequence_number_bits=16,
        )
    else:
        raise ValueError(f"Unsupported protocol type: {protocol}")

