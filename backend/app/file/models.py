"""File metadata and validation data models."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
import math
import os
from typing import Optional
import uuid

DEFAULT_CHUNK_SIZE: int = 1024
MAX_FILE_SIZE: int = 5 * 1024 * 1024  # 5 MB


@dataclass
class FileMetadata:
    """Represents a file selected for transfer or reconstructed upon receipt."""
    file_id: uuid.UUID
    file_name: str
    file_path: str
    file_size: int
    file_type: str = "application/octet-stream"
    chunk_size: int = DEFAULT_CHUNK_SIZE
    total_frames: int = 0
    sha256_hash: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self) -> None:
        if self.file_size == 0:
            self.total_frames = 0
        else:
            self.total_frames = math.ceil(self.file_size / self.chunk_size)

