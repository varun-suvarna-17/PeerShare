"""Unit tests for binary ACK frame encoding, decoding, validation, and error handling."""

import uuid
import pytest

from app.protocol.constants import (
    HEADER_SIZE,
    MAGIC,
    PROTOCOL_VERSION,
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
    SequenceNumberOutOfRangeError,
    UnsupportedVersionError,
)
from app.protocol.frame import (
    AckFrame,
    decode_ack_frame,
    decode_frame,
    encode_ack_frame,
)


@pytest.fixture
def sample_ids() -> tuple[uuid.UUID, uuid.UUID]:
    return uuid.uuid4(), uuid.uuid4()


def test_ack_frame_roundtrip_individual(sample_ids: tuple[uuid.UUID, uuid.UUID]) -> None:
    """Encode and decode an individual ACK frame."""
    session_id, transfer_id = sample_ids
    frame = AckFrame(
        session_id=session_id,
        transfer_id=transfer_id,
        ack_number=5,
        frame_index=5,
        ack_type=AckType.INDIVIDUAL,
    )

    encoded = encode_ack_frame(frame)
    assert len(encoded) == HEADER_SIZE  # Exactly 48 bytes
    assert frame.checksum is not None

    decoded = decode_ack_frame(encoded)
    assert decoded.session_id == session_id
    assert decoded.transfer_id == transfer_id
    assert decoded.ack_number == 5
    assert decoded.frame_index == 5
    assert decoded.ack_type == AckType.INDIVIDUAL
    assert decoded.frame_type == FrameType.ACK
    assert decoded.checksum == frame.checksum


def test_ack_frame_roundtrip_cumulative(sample_ids: tuple[uuid.UUID, uuid.UUID]) -> None:
    """Encode and decode a cumulative ACK frame."""
    session_id, transfer_id = sample_ids
    frame = AckFrame(
        session_id=session_id,
        transfer_id=transfer_id,
        ack_number=10,
        frame_index=10,
        ack_type=AckType.CUMULATIVE,
    )

    encoded = frame.encode()
    assert len(encoded) == HEADER_SIZE

    decoded = AckFrame.decode(encoded)
    assert decoded.ack_number == 10
    assert decoded.frame_index == 10
    assert decoded.ack_type == AckType.CUMULATIVE
    assert decoded.frame_type == FrameType.ACK


def test_fin_ack_frame_roundtrip(sample_ids: tuple[uuid.UUID, uuid.UUID]) -> None:
    """Encode and decode a FIN_ACK frame."""
    session_id, transfer_id = sample_ids
    frame = AckFrame(
        session_id=session_id,
        transfer_id=transfer_id,
        ack_number=100,
        frame_index=100,
        frame_type=FrameType.FIN_ACK,
    )

    encoded = frame.encode()
    assert len(encoded) == HEADER_SIZE

    decoded = decode_ack_frame(encoded)
    assert decoded.frame_type == FrameType.FIN_ACK
    assert decoded.ack_number == 100
    assert decoded.frame_index == 100


def test_ack_string_uuid_support() -> None:
    """AckFrame accepts UUID strings and normalizes to uuid.UUID."""
    s_id_str = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
    t_id_str = "11111111-2222-3333-4444-555555555555"
    frame = AckFrame(
        session_id=s_id_str,
        transfer_id=t_id_str,
        ack_number=0,
        frame_index=0,
    )
    assert isinstance(frame.session_id, uuid.UUID)
    assert isinstance(frame.transfer_id, uuid.UUID)


def test_ack_number_out_of_range(sample_ids: tuple[uuid.UUID, uuid.UUID]) -> None:
    """ACK number outside [0, 65535] must raise SequenceNumberOutOfRangeError."""
    session_id, transfer_id = sample_ids
    with pytest.raises(SequenceNumberOutOfRangeError):
        AckFrame(
            session_id=session_id,
            transfer_id=transfer_id,
            ack_number=-1,
            frame_index=0,
        )

    with pytest.raises(SequenceNumberOutOfRangeError):
        AckFrame(
            session_id=session_id,
            transfer_id=transfer_id,
            ack_number=65536,
            frame_index=0,
        )


def test_ack_frame_index_out_of_range(sample_ids: tuple[uuid.UUID, uuid.UUID]) -> None:
    """Frame index < 0 or > 2^32-1 must raise FrameIndexOutOfRangeError."""
    session_id, transfer_id = sample_ids
    with pytest.raises(FrameIndexOutOfRangeError):
        AckFrame(
            session_id=session_id,
            transfer_id=transfer_id,
            ack_number=0,
            frame_index=-1,
        )


def test_invalid_frame_type_for_ack(sample_ids: tuple[uuid.UUID, uuid.UUID]) -> None:
    """AckFrame cannot have DATA or invalid frame_type."""
    session_id, transfer_id = sample_ids
    with pytest.raises(InvalidFrameTypeError):
        AckFrame(
            session_id=session_id,
            transfer_id=transfer_id,
            ack_number=0,
            frame_index=0,
            frame_type=FrameType.DATA,
        )


def test_invalid_ack_type(sample_ids: tuple[uuid.UUID, uuid.UUID]) -> None:
    """Invalid ack_type value must raise InvalidAckTypeError."""
    session_id, transfer_id = sample_ids
    with pytest.raises(InvalidAckTypeError):
        AckFrame(
            session_id=session_id,
            transfer_id=transfer_id,
            ack_number=0,
            frame_index=0,
            ack_type=99,  # type: ignore[arg-type]
        )


def test_decode_ack_frame_too_short() -> None:
    """Bytes shorter than 48 bytes must raise FrameTooShortError."""
    with pytest.raises(FrameTooShortError):
        decode_ack_frame(b"PS\x01\x02" + b"\x00" * 10)


def test_decode_ack_frame_extra_bytes(sample_ids: tuple[uuid.UUID, uuid.UUID]) -> None:
    """ACK frame with extra trailing bytes must raise FrameDecodeError."""
    session_id, transfer_id = sample_ids
    frame = AckFrame(
        session_id=session_id,
        transfer_id=transfer_id,
        ack_number=1,
        frame_index=1,
    )
    encoded = frame.encode() + b"extra"
    with pytest.raises(FrameDecodeError):
        decode_ack_frame(encoded)


def test_decode_ack_corrupted_crc(sample_ids: tuple[uuid.UUID, uuid.UUID]) -> None:
    """Corrupted byte in ACK header must fail CRC32 verification."""
    session_id, transfer_id = sample_ids
    frame = AckFrame(
        session_id=session_id,
        transfer_id=transfer_id,
        ack_number=7,
        frame_index=7,
    )
    encoded = bytearray(frame.encode())
    # Corrupt ack_number byte at offset 37
    encoded[37] ^= 0x01

    with pytest.raises(CorruptedFrameError):
        decode_ack_frame(bytes(encoded))


def test_decode_ack_invalid_magic(sample_ids: tuple[uuid.UUID, uuid.UUID]) -> None:
    """Invalid magic identifier in ACK must raise InvalidMagicError."""
    session_id, transfer_id = sample_ids
    frame = AckFrame(
        session_id=session_id,
        transfer_id=transfer_id,
        ack_number=1,
        frame_index=1,
    )
    encoded = bytearray(frame.encode())
    encoded[:2] = b"NO"
    with pytest.raises(InvalidMagicError):
        decode_ack_frame(bytes(encoded))


def test_generic_decode_frame_for_ack_and_fin_ack(sample_ids: tuple[uuid.UUID, uuid.UUID]) -> None:
    """Generic decode_frame accurately routes ACK and FIN_ACK frames."""
    session_id, transfer_id = sample_ids
    ack_frame = AckFrame(
        session_id=session_id,
        transfer_id=transfer_id,
        ack_number=3,
        frame_index=3,
    )
    fin_ack_frame = AckFrame(
        session_id=session_id,
        transfer_id=transfer_id,
        ack_number=4,
        frame_index=4,
        frame_type=FrameType.FIN_ACK,
    )

    res_ack = decode_frame(ack_frame.encode())
    assert isinstance(res_ack, AckFrame)
    assert res_ack.frame_type == FrameType.ACK
    assert res_ack.ack_number == 3

    res_fin_ack = decode_frame(fin_ack_frame.encode())
    assert isinstance(res_fin_ack, AckFrame)
    assert res_fin_ack.frame_type == FrameType.FIN_ACK
    assert res_fin_ack.ack_number == 4

