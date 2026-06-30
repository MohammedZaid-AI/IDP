from __future__ import annotations

import json
import logging
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from database.crud import create_document, get_document as fetch_document, get_document as fetch_document_detail, search_documents
from database.db import SessionLocal
from database.models import AuditLog, Document, Extraction, Review, User


@contextmanager
def get_session() -> Session:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


LOGGER = logging.getLogger(__name__)


def _json_payload(value: Any) -> str:
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False, indent=2)


def seed_demo_data() -> Session:
    session = SessionLocal()
    try:
        if session.scalar(select(func.count(Document.id))) == 0:
            demo_document = Document(
                filename="sample-invoice.pdf",
                original_filename="sample-invoice.pdf",
                file_path="uploads/sample-invoice.pdf",
                document_type="invoice",
                json_output=_json_payload(
                    {
                        "invoice_number": "INV-1001",
                        "invoice_date": "2026-06-01",
                        "vendor_name": "Northwind Traders",
                        "customer_name": "Contoso Ltd",
                        "currency": "USD",
                        "subtotal": 1000.0,
                        "tax_amount": 180.0,
                        "total_amount": 1180.0,
                    }
                ),
                confidence=0.93,
            )
            session.add(demo_document)
            session.flush()
            session.add(
                Extraction(
                    document_id=demo_document.id,
                    raw_text="Invoice INV-1001 from Northwind Traders",
                    json_output=demo_document.json_output,
                    confidence=0.93,
                    engine="demo",
                )
            )
            session.add(
                Review(
                    document_id=demo_document.id,
                    reviewer_name="system",
                    action="approved",
                    notes="Seed record",
                )
            )
            session.add(
                AuditLog(
                    document_id=demo_document.id,
                    actor="system",
                    event_type="seeded",
                    payload=_json_payload({"message": "Seed document created"}),
                )
            )
        return session
    except Exception:
        session.rollback()
        session.close()
        raise


def save_processed_document(
    session: Session,
    *,
    filename: str,
    original_filename: str,
    file_path: str,
    document_type: str,
    json_output: dict[str, Any] | str,
    confidence: float,
    status: str,
    processing_time: float,
    page_count: int,
    raw_text: str,
    engine: str,
    raw_llm_response: str = "",
    validation_result: dict[str, Any] | str | None = None,
    excel_file_path: str = "",
    processing_timings: dict[str, float] | str = "{}",
    session_id: int | None = None,
) -> Document:
    return create_document(
        session,
        filename=filename,
        original_filename=original_filename,
        file_path=file_path,
        document_type=document_type,
        extracted_json=json_output,
        confidence=confidence,
        status=status,
        processing_time=processing_time,
        page_count=page_count,
        ocr_text=raw_text,
        raw_llm_response=raw_llm_response,
        validation_result=validation_result,
        excel_file_path=excel_file_path,
        extraction_engine=engine,
        processing_timings=processing_timings,
        session_id=session_id,
    )


def update_document_json(session: Session, document_id: int, json_output: dict[str, Any] | str) -> Document | None:
    document = session.get(Document, document_id)
    if document is None:
        return None
    document.json_output = _json_payload(json_output)
    session.add(
        AuditLog(
            document_id=document_id,
            actor="system",
            event_type="json_updated",
            payload=document.json_output,
        )
    )
    session.commit()
    session.refresh(document)
    return document


def get_document(session: Session, document_id: int) -> Document | None:
    return fetch_document(session, document_id)


def list_documents(
    session: Session,
    *,
    search: str | None = None,
    document_type: str | None = None,
    status: str | None = None,
    sort: str = "created_at",
    descending: bool = True,
    page: int = 1,
    page_size: int = 12,
) -> tuple[list[Document], int]:
    return search_documents(
        session,
        search=search,
        document_type=document_type,
        status=status,
        sort=sort,
        descending=descending,
        page=page,
        page_size=page_size,
    )


def get_document_detail(session: Session, document_id: int) -> Document | None:
    return fetch_document_detail(session, document_id)


def dashboard_metrics(session: Session) -> dict[str, Any]:
    total_documents = session.scalar(select(func.count(Document.id))) or 0
    approved = session.scalar(select(func.count(Document.id)).where(Document.status.in_(["approved", "Approved"]))) or 0
    pending = session.scalar(select(func.count(Document.id)).where(Document.status.in_(["pending_review", "in_review", "Needs Review"]))) or 0
    rejected = session.scalar(select(func.count(Document.id)).where(Document.status.in_(["rejected", "Rejected"]))) or 0
    exported = session.scalar(select(func.count(Document.id)).where(Document.excel_file_path != "")) or 0
    avg_confidence = session.scalar(select(func.avg(Document.confidence))) or 0.0
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    documents_today = session.scalar(select(func.count(Document.id)).where(Document.created_at >= today_start)) or 0
    avg_processing = session.scalar(select(func.avg(Document.processing_time))) or 0.0
    validation_failures = session.scalar(select(func.count(Document.id)).where(Document.confidence < 0.75)) or 0
    extraction_accuracy = round((approved / total_documents) * 100, 2) if total_documents else 0.0
    return {
        "total_documents": total_documents,
        "approved": approved,
        "pending_review": pending,
        "rejected": rejected,
        "exported": exported,
        "average_confidence": round(float(avg_confidence), 2),
        "documents_today": documents_today,
        "extraction_accuracy": extraction_accuracy,
        "processing_time": round(float(avg_processing), 2),
        "validation_failures": validation_failures,
    }


def analytics_payload(session: Session) -> dict[str, Any]:
    by_type = session.execute(
        select(Document.document_type, func.count(Document.id)).group_by(Document.document_type)
    ).all()
    trend = session.execute(
        select(func.date(Document.created_at), func.count(Document.id)).group_by(func.date(Document.created_at)).order_by(func.date(Document.created_at))
    ).all()
    confidence_rows = session.execute(
        select(Document.confidence).order_by(Document.confidence.asc())
    ).scalars().all()
    user_activity = session.scalar(select(func.count(AuditLog.id))) or 0
    return {
        "documents_by_type": [{"label": label, "value": count} for label, count in by_type],
        "daily_processing_trend": [{"label": str(day), "value": count} for day, count in trend],
        "confidence_distribution": confidence_rows,
        "user_activity": user_activity,
    }


def document_history_records(session: Session) -> list[dict[str, Any]]:
    documents = session.execute(select(Document).order_by(Document.created_at.desc())).scalars().all()
    return [
        {
            "id": document.id,
            "filename": document.filename,
            "document_type": document.document_type,
            "status": document.status,
            "confidence": document.confidence,
            "created_at": document.created_at,
        }
        for document in documents
    ]
