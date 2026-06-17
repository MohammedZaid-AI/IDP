from __future__ import annotations

import os
from collections.abc import Generator
from pathlib import Path

from sqlalchemy import text
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import Session, declarative_base, sessionmaker


Base = declarative_base()


def get_database_url() -> str:
    default_db_path = Path(__file__).resolve().parent / "idp.sqlite3"
    return os.getenv("DATABASE_URL", f"sqlite:///{default_db_path.as_posix()}")


def build_engine(database_url: str | None = None) -> Engine:
    url = database_url or get_database_url()
    if url.startswith("sqlite:///") and url != "sqlite:///:memory:":
        Path(url.removeprefix("sqlite:///")).expanduser().parent.mkdir(parents=True, exist_ok=True)
    engine_kwargs = {"future": True}
    if url.startswith("sqlite"):
        engine_kwargs["connect_args"] = {"check_same_thread": False}
        engine_kwargs["poolclass"] = StaticPool
    return create_engine(url, **engine_kwargs)


engine = build_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, future=True)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    from database import models  # noqa: F401

    # Recreate missing tables to ensure schema matches models
    Base.metadata.create_all(bind=engine)
    _ensure_document_columns()


def _ensure_document_columns() -> None:
    if not engine.url.get_backend_name().startswith("sqlite"):
        return

    required_columns = {
        "ocr_text": "TEXT NOT NULL DEFAULT ''",
        "raw_llm_response": "TEXT NOT NULL DEFAULT ''",
        "extracted_json": "TEXT NOT NULL DEFAULT '{}'",
        "validation_result": "TEXT NOT NULL DEFAULT '{}'",
        "excel_file_path": "VARCHAR(500) NOT NULL DEFAULT ''",
        "extraction_engine": "VARCHAR(100) NOT NULL DEFAULT 'qwen2.5-vl'",
        "processing_timings": "TEXT NOT NULL DEFAULT '{}'",
    }
    with engine.begin() as connection:
        existing_columns = {
            row[1]
            for row in connection.exec_driver_sql("PRAGMA table_info(documents)").fetchall()
        }
        for column_name, column_definition in required_columns.items():
            if column_name not in existing_columns:
                connection.execute(text(f"ALTER TABLE documents ADD COLUMN {column_name} {column_definition}"))
        connection.execute(
            text("UPDATE documents SET extracted_json = json_output WHERE extracted_json = '{}' OR extracted_json = ''")
        )
