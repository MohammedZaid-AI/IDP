from __future__ import annotations

import json
from datetime import date, datetime, time
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from database.models import AuditLog, Document, Extraction, ProcessingSession


def _json_payload(value: Any) -> str:
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False, indent=2)


def create_document(
    session: Session,
    *,
    filename: str,
    document_type: str,
    status: str,
    confidence: float,
    ocr_text: str,
    raw_llm_response: str,
    extracted_json: dict[str, Any] | str,
    excel_file_path: str = "",
    validation_result: dict[str, Any] | str | None = None,
    original_filename: str | None = None,
    file_path: str = "",
    processing_time: float = 0.0,
    page_count: int = 1,
    extraction_engine: str = "hybrid",
    session_id: int | None = None,
) -> Document:
    extracted_json_payload = _json_payload(extracted_json)
    validation_payload = _json_payload(validation_result or {})
    document = Document(
        session_id=session_id,
        filename=filename,
        original_filename=original_filename or filename,
        file_path=file_path,
        document_type=document_type,
        json_output=extracted_json_payload,
        ocr_text=ocr_text,
        raw_llm_response=raw_llm_response,
        extracted_json=extracted_json_payload,
        validation_result=validation_payload,
        excel_file_path=excel_file_path,
        confidence=confidence,
        status=status,
        processing_time=processing_time,
        page_count=page_count,
    )
    session.add(document)
    session.flush()
    session.add(
        Extraction(
            document_id=document.id,
            raw_text=ocr_text,
            json_output=extracted_json_payload,
            confidence=confidence,
            engine=extraction_engine,
        )
    )
    session.add(
        AuditLog(
            document_id=document.id,
            actor="system",
            event_type="processed",
            payload=_json_payload(
                {
                    "document_type": document_type,
                    "status": status,
                    "confidence": confidence,
                    "engine": extraction_engine,
                }
            ),
        )
    )
    session.commit()
    session.refresh(document)
    return document


def get_document(session: Session, document_id: int) -> Document | None:
    query = (
        select(Document)
        .where(Document.id == document_id)
        .options(selectinload(Document.extractions), selectinload(Document.reviews), selectinload(Document.audit_logs))
    )
    return session.execute(query).scalar_one_or_none()


def get_all_documents(
    session: Session,
    *,
    page: int = 1,
    page_size: int = 12,
    sort: str = "created_at",
    descending: bool = True,
) -> tuple[list[Document], int]:
    return search_documents(session, page=page, page_size=page_size, sort=sort, descending=descending)


def delete_document(session: Session, document_id: int) -> bool:
    document = session.get(Document, document_id)
    if document is None:
        return False
    session.delete(document)
    session.commit()
    return True


def search_documents(
    session: Session,
    *,
    search: str | None = None,
    document_type: str | None = None,
    status: str | None = None,
    date_from: str | date | None = None,
    date_to: str | date | None = None,
    sort: str = "created_at",
    descending: bool = True,
    page: int = 1,
    page_size: int = 12,
) -> tuple[list[Document], int]:
    query = select(Document).options(selectinload(Document.extractions))

    if search:
        like = f"%{search.strip()}%"
        query = query.where(
            or_(
                Document.filename.ilike(like),
                Document.original_filename.ilike(like),
                Document.extracted_json.ilike(like),
                Document.json_output.ilike(like),
            )
        )
    if document_type:
        query = query.where(Document.document_type == document_type)
    if status:
        query = query.where(Document.status == status)
    if date_from:
        query = query.where(Document.created_at >= _date_start(date_from))
    if date_to:
        query = query.where(Document.created_at <= _date_end(date_to))

    sort_column = getattr(Document, sort, Document.created_at)
    query = query.order_by(sort_column.desc() if descending else sort_column.asc())
    total = session.scalar(select(func.count()).select_from(query.subquery())) or 0
    items = session.execute(query.offset((page - 1) * page_size).limit(page_size)).scalars().all()
    return items, total


def update_document_excel_path(session: Session, document_id: int, excel_file_path: str) -> Document | None:
    document = session.get(Document, document_id)
    if document is None:
        return None
    document.excel_file_path = excel_file_path
    session.add(document)
    session.commit()
    session.refresh(document)
    return document


def _date_start(value: str | date) -> datetime:
    parsed = date.fromisoformat(value) if isinstance(value, str) else value
    return datetime.combine(parsed, time.min)


def _date_end(value: str | date) -> datetime:
    parsed = date.fromisoformat(value) if isinstance(value, str) else value
    return datetime.combine(parsed, time.max)


def create_processing_session(session: Session, name: str, excel_file_path: str = "") -> ProcessingSession:
    db_session = ProcessingSession(name=name, excel_file_path=excel_file_path)
    session.add(db_session)
    session.commit()
    session.refresh(db_session)
    return db_session


def get_processing_session(session: Session, session_id: int) -> ProcessingSession | None:
    query = (
        select(ProcessingSession)
        .where(ProcessingSession.id == session_id)
        .options(selectinload(ProcessingSession.documents))
    )
    return session.execute(query).scalar_one_or_none()


def list_processing_sessions(session: Session) -> list[ProcessingSession]:
    query = select(ProcessingSession).order_by(ProcessingSession.created_at.desc())
    return list(session.execute(query).scalars().all())


def delete_processing_session(session: Session, session_id: int) -> bool:
    db_session = session.get(ProcessingSession, session_id)
    if db_session is None:
        return False
    session.delete(db_session)
    session.commit()
    return True

