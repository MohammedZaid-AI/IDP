from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from services.settings import get_settings


class FileService:
    def __init__(self) -> None:
        self.settings = get_settings()

    def save_upload(self, filename: str, content: bytes) -> Path:
        safe_name = Path(filename).name
        suffix = Path(safe_name).suffix
        target = self.settings.uploads_dir / f"{Path(safe_name).stem}_{uuid4().hex[:12]}{suffix}"
        target.write_bytes(content)
        return target
