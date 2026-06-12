from __future__ import annotations

from dataclasses import dataclass
import os
from functools import lru_cache
from pathlib import Path


@dataclass(frozen=True)
class AppSettings:
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./idp.db")
    uploads_dir: Path = Path(os.getenv("UPLOADS_DIR", "uploads"))
    exports_dir: Path = Path(os.getenv("EXPORTS_DIR", "exports"))
    secret_key: str = os.getenv("SECRET_KEY", "idp-secret-key")
    groq_api_key: str | None = os.getenv("GROQ_API_KEY")
    qwen_api_url: str | None = os.getenv("QWEN_API_URL")
    qwen_api_key: str | None = os.getenv("QWEN_API_KEY")
    qwen_model: str = os.getenv("QWEN_MODEL", "qwen2.5-vl")


@lru_cache(maxsize=1)
def get_settings() -> AppSettings:
    settings = AppSettings()
    settings.uploads_dir.mkdir(parents=True, exist_ok=True)
    settings.exports_dir.mkdir(parents=True, exist_ok=True)
    return settings
