"""PeerShare Protocol Foundation and ARQ Engine package."""

from app.protocol.base import BaseReceiver, BaseSender
from app.protocol.checksum import (
    calculate_crc32,
    verify_crc32,
)
from app.protocol.config import (
    InvalidProtocolConfigError,
    ProtocolConfig,
    get_default_config,
)
from app.protocol.constants import (
    HEADER_SIZE,
    MAGIC,
    MAX_FRAME_INDEX,
    MAX_PAYLOAD_SIZE,
    PROTOCOL_VERSION,
    SEQ_NUM_16BIT_MAX,
    SEQ_NUM_16BIT_MODULO,
    STOP_AND_WAIT_MODULO,
    AckType,
    FrameType,
    ProtocolType,
    TransferStatus,
)
from app.protocol.exceptions import (
    CorruptedFrameError,
    FrameDecodeError,
    FrameEncodeError,
    FrameIndexOutOfRangeError,
    FrameTooShortError,
    InvalidAckTypeError,
    InvalidFrameTypeError,
    InvalidMagicError,
    InvalidPayloadLengthError,
    PayloadTooLargeError,
    ProtocolError,
    SequenceNumberOutOfRangeError,
    UnsupportedVersionError,
)
from app.protocol.frame import (
    AckFrame,
    DataFrame,
    decode_ack_frame,
    decode_data_frame,
    decode_frame,
    encode_ack_frame,
    encode_data_frame,
)
from app.protocol.go_back_n import GoBackNReceiver, GoBackNSender
from app.protocol.selective_repeat import (
    SelectiveRepeatReceiver,
    SelectiveRepeatSender,
)
from app.protocol.sequence import (
    is_sequence_in_window,
    next_sequence_number,
    next_stop_and_wait_seq,
    sequence_distance,
    sequence_from_index,
    stop_and_wait_seq_from_index,
    validate_sr_window_sizes,
)
from app.protocol.simulator import NetworkSimulator
from app.protocol.stats import TransferStatistics
from app.protocol.stop_and_wait import (
    StopAndWaitReceiver,
    StopAndWaitSender,
)
from app.protocol.timer import Timer, TimerStatus, get_current_time

__all__ = [
    # Constants
    "MAGIC",
    "PROTOCOL_VERSION",
    "HEADER_SIZE",
    "MAX_PAYLOAD_SIZE",
    "SEQ_NUM_16BIT_MAX",
    "SEQ_NUM_16BIT_MODULO",
    "STOP_AND_WAIT_MODULO",
    "MAX_FRAME_INDEX",
    "FrameType",
    "AckType",
    "ProtocolType",
    "TransferStatus",
    # Config & Stats
    "ProtocolConfig",
    "get_default_config",
    "InvalidProtocolConfigError",
    "TransferStatistics",
    # Timers
    "Timer",
    "TimerStatus",
    "get_current_time",
    # Base
    "BaseSender",
    "BaseReceiver",
    # ARQ Protocols
    "StopAndWaitSender",
    "StopAndWaitReceiver",
    "GoBackNSender",
    "GoBackNReceiver",
    "SelectiveRepeatSender",
    "SelectiveRepeatReceiver",
    # Simulation
    "NetworkSimulator",
    # Models
    "DataFrame",
    "AckFrame",
    # Frame encoding & decoding
    "encode_data_frame",
    "decode_data_frame",
    "encode_ack_frame",
    "decode_ack_frame",
    "decode_frame",
    # CRC32
    "calculate_crc32",
    "verify_crc32",
    # Sequence number & windowing
    "next_sequence_number",
    "sequence_from_index",
    "next_stop_and_wait_seq",
    "stop_and_wait_seq_from_index",
    "sequence_distance",
    "is_sequence_in_window",
    "validate_sr_window_sizes",
    # Exceptions
    "ProtocolError",
    "FrameEncodeError",
    "FrameDecodeError",
    "PayloadTooLargeError",
    "SequenceNumberOutOfRangeError",
    "FrameIndexOutOfRangeError",
    "FrameTooShortError",
    "InvalidMagicError",
    "UnsupportedVersionError",
    "InvalidFrameTypeError",
    "InvalidPayloadLengthError",
    "InvalidAckTypeError",
    "CorruptedFrameError",
]


