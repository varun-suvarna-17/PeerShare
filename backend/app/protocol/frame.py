"""Binary frame format, encoding, decoding and validation for PeerShare."""

from dataclasses import dataclass, field
import struct
from typing import Optional, Union
import uuid

from app.protocol.checksum import calculate_crc32
from app.protocol.constants import (
    HEADER_SIZE,
    MAGIC,
    MAX_FRAME_INDEX,
    MAX_PAYLOAD_SIZE,
    PROTOCOL_VERSION,
    SEQ_NUM_16BIT_MAX,
    AckType,
    FrameType,
)
from app.protocol.exceptions import (
    CorruptedFrameError,
    FrameDecodeError,
    FrameIndexOutOfRangeError,
    FrameTooShortError,
    InvalidAckTypeError,
    InvalidFrameTypeError,
    InvalidMagicError,
    InvalidPayloadLengthError,
    PayloadTooLargeError,
    SequenceNumberOutOfRangeError,
    UnsupportedVersionError,
)

# Struct formats:
# Big-endian:
# DATA prefix (44 bytes): magic (2s), version (B), frame_type (B),
#                         session_id (16s), transfer_id (16s),
#                         sequence_number (H), frame_index (I), payload_length (H)
DATA_PREFIX_FORMAT = "!2s B B 16s 16s H I H"
DATA_PREFIX_SIZE = struct.calcsize(DATA_PREFIX_FORMAT)  # 44 bytes

# ACK prefix (44 bytes): magic (2s), version (B), frame_type (B),
#                        session_id (16s), transfer_id (16s),
#                        ack_number (H), frame_index (I), ack_type (B), reserved (B)
ACK_PREFIX_FORMAT = "!2s B B 16s 16s H I B B"
ACK_PREFIX_SIZE = struct.calcsize(ACK_PREFIX_FORMAT)  # 44 bytes

CHECKSUM_FORMAT = "!I"
CHECKSUM_SIZE = struct.calcsize(CHECKSUM_FORMAT)  # 4 bytes

assert DATA_PREFIX_SIZE + CHECKSUM_SIZE == HEADER_SIZE
assert ACK_PREFIX_SIZE + CHECKSUM_SIZE == HEADER_SIZE


def _normalize_uuid(val: Union[uuid.UUID, str, bytes]) -> uuid.UUID:
    """Normalize a UUID from string, bytes, or UUID instance."""
    if isinstance(val, uuid.UUID):
        return val
    if isinstance(val, bytes):
        if len(val) == 16:
            return uuid.UUID(bytes=val)
        return uuid.UUID(val.decode("ascii"))
    if isinstance(val, str):
        return uuid.UUID(val)
    raise TypeError(f"Expected uuid.UUID, str, or bytes, got {type(val).__name__}")


@dataclass
class DataFrame:
    """Represents a wire-level DATA or FIN frame."""
    session_id: uuid.UUID
    transfer_id: uuid.UUID
    sequence_number: int
    frame_index: int
    payload: bytes = b""
    frame_type: FrameType = FrameType.DATA
    checksum: Optional[int] = None

    def __post_init__(self) -> None:
        self.session_id = _normalize_uuid(self.session_id)
        self.transfer_id = _normalize_uuid(self.transfer_id)

        if isinstance(self.frame_type, int) and not isinstance(self.frame_type, FrameType):
            try:
                self.frame_type = FrameType(self.frame_type)
            except ValueError:
                raise InvalidFrameTypeError(f"Invalid frame type: {self.frame_type}")

        if self.frame_type not in (FrameType.DATA, FrameType.FIN):
            raise InvalidFrameTypeError(
                f"DataFrame frame_type must be DATA (1) or FIN (3), got {self.frame_type}"
            )

        if not (0 <= self.sequence_number <= SEQ_NUM_16BIT_MAX):
            raise SequenceNumberOutOfRangeError(
                f"Sequence number {self.sequence_number} out of range [0, {SEQ_NUM_16BIT_MAX}]"
            )

        if not (0 <= self.frame_index <= MAX_FRAME_INDEX):
            raise FrameIndexOutOfRangeError(
                f"Frame index {self.frame_index} out of range [0, {MAX_FRAME_INDEX}]"
            )

        if len(self.payload) > MAX_PAYLOAD_SIZE:
            raise PayloadTooLargeError(
                f"Payload size {len(self.payload)} exceeds maximum allowed {MAX_PAYLOAD_SIZE}"
            )

    @property
    def payload_length(self) -> int:
        return len(self.payload)

    @property
    def session_id_bytes(self) -> bytes:
        return self.session_id.bytes

    @property
    def transfer_id_bytes(self) -> bytes:
        return self.transfer_id.bytes

    def encode(self) -> bytes:
        """Encode this data frame into its binary wire representation."""
        return encode_data_frame(self)

    @classmethod
    def decode(cls, raw_bytes: bytes) -> "DataFrame":
        """Decode a binary wire representation into a DataFrame."""
        return decode_data_frame(raw_bytes)


@dataclass
class AckFrame:
    """Represents a wire-level ACK or FIN_ACK frame."""
    session_id: uuid.UUID
    transfer_id: uuid.UUID
    ack_number: int
    frame_index: int
    ack_type: AckType = AckType.INDIVIDUAL
    frame_type: FrameType = FrameType.ACK
    checksum: Optional[int] = None

    def __post_init__(self) -> None:
        self.session_id = _normalize_uuid(self.session_id)
        self.transfer_id = _normalize_uuid(self.transfer_id)

        if isinstance(self.frame_type, int) and not isinstance(self.frame_type, FrameType):
            try:
                self.frame_type = FrameType(self.frame_type)
            except ValueError:
                raise InvalidFrameTypeError(f"Invalid frame type: {self.frame_type}")

        if self.frame_type not in (FrameType.ACK, FrameType.FIN_ACK):
            raise InvalidFrameTypeError(
                f"AckFrame frame_type must be ACK (2) or FIN_ACK (4), got {self.frame_type}"
            )

        if isinstance(self.ack_type, int) and not isinstance(self.ack_type, AckType):
            try:
                self.ack_type = AckType(self.ack_type)
            except ValueError:
                raise InvalidAckTypeError(f"Invalid ACK type: {self.ack_type}")

        if not (0 <= self.ack_number <= SEQ_NUM_16BIT_MAX):
            raise SequenceNumberOutOfRangeError(
                f"ACK number {self.ack_number} out of range [0, {SEQ_NUM_16BIT_MAX}]"
            )

        if not (0 <= self.frame_index <= MAX_FRAME_INDEX):
            raise FrameIndexOutOfRangeError(
                f"Frame index {self.frame_index} out of range [0, {MAX_FRAME_INDEX}]"
            )

    @property
    def session_id_bytes(self) -> bytes:
        return self.session_id.bytes

    @property
    def transfer_id_bytes(self) -> bytes:
        return self.transfer_id.bytes

    def encode(self) -> bytes:
        """Encode this ACK frame into its binary wire representation."""
        return encode_ack_frame(self)

    @classmethod
    def decode(cls, raw_bytes: bytes) -> "AckFrame":
        """Decode a binary wire representation into an AckFrame."""
        return decode_ack_frame(raw_bytes)


def encode_data_frame(frame: DataFrame) -> bytes:
    """Encode a DataFrame into its binary wire representation.

    Layout:
      0..1:   Magic bytes (b"PS")
      2:      Protocol version (1)
      3:      Frame type (DATA=1, FIN=3)
      4..19:  Session ID (16 bytes)
      20..35: Transfer ID (16 bytes)
      36..37: Sequence number (uint16)
      38..41: Absolute frame index (uint32)
      42..43: Payload length (uint16)
      44..47: CRC32 checksum (uint32)
      48..:   Payload bytes

    Args:
        frame: The DataFrame to encode.

    Returns:
        Encoded binary packet bytes.
    """
    prefix = struct.pack(
        DATA_PREFIX_FORMAT,
        MAGIC,
        PROTOCOL_VERSION,
        int(frame.frame_type),
        frame.session_id_bytes,
        frame.transfer_id_bytes,
        frame.sequence_number,
        frame.frame_index,
        frame.payload_length,
    )
    checksum = calculate_crc32(prefix + frame.payload)
    frame.checksum = checksum
    checksum_bytes = struct.pack(CHECKSUM_FORMAT, checksum)
    return prefix + checksum_bytes + frame.payload


def decode_data_frame(raw_bytes: bytes) -> DataFrame:
    """Decode binary bytes into a DataFrame, validating magic, version, length and CRC32.

    Args:
        raw_bytes: Wire datagram bytes.

    Returns:
        Decoded DataFrame instance.

    Raises:
        FrameTooShortError: If bytes length < HEADER_SIZE (48 bytes).
        InvalidMagicError: If magic bytes are not b"PS".
        UnsupportedVersionError: If protocol version != 1.
        InvalidFrameTypeError: If frame type is not DATA or FIN.
        InvalidPayloadLengthError: If payload length field does not match payload length.
        CorruptedFrameError: If CRC32 checksum verification fails.
    """
    if len(raw_bytes) < HEADER_SIZE:
        raise FrameTooShortError(
            f"Frame length {len(raw_bytes)} is shorter than minimum header size {HEADER_SIZE}"
        )

    magic = raw_bytes[:2]
    if magic != MAGIC:
        raise InvalidMagicError(f"Invalid magic identifier: expected {MAGIC!r}, got {magic!r}")

    version = raw_bytes[2]
    if version != PROTOCOL_VERSION:
        raise UnsupportedVersionError(
            f"Unsupported protocol version: expected {PROTOCOL_VERSION}, got {version}"
        )

    frame_type_val = raw_bytes[3]
    try:
        frame_type = FrameType(frame_type_val)
    except ValueError:
        raise InvalidFrameTypeError(f"Invalid frame type: {frame_type_val}")

    if frame_type not in (FrameType.DATA, FrameType.FIN):
        raise InvalidFrameTypeError(
            f"Expected DATA (1) or FIN (3) frame type, got {frame_type}"
        )

    (
        _,
        _,
        _,
        session_id_bytes,
        transfer_id_bytes,
        sequence_number,
        frame_index,
        payload_length,
    ) = struct.unpack(DATA_PREFIX_FORMAT, raw_bytes[:DATA_PREFIX_SIZE])

    received_checksum = struct.unpack(
        CHECKSUM_FORMAT, raw_bytes[DATA_PREFIX_SIZE:HEADER_SIZE]
    )[0]
    payload = raw_bytes[HEADER_SIZE:]

    if len(payload) != payload_length:
        raise InvalidPayloadLengthError(
            f"Declared payload length ({payload_length}) does not match actual payload length ({len(payload)})"
        )

    expected_checksum = calculate_crc32(raw_bytes[:DATA_PREFIX_SIZE] + payload)
    if received_checksum != expected_checksum:
        raise CorruptedFrameError(
            expected=expected_checksum,
            actual=received_checksum,
        )

    return DataFrame(
        session_id=uuid.UUID(bytes=session_id_bytes),
        transfer_id=uuid.UUID(bytes=transfer_id_bytes),
        sequence_number=sequence_number,
        frame_index=frame_index,
        payload=payload,
        frame_type=frame_type,
        checksum=received_checksum,
    )


def encode_ack_frame(frame: AckFrame) -> bytes:
    """Encode an AckFrame into its binary wire representation.

    Layout (48 bytes):
      0..1:   Magic bytes (b"PS")
      2:      Protocol version (1)
      3:      Frame type (ACK=2, FIN_ACK=4)
      4..19:  Session ID (16 bytes)
      20..35: Transfer ID (16 bytes)
      36..37: ACK number (uint16)
      38..41: Absolute frame index (uint32)
      42:     ACK type (INDIVIDUAL=1, CUMULATIVE=2)
      43:     Reserved (uint8, 0)
      44..47: CRC32 checksum (uint32)

    Args:
        frame: The AckFrame to encode.

    Returns:
        Encoded 48-byte binary packet bytes.
    """
    prefix = struct.pack(
        ACK_PREFIX_FORMAT,
        MAGIC,
        PROTOCOL_VERSION,
        int(frame.frame_type),
        frame.session_id_bytes,
        frame.transfer_id_bytes,
        frame.ack_number,
        frame.frame_index,
        int(frame.ack_type),
        0,  # reserved byte
    )
    checksum = calculate_crc32(prefix)
    frame.checksum = checksum
    checksum_bytes = struct.pack(CHECKSUM_FORMAT, checksum)
    return prefix + checksum_bytes


def decode_ack_frame(raw_bytes: bytes) -> AckFrame:
    """Decode binary bytes into an AckFrame, validating magic, version, length and CRC32.

    Args:
        raw_bytes: Wire datagram bytes.

    Returns:
        Decoded AckFrame instance.

    Raises:
        FrameTooShortError: If bytes length < HEADER_SIZE (48 bytes).
        FrameDecodeError: If ACK frame contains unexpected trailing bytes (> 48 bytes).
        InvalidMagicError: If magic bytes are not b"PS".
        UnsupportedVersionError: If protocol version != 1.
        InvalidFrameTypeError: If frame type is not ACK or FIN_ACK.
        InvalidAckTypeError: If ACK type is unrecognized.
        CorruptedFrameError: If CRC32 checksum verification fails.
    """
    if len(raw_bytes) < HEADER_SIZE:
        raise FrameTooShortError(
            f"Frame length {len(raw_bytes)} is shorter than ACK header size {HEADER_SIZE}"
        )
    if len(raw_bytes) > HEADER_SIZE:
        raise FrameDecodeError(
            f"ACK frame cannot have extra trailing payload (expected {HEADER_SIZE} bytes, got {len(raw_bytes)})"
        )

    magic = raw_bytes[:2]
    if magic != MAGIC:
        raise InvalidMagicError(f"Invalid magic identifier: expected {MAGIC!r}, got {magic!r}")

    version = raw_bytes[2]
    if version != PROTOCOL_VERSION:
        raise UnsupportedVersionError(
            f"Unsupported protocol version: expected {PROTOCOL_VERSION}, got {version}"
        )

    frame_type_val = raw_bytes[3]
    try:
        frame_type = FrameType(frame_type_val)
    except ValueError:
        raise InvalidFrameTypeError(f"Invalid frame type: {frame_type_val}")

    if frame_type not in (FrameType.ACK, FrameType.FIN_ACK):
        raise InvalidFrameTypeError(
            f"Expected ACK (2) or FIN_ACK (4) frame type, got {frame_type}"
        )

    (
        _,
        _,
        _,
        session_id_bytes,
        transfer_id_bytes,
        ack_number,
        frame_index,
        ack_type_val,
        _,
    ) = struct.unpack(ACK_PREFIX_FORMAT, raw_bytes[:ACK_PREFIX_SIZE])

    try:
        ack_type = AckType(ack_type_val)
    except ValueError:
        raise InvalidAckTypeError(f"Invalid ACK type: {ack_type_val}")

    received_checksum = struct.unpack(
        CHECKSUM_FORMAT, raw_bytes[ACK_PREFIX_SIZE:HEADER_SIZE]
    )[0]

    expected_checksum = calculate_crc32(raw_bytes[:ACK_PREFIX_SIZE])
    if received_checksum != expected_checksum:
        raise CorruptedFrameError(
            expected=expected_checksum,
            actual=received_checksum,
        )

    return AckFrame(
        session_id=uuid.UUID(bytes=session_id_bytes),
        transfer_id=uuid.UUID(bytes=transfer_id_bytes),
        ack_number=ack_number,
        frame_index=frame_index,
        ack_type=ack_type,
        frame_type=frame_type,
        checksum=received_checksum,
    )


def decode_frame(raw_bytes: bytes) -> Union[DataFrame, AckFrame]:
    """Decode any incoming wire frame by inspecting its frame type after header verification.

    Args:
        raw_bytes: Incoming datagram bytes.

    Returns:
        DataFrame or AckFrame instance.

    Raises:
        FrameTooShortError: If bytes length < HEADER_SIZE.
        InvalidMagicError: If magic bytes are not b"PS".
        UnsupportedVersionError: If protocol version != 1.
        InvalidFrameTypeError: If frame type is unrecognized.
        CorruptedFrameError: If CRC32 checksum fails.
    """
    if len(raw_bytes) < HEADER_SIZE:
        raise FrameTooShortError(
            f"Frame length {len(raw_bytes)} is shorter than header size {HEADER_SIZE}"
        )

    magic = raw_bytes[:2]
    if magic != MAGIC:
        raise InvalidMagicError(f"Invalid magic identifier: expected {MAGIC!r}, got {magic!r}")

    version = raw_bytes[2]
    if version != PROTOCOL_VERSION:
        raise UnsupportedVersionError(
            f"Unsupported protocol version: expected {PROTOCOL_VERSION}, got {version}"
        )

    frame_type_val = raw_bytes[3]
    try:
        frame_type = FrameType(frame_type_val)
    except ValueError:
        raise InvalidFrameTypeError(f"Invalid frame type: {frame_type_val}")

    if frame_type in (FrameType.DATA, FrameType.FIN):
        return decode_data_frame(raw_bytes)
    elif frame_type in (FrameType.ACK, FrameType.FIN_ACK):
        return decode_ack_frame(raw_bytes)
    else:
        raise InvalidFrameTypeError(f"Unhandled frame type: {frame_type}")

