from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.db import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    google_id: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    profile_picture: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_login: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    @property
    def name(self) -> str:
        return self.full_name

    @name.setter
    def name(self, value: str) -> None:
        self.full_name = value


class ProcessingSession(Base):
    __tablename__ = "processing_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    excel_file_path: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)

    documents: Mapped[list["Document"]] = relationship("Document", back_populates="session", cascade="all, delete-orphan")


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    session_id: Mapped[int | None] = mapped_column(ForeignKey("processing_sessions.id", ondelete="CASCADE"), nullable=True, index=True)
    filename: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    file_path: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    document_type: Mapped[str] = mapped_column(String(100), nullable=False, default="unknown")
    json_output: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    ocr_text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    raw_llm_response: Mapped[str] = mapped_column(Text, nullable=False, default="")
    extracted_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    validation_result: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    excel_file_path: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending_review")
    processing_time: Mapped[float] = mapped_column(Float, default=0.0)
    page_count: Mapped[int] = mapped_column(Integer, default=1)
    extraction_engine: Mapped[str] = mapped_column(String(100), nullable=False, default="qwen2.5-vl")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    session: Mapped[ProcessingSession | None] = relationship("ProcessingSession", back_populates="documents")
    extractions: Mapped[list["Extraction"]] = relationship("Extraction", back_populates="document", cascade="all, delete-orphan")
    reviews: Mapped[list["Review"]] = relationship("Review", back_populates="document", cascade="all, delete-orphan")
    audit_logs: Mapped[list["AuditLog"]] = relationship("AuditLog", back_populates="document", cascade="all, delete-orphan")


class Extraction(Base):
    __tablename__ = "extractions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id"), nullable=False, index=True)
    raw_text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    json_output: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    engine: Mapped[str] = mapped_column(String(100), nullable=False, default="qwen2.5-vl")
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    document: Mapped["Document"] = relationship("Document", back_populates="extractions")


class Review(Base):
    __tablename__ = "reviews"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id"), nullable=False, index=True)
    reviewer_name: Mapped[str] = mapped_column(String(255), nullable=False, default="system")
    action: Mapped[str] = mapped_column(String(50), nullable=False, default="pending")
    notes: Mapped[str] = mapped_column(Text, nullable=False, default="")
    edited_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    document: Mapped["Document"] = relationship("Document", back_populates="reviews")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id"), nullable=False, index=True)
    actor: Mapped[str] = mapped_column(String(255), nullable=False, default="system")
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    payload: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    document: Mapped["Document"] = relationship("Document", back_populates="audit_logs")


class OAuthState(Base):
    """Server-side OAuth state storage.

    Stores the OAuth state token and associated data in the database
    instead of relying on session cookies, which can be lost during
    cross-origin redirects through Google's OAuth servers.
    """
    __tablename__ = "oauth_states"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    state: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    data: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

