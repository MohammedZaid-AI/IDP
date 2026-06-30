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
    ollama_url: str = os.getenv("OLLAMA_URL", "http://localhost:11434")
    ollama_model: str = os.getenv("OLLAMA_MODEL", "qwen2.5:0.5b")
    ollama_classification_model: str = os.getenv("OLLAMA_CLASSIFICATION_MODEL", "qwen2.5-cpu:0.5b")
    ollama_validation_model: str = os.getenv("OLLAMA_VALIDATION_MODEL", "qwen2.5vl-cpu:3b")
    ollama_field_extraction_model: str = os.getenv("OLLAMA_FIELD_EXTRACTION_MODEL", "gemma4:e4b")
    extraction_engine: str = os.getenv("EXTRACTION_ENGINE", "ocr")


@lru_cache(maxsize=1)
def get_settings() -> AppSettings:
    settings = AppSettings()
    settings.uploads_dir.mkdir(parents=True, exist_ok=True)
    settings.exports_dir.mkdir(parents=True, exist_ok=True)
    return settings
