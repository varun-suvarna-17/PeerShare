"""File handling package for PeerShare."""

from app.file.manager import (
    FileError,
    FileManager,
    FileTooLargeError,
    InsufficientDiskSpaceError,
    IntegrityVerificationError,
    InvalidFilenameError,
    calculate_sha256,
    calculate_sha256_bytes,
    sanitize_filename,
)
from app.file.models import DEFAULT_CHUNK_SIZE, MAX_FILE_SIZE, FileMetadata

__all__ = [
    "DEFAULT_CHUNK_SIZE",
    "MAX_FILE_SIZE",
    "FileMetadata",
    "FileManager",
    "FileError",
    "FileTooLargeError",
    "InvalidFilenameError",
    "InsufficientDiskSpaceError",
    "IntegrityVerificationError",
    "sanitize_filename",
    "calculate_sha256",
    "calculate_sha256_bytes",
]

