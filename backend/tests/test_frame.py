"""Unit tests for binary data frame encoding, decoding, validation, and corruption handling."""

import uuid
import pytest

from app.protocol.constants import (
    HEADER_SIZE,
    MAGIC,
    MAX_PAYLOAD_SIZE,
    PROTOCOL_VERSION,
    FrameType,
)
from app.protocol.exceptions import (
    CorruptedFrameError,
    FrameIndexOutOfRangeError,
    FrameTooShortError,
    InvalidFrameTypeError,
    InvalidMagicError,
    InvalidPayloadLengthError,
    PayloadTooLargeError,
    SequenceNumberOutOfRangeError,
    UnsupportedVersionError,
)
from app.protocol.frame import (
    DataFrame,
    decode_data_frame,
    decode_frame,
    encode_data_frame,
)


@pytest.fixture
def sample_ids() -> tuple[uuid.UUID, uuid.UUID]:
    return uuid.uuid4(), uuid.uuid4()


def test_data_frame_roundtrip_empty_payload(sample_ids: tuple[uuid.UUID, uuid.UUID]) -> None:
    """Encode and decode a DataFrame with empty payload."""
    session_id, transfer_id = sample_ids
    frame = DataFrame(
        session_id=session_id,
        transfer_id=transfer_id,
        sequence_number=0,
        frame_index=0,
        payload=b"",
    )

    encoded = encode_data_frame(frame)
    assert len(encoded) == HEADER_SIZE  # 48 bytes exactly
    assert frame.checksum is not None

    decoded = decode_data_frame(encoded)
    assert decoded.session_id == session_id
    assert decoded.transfer_id == transfer_id
    assert decoded.sequence_number == 0
    assert decoded.frame_index == 0
    assert decoded.payload == b""
    assert decoded.payload_length == 0
    assert decoded.frame_type == FrameType.DATA
    assert decoded.checksum == frame.checksum


def test_data_frame_roundtrip_max_payload(sample_ids: tuple[uuid.UUID, uuid.UUID]) -> None:
    """Encode and decode a DataFrame with maximum 1024-byte payload."""
    session_id, transfer_id = sample_ids
    payload = bytes(range(256)) * 4  # 1024 bytes
    assert len(payload) == MAX_PAYLOAD_SIZE

    frame = DataFrame(
        session_id=session_id,
        transfer_id=transfer_id,
        sequence_number=65535,
        frame_index=131071,
        payload=payload,
    )

    encoded = frame.encode()
    assert len(encoded) == HEADER_SIZE + MAX_PAYLOAD_SIZE

    decoded = DataFrame.decode(encoded)
    assert decoded.session_id == session_id
    assert decoded.transfer_id == transfer_id
    assert decoded.sequence_number == 65535
    assert decoded.frame_index == 131071
    assert decoded.payload == payload
    assert decoded.payload_length == MAX_PAYLOAD_SIZE
    assert decoded.frame_type == FrameType.DATA


def test_fin_frame_roundtrip(sample_ids: tuple[uuid.UUID, uuid.UUID]) -> None:
    """Encode and decode a FIN frame."""
    session_id, transfer_id = sample_ids
    frame = DataFrame(
        session_id=session_id,
        transfer_id=transfer_id,
        sequence_number=12,
        frame_index=12,
        payload=b"",
        frame_type=FrameType.FIN,
    )

    encoded = frame.encode()
    assert len(encoded) == HEADER_SIZE

    decoded = decode_data_frame(encoded)
    assert decoded.frame_type == FrameType.FIN
    assert decoded.sequence_number == 12
    assert decoded.frame_index == 12


def test_string_uuid_support() -> None:
    """DataFrame accepts UUID strings and normalizes to uuid.UUID."""
    s_id_str = "12345678-1234-5678-1234-567812345678"
    t_id_str = "87654321-4321-8765-4321-876543210987"
    frame = DataFrame(
        session_id=s_id_str,
        transfer_id=t_id_str,
        sequence_number=1,
        frame_index=1,
        payload=b"test data",
    )
    assert isinstance(frame.session_id, uuid.UUID)
    assert isinstance(frame.transfer_id, uuid.UUID)
    assert str(frame.session_id) == s_id_str
    assert str(frame.transfer_id) == t_id_str


def test_payload_too_large(sample_ids: tuple[uuid.UUID, uuid.UUID]) -> None:
    """Payload exceeding MAX_PAYLOAD_SIZE must raise PayloadTooLargeError."""
    session_id, transfer_id = sample_ids
    with pytest.raises(PayloadTooLargeError):
        DataFrame(
            session_id=session_id,
            transfer_id=transfer_id,
            sequence_number=0,
            frame_index=0,
            payload=b"x" * (MAX_PAYLOAD_SIZE + 1),
        )


def test_sequence_number_out_of_range(sample_ids: tuple[uuid.UUID, uuid.UUID]) -> None:
    """Sequence numbers outside [0, 65535] must raise SequenceNumberOutOfRangeError."""
    session_id, transfer_id = sample_ids
    with pytest.raises(SequenceNumberOutOfRangeError):
        DataFrame(
            session_id=session_id,
            transfer_id=transfer_id,
            sequence_number=-1,
            frame_index=0,
        )

    with pytest.raises(SequenceNumberOutOfRangeError):
        DataFrame(
            session_id=session_id,
            transfer_id=transfer_id,
            sequence_number=65536,
            frame_index=0,
        )


def test_frame_index_out_of_range(sample_ids: tuple[uuid.UUID, uuid.UUID]) -> None:
    """Frame index < 0 or > 2^32-1 must raise FrameIndexOutOfRangeError."""
    session_id, transfer_id = sample_ids
    with pytest.raises(FrameIndexOutOfRangeError):
        DataFrame(
            session_id=session_id,
            transfer_id=transfer_id,
            sequence_number=0,
            frame_index=-1,
        )

    with pytest.raises(FrameIndexOutOfRangeError):
        DataFrame(
            session_id=session_id,
            transfer_id=transfer_id,
            sequence_number=0,
            frame_index=4294967296,
        )


def test_invalid_frame_type_for_dataframe(sample_ids: tuple[uuid.UUID, uuid.UUID]) -> None:
    """DataFrame cannot have ACK or invalid frame_type."""
    session_id, transfer_id = sample_ids
    with pytest.raises(InvalidFrameTypeError):
        DataFrame(
            session_id=session_id,
            transfer_id=transfer_id,
            sequence_number=0,
            frame_index=0,
            frame_type=FrameType.ACK,
        )

    with pytest.raises(InvalidFrameTypeError):
        DataFrame(
            session_id=session_id,
            transfer_id=transfer_id,
            sequence_number=0,
            frame_index=0,
            frame_type=99,  # type: ignore[arg-type]
        )


def test_decode_frame_too_short() -> None:
    """Bytes shorter than HEADER_SIZE (48 bytes) must raise FrameTooShortError."""
    with pytest.raises(FrameTooShortError):
        decode_data_frame(b"PS\x01\x01" + b"\x00" * 20)


def test_decode_invalid_magic(sample_ids: tuple[uuid.UUID, uuid.UUID]) -> None:
    """Invalid magic identifier must raise InvalidMagicError."""
    session_id, transfer_id = sample_ids
    frame = DataFrame(
        session_id=session_id,
        transfer_id=transfer_id,
        sequence_number=0,
        frame_index=0,
        payload=b"test",
    )
    encoded = bytearray(frame.encode())
    encoded[:2] = b"XX"  # Corrupt magic
    with pytest.raises(InvalidMagicError):
        decode_data_frame(bytes(encoded))


def test_decode_unsupported_version(sample_ids: tuple[uuid.UUID, uuid.UUID]) -> None:
    """Protocol version != 1 must raise UnsupportedVersionError."""
    session_id, transfer_id = sample_ids
    frame = DataFrame(
        session_id=session_id,
        transfer_id=transfer_id,
        sequence_number=0,
        frame_index=0,
    )
    encoded = bytearray(frame.encode())
    encoded[2] = 2  # Version 2
    with pytest.raises(UnsupportedVersionError):
        decode_data_frame(bytes(encoded))


def test_decode_invalid_payload_length(sample_ids: tuple[uuid.UUID, uuid.UUID]) -> None:
    """Truncated payload where length does not match header raises InvalidPayloadLengthError."""
    session_id, transfer_id = sample_ids
    frame = DataFrame(
        session_id=session_id,
        transfer_id=transfer_id,
        sequence_number=0,
        frame_index=0,
        payload=b"1234567890",
    )
    encoded = frame.encode()
    truncated = encoded[:-3]  # Drop 3 payload bytes
    with pytest.raises(InvalidPayloadLengthError):
        decode_data_frame(truncated)


def test_corrupted_payload_fails_crc(sample_ids: tuple[uuid.UUID, uuid.UUID]) -> None:
    """Single bit flip in payload must raise CorruptedFrameError."""
    session_id, transfer_id = sample_ids
    frame = DataFrame(
        session_id=session_id,
        transfer_id=transfer_id,
        sequence_number=5,
        frame_index=5,
        payload=b"Sensitive file chunk content",
    )
    encoded = bytearray(frame.encode())
    # Corrupt payload byte
    encoded[HEADER_SIZE + 2] ^= 0x01

    with pytest.raises(CorruptedFrameError) as exc_info:
        decode_data_frame(bytes(encoded))
    assert exc_info.value.expected != exc_info.value.actual


def test_corrupted_header_fails_crc(sample_ids: tuple[uuid.UUID, uuid.UUID]) -> None:
    """Bit flip in header (sequence number field) must raise CorruptedFrameError."""
    session_id, transfer_id = sample_ids
    frame = DataFrame(
        session_id=session_id,
        transfer_id=transfer_id,
        sequence_number=10,
        frame_index=10,
        payload=b"chunk data",
    )
    encoded = bytearray(frame.encode())
    # Corrupt sequence number byte at offset 37
    encoded[37] ^= 0x01

    with pytest.raises(CorruptedFrameError):
        decode_data_frame(bytes(encoded))


def test_generic_decode_frame_for_data_and_fin(sample_ids: tuple[uuid.UUID, uuid.UUID]) -> None:
    """Generic decode_frame accurately routes DATA and FIN frames."""
    session_id, transfer_id = sample_ids
    data_frame = DataFrame(
        session_id=session_id,
        transfer_id=transfer_id,
        sequence_number=1,
        frame_index=1,
        payload=b"data payload",
    )
    fin_frame = DataFrame(
        session_id=session_id,
        transfer_id=transfer_id,
        sequence_number=2,
        frame_index=2,
        frame_type=FrameType.FIN,
    )

    res_data = decode_frame(data_frame.encode())
    assert isinstance(res_data, DataFrame)
    assert res_data.frame_type == FrameType.DATA
    assert res_data.payload == b"data payload"

    res_fin = decode_frame(fin_frame.encode())
    assert isinstance(res_fin, DataFrame)
    assert res_fin.frame_type == FrameType.FIN

