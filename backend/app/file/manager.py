"""File manager for file selection, chunking, sanitization, reconstruction, and SHA-256 integrity verification."""

import hashlib
import mimetypes
import os
import re
import shutil
from typing import List, Optional, Tuple
import uuid

from app.file.models import DEFAULT_CHUNK_SIZE, MAX_FILE_SIZE, FileMetadata


class FileError(Exception):
    """Base exception for file management errors."""
    pass


class FileTooLargeError(FileError):
    """Raised when file size exceeds 5 MB cap."""
    pass


class InvalidFilenameError(FileError):
    """Raised when filename is unsafe or malicious."""
    pass


class InsufficientDiskSpaceError(FileError):
    """Raised when local filesystem does not have enough space."""
    pass


class IntegrityVerificationError(FileError):
    """Raised when SHA-256 hash comparison fails."""
    pass


def sanitize_filename(filename: str) -> str:
    """Sanitize filename to prevent directory traversal and remove unsafe characters.

    Args:
        filename: Raw incoming filename.

    Returns:
        Sanitized safe filename basename.

    Raises:
        InvalidFilenameError: If path contains explicit path traversal attempt.
    """
    if ".." in filename or "/" in filename or "\\" in filename:
        # Check explicit directory traversal
        base = os.path.basename(filename.replace("\\", "/"))
        if not base or base in (".", ".."):
            raise InvalidFilenameError(f"Malicious or invalid filename path: {filename}")
    else:
        base = filename

    # Remove non-printable / control characters
    cleaned = re.sub(r'[\\/*?:"<>|\x00-\x1f]', "", base).strip()
    if not cleaned or cleaned in (".", ".."):
        cleaned = "unnamed_file"

    return cleaned


def validate_filename(filename: str) -> None:
    """Validate filename and reject path traversal attempts.

    Args:
        filename: Raw filename to validate.

    Raises:
        InvalidFilenameError: If path contains directory traversal sequences.
    """
    if ".." in filename or filename.startswith("/") or filename.startswith("\\"):
        raise InvalidFilenameError(f"Path traversal sequence detected: {filename}")


def calculate_sha256(file_path: str) -> str:
    """Calculate SHA-256 hash of a file on disk."""
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def calculate_sha256_bytes(data: bytes) -> str:
    """Calculate SHA-256 hash of raw bytes."""
    return hashlib.sha256(data).hexdigest()


class FileManager:
    """Handles file registration, chunking, validation, and reconstruction."""

    def __init__(self, storage_dir: str = "/tmp/peershare_files") -> None:
        self.storage_dir = storage_dir
        os.makedirs(self.storage_dir, exist_ok=True)
        self.registered_files: dict[uuid.UUID, FileMetadata] = {}

    def register_file(
        self,
        file_path: str,
        custom_name: Optional[str] = None,
        chunk_size: int = DEFAULT_CHUNK_SIZE,
    ) -> FileMetadata:
        """Register a file for transfer, validating size cap and extracting metadata.

        Args:
            file_path: Absolute local path to file.
            custom_name: Optional custom filename.
            chunk_size: Chunk size in bytes (default 1024).

        Returns:
            FileMetadata instance.

        Raises:
            FileNotFoundError: If file does not exist.
            FileTooLargeError: If file exceeds 5 MB.
        """
        if not os.path.isfile(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        file_size = os.path.getsize(file_path)
        if file_size > MAX_FILE_SIZE:
            raise FileTooLargeError(
                f"File size {file_size} bytes exceeds maximum allowed limit {MAX_FILE_SIZE} bytes (5 MB)"
            )

        if custom_name is not None:
            validate_filename(custom_name)
        raw_name = custom_name or os.path.basename(file_path)
        safe_name = sanitize_filename(raw_name)

        sha256 = calculate_sha256(file_path)
        file_type, _ = mimetypes.guess_type(safe_name)
        file_id = uuid.uuid4()

        meta = FileMetadata(
            file_id=file_id,
            file_name=safe_name,
            file_path=os.path.abspath(file_path),
            file_size=file_size,
            file_type=file_type or "application/octet-stream",
            chunk_size=chunk_size,
            sha256_hash=sha256,
        )
        self.registered_files[file_id] = meta
        return meta

    def get_chunks(self, file_id: uuid.UUID) -> List[bytes]:
        """Read file and partition into chunks of chunk_size."""
        meta = self.registered_files.get(file_id)
        if meta is None:
            raise KeyError(f"Unregistered file ID: {file_id}")

        if meta.file_size == 0:
            return []

        chunks: List[bytes] = []
        with open(meta.file_path, "rb") as f:
            while chunk := f.read(meta.chunk_size):
                chunks.append(chunk)

        return chunks

    def save_reconstructed_file(
        self,
        file_name: str,
        data: bytes,
        expected_sha256: str,
        dest_dir: Optional[str] = None,
    ) -> Tuple[str, bool]:
        """Save reconstructed file to destination directory and verify SHA-256 hash.

        Args:
            file_name: Desired filename.
            data: Reconstructed bytes.
            expected_sha256: SHA-256 hash sent by sender in transfer request.
            dest_dir: Destination folder (defaults to storage_dir).

        Returns:
            Tuple of (saved_absolute_path, integrity_verified: bool)

        Raises:
            InvalidFilenameError: If filename contains directory traversal.
            InsufficientDiskSpaceError: If not enough free disk space.
            IntegrityVerificationError: If SHA-256 verification fails.
        """
        validate_filename(file_name)
        target_dir = dest_dir or self.storage_dir
        os.makedirs(target_dir, exist_ok=True)

        safe_name = sanitize_filename(file_name)

        # Check free disk space
        stat = shutil.disk_usage(target_dir)
        if stat.free < len(data) + 1024 * 1024:  # At least file size + 1MB buffer
            raise InsufficientDiskSpaceError(
                f"Insufficient disk space in {target_dir}: {stat.free} bytes available, need {len(data)} bytes"
            )

        # Collision avoidance: if file exists, append _1, _2, etc.
        base_path = os.path.join(target_dir, safe_name)
        final_path = base_path
        counter = 1
        name_part, ext_part = os.path.splitext(safe_name)
        while os.path.exists(final_path):
            final_path = os.path.join(target_dir, f"{name_part}_{counter}{ext_part}")
            counter += 1

        with open(final_path, "wb") as f:
            f.write(data)

        # Calculate actual hash
        actual_sha256 = calculate_sha256(final_path)
        is_verified = (actual_sha256.lower() == expected_sha256.lower())

        if not is_verified:
            # Clean up corrupted file
            try:
                os.remove(final_path)
            except OSError:
                pass
            raise IntegrityVerificationError(
                f"SHA-256 hash mismatch: expected {expected_sha256}, got {actual_sha256}"
            )

        return final_path, is_verified

