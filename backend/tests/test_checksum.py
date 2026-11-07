"""Unit tests for CRC32 checksum calculation and verification."""

import pytest
import zlib

from app.protocol.checksum import calculate_crc32, verify_crc32


def test_calculate_crc32_empty() -> None:
    """CRC32 of empty bytes should be 0."""
    assert calculate_crc32(b"") == 0
    assert verify_crc32(b"", 0) is True


def test_calculate_crc32_known_vectors() -> None:
    """Verify known test strings against standard zlib CRC32."""
    test_cases = [
        b"123456789",
        b"PeerShare",
        b"The quick brown fox jumps over the lazy dog",
        b"\x00" * 1024,
        bytes(range(256)),
    ]
    for data in test_cases:
        expected = zlib.crc32(data) & 0xFFFFFFFF
        actual = calculate_crc32(data)
        assert actual == expected
        assert verify_crc32(data, expected) is True


def test_verify_crc32_mismatch() -> None:
    """verify_crc32 should return False when expected does not match."""
    data = b"PeerShare Protocol Data"
    actual = calculate_crc32(data)
    assert verify_crc32(data, actual ^ 0x01) is False
    assert verify_crc32(data, 0) is False


def test_calculate_crc32_single_bit_flip_detection() -> None:
    """Flipping a single bit in the data must result in a different checksum."""
    data = bytearray(b"Reliable file transfer protocol frame payload")
    orig_crc = calculate_crc32(data)

    # Flip 1 bit at index 5
    data[5] ^= 0x01
    corrupted_crc = calculate_crc32(data)

    assert orig_crc != corrupted_crc
    assert verify_crc32(data, orig_crc) is False

