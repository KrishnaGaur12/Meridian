"""
Storage abstraction for Razorpay AI Risk Manager evidence documents.
Provides clean interface allowing local filesystem storage or future S3/cloud backends.
"""

import os
import shutil
import uuid
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime, timezone

from config.settings import BASE_DIR

UPLOAD_DIR = BASE_DIR / "data" / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


class StorageService(ABC):
    """Abstract interface for evidence document storage."""

    @abstractmethod
    def save_file(self, file_bytes: bytes, original_filename: str, content_type: Optional[str] = None) -> Dict[str, Any]:
        pass

    @abstractmethod
    def get_file(self, file_path: str) -> Optional[bytes]:
        pass

    @abstractmethod
    def delete_file(self, file_path: str) -> bool:
        pass

    @abstractmethod
    def file_exists(self, file_path: str) -> bool:
        pass


class LocalStorageService(StorageService):
    """Local filesystem implementation of StorageService."""

    def __init__(self, base_dir: Path = UPLOAD_DIR):
        self.base_dir = base_dir
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def save_file(self, file_bytes: bytes, original_filename: str, content_type: Optional[str] = None) -> Dict[str, Any]:
        ext = Path(original_filename).suffix.lower()
        unique_name = f"{uuid.uuid4().hex[:12]}_{Path(original_filename).stem}{ext}"
        target_path = self.base_dir / unique_name

        with open(target_path, "wb") as f:
            f.write(file_bytes)

        return {
            "file_path": str(target_path.resolve()),
            "relative_path": f"data/uploads/{unique_name}",
            "filename": unique_name,
            "original_filename": original_filename,
            "file_size": len(file_bytes),
            "content_type": content_type or "application/octet-stream",
            "stored_at": datetime.now(timezone.utc).isoformat()
        }

    def get_file(self, file_path: str) -> Optional[bytes]:
        p = Path(file_path)
        if not p.is_absolute():
            p = self.base_dir / p
        if p.exists() and p.is_file():
            with open(p, "rb") as f:
                return f.read()
        return None

    def delete_file(self, file_path: str) -> bool:
        p = Path(file_path)
        if not p.is_absolute():
            p = self.base_dir / p
        if p.exists() and p.is_file():
            try:
                os.remove(p)
                return True
            except OSError:
                return False
        return False

    def file_exists(self, file_path: str) -> bool:
        p = Path(file_path)
        if not p.is_absolute():
            p = self.base_dir / p
        return p.exists() and p.is_file()


# Default singleton storage service instance
default_storage_service = LocalStorageService()
