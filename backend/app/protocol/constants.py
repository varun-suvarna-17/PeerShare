"""Constants and Enums for the PeerShare binary wire protocol."""

from enum import Enum, IntEnum

# Protocol identification
MAGIC: bytes = b"PS"
PROTOCOL_VERSION: int = 1

# Header and payload constraints
HEADER_SIZE: int = 48
MAX_PAYLOAD_SIZE: int = 1024

# Sequence number parameters
SEQ_NUM_16BIT_MAX: int = 65535
SEQ_NUM_16BIT_MODULO: int = 65536
STOP_AND_WAIT_MODULO: int = 2
MAX_FRAME_INDEX: int = 4294967295  # 2^32 - 1


class FrameType(IntEnum):
    """Supported binary frame types."""
    DATA = 1
    ACK = 2
    FIN = 3
    FIN_ACK = 4


class AckType(IntEnum):
    """Supported acknowledgement semantics."""
    INDIVIDUAL = 1
    CUMULATIVE = 2


class ProtocolType(str, Enum):
    """Supported ARQ protocols."""
    STOP_AND_WAIT = "stop_and_wait"
    GO_BACK_N = "go_back_n"
    SELECTIVE_REPEAT = "selective_repeat"


class TransferStatus(str, Enum):
    """Transfer operational status states."""
    PENDING = "pending"
    TRANSFERRING = "transferring"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

