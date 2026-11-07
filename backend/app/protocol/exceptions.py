"""Custom exceptions for PeerShare network protocol handling."""


class ProtocolError(Exception):
    """Base exception for all protocol errors."""
    pass


class FrameEncodeError(ProtocolError):
    """Raised when encoding a frame fails."""
    pass


class PayloadTooLargeError(FrameEncodeError):
    """Raised when payload exceeds maximum allowed size."""
    pass


class SequenceNumberOutOfRangeError(FrameEncodeError):
    """Raised when sequence number is outside allowed range."""
    pass


class FrameIndexOutOfRangeError(FrameEncodeError):
    """Raised when frame index is outside allowed range."""
    pass


class FrameDecodeError(ProtocolError):
    """Base exception for decoding failures."""
    pass


class FrameTooShortError(FrameDecodeError):
    """Raised when raw frame data is shorter than expected header size."""
    pass


class InvalidMagicError(FrameDecodeError):
    """Raised when magic header bytes do not match b'PS'."""
    pass


class UnsupportedVersionError(FrameDecodeError):
    """Raised when frame protocol version is not supported."""
    pass


class InvalidFrameTypeError(FrameDecodeError):
    """Raised when frame type is invalid or unexpected."""
    pass


class InvalidPayloadLengthError(FrameDecodeError):
    """Raised when payload length field does not match the received payload length."""
    pass


class InvalidAckTypeError(FrameDecodeError):
    """Raised when ACK type field is invalid."""
    pass


class CorruptedFrameError(FrameDecodeError):
    """Raised when frame CRC32 validation fails."""
    def __init__(self, expected: int, actual: int, message: str = ""):
        self.expected = expected
        self.actual = actual
        super().__init__(
            message or f"Frame CRC32 checksum mismatch: expected {expected:#010x}, got {actual:#010x}"
        )

