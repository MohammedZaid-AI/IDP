from __future__ import annotations

import os
from collections.abc import Generator
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import Session, declarative_base, sessionmaker


Base = declarative_base()


def get_database_url() -> str:
    return os.getenv("DATABASE_URL", "sqlite:///:memory:")


def build_engine(database_url: str | None = None) -> Engine:
    url = database_url or get_database_url()
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

    Base.metadata.create_all(bind=engine)
