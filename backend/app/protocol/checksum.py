"""CRC32 checksum generation and verification for network frames."""

import zlib


def calculate_crc32(data: bytes) -> int:
    """Calculate the 32-bit CRC checksum for the given byte sequence.

    Args:
        data: The bytes to calculate the CRC32 checksum over.

    Returns:
        Unsigned 32-bit integer checksum.
    """
    return zlib.crc32(data) & 0xFFFFFFFF


def verify_crc32(data: bytes, expected_crc: int) -> bool:
    """Verify that the CRC32 checksum of data matches expected_crc.

    Args:
        data: The byte sequence to verify.
        expected_crc: The expected 32-bit CRC checksum.

    Returns:
        True if checksum matches, False otherwise.
    """
    return calculate_crc32(data) == (expected_crc & 0xFFFFFFFF)

