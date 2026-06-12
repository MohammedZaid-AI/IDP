from __future__ import annotations

import json
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from database.db import SessionLocal
from database.models import AuditLog, Document, Extraction, Review, User


@contextmanager
def get_session() -> Session:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


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
                language="english",
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
            status="Approved",
                processing_time=2.8,
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
            session.add(
                User(
                    name="Admin",
                    email="admin@idp.local",
                    role="admin",
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
    language: str,
    json_output: dict[str, Any] | str,
    confidence: float,
    status: str,
    processing_time: float,
    page_count: int,
    raw_text: str,
    engine: str,
) -> Document:
    document = Document(
        filename=filename,
        original_filename=original_filename,
        file_path=file_path,
        document_type=document_type,
        language=language,
        json_output=_json_payload(json_output),
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
            raw_text=raw_text,
            json_output=document.json_output,
            confidence=confidence,
            engine=engine,
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
                    "engine": engine,
                }
            ),
        )
    )
    session.commit()
    session.refresh(document)
    return document


def add_review(
    session: Session,
    *,
    document_id: int,
    reviewer_name: str,
    action: str,
    notes: str = "",
    edited_json: dict[str, Any] | str | None = None,
) -> Review:
    review = Review(
        document_id=document_id,
        reviewer_name=reviewer_name,
        action=action,
        notes=notes,
        edited_json=_json_payload(edited_json or {}),
    )
    session.add(review)
    session.add(
        AuditLog(
            document_id=document_id,
            actor=reviewer_name,
            event_type=f"review_{action}",
            payload=_json_payload({"notes": notes}),
        )
    )
    document = session.get(Document, document_id)
    if document is not None:
        if action == "approve":
            document.status = "Approved"
        elif action == "reject":
            document.status = "Rejected"
        else:
            document.status = "Needs Review"
    session.commit()
    session.refresh(review)
    return review


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
    return session.get(Document, document_id)


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
    query = select(Document).options(selectinload(Document.extractions))
    if search:
        like = f"%{search}%"
        query = query.where(
            (Document.filename.ilike(like))
            | (Document.document_type.ilike(like))
            | (Document.language.ilike(like))
        )
    if document_type:
        query = query.where(Document.document_type == document_type)
    if status:
        status_aliases = {
            "approved": ["approved", "Approved"],
            "needs_review": ["pending_review", "in_review", "Needs Review"],
            "pending_review": ["pending_review", "in_review", "Needs Review"],
            "rejected": ["rejected", "Rejected"],
        }
        query = query.where(Document.status.in_(status_aliases.get(status.lower().replace(" ", "_"), [status])))
    sort_column = getattr(Document, sort, Document.created_at)
    query = query.order_by(sort_column.desc() if descending else sort_column.asc())
    total = session.scalar(select(func.count()).select_from(query.subquery())) or 0
    items = (
        session.execute(query.offset((page - 1) * page_size).limit(page_size))
        .scalars()
        .all()
    )
    return items, total


def list_pending_reviews(session: Session) -> list[Document]:
    query = select(Document).where(Document.status.in_(["pending_review", "in_review", "Needs Review"])).order_by(Document.created_at.desc())
    return session.execute(query).scalars().all()


def get_document_detail(session: Session, document_id: int) -> Document | None:
    query = (
        select(Document)
        .where(Document.id == document_id)
        .options(selectinload(Document.extractions), selectinload(Document.reviews), selectinload(Document.audit_logs))
    )
    return session.execute(query).scalar_one_or_none()


def dashboard_metrics(session: Session) -> dict[str, Any]:
    total_documents = session.scalar(select(func.count(Document.id))) or 0
    approved = session.scalar(select(func.count(Document.id)).where(Document.status.in_(["approved", "Approved"]))) or 0
    pending = session.scalar(select(func.count(Document.id)).where(Document.status.in_(["pending_review", "in_review", "Needs Review"]))) or 0
    rejected = session.scalar(select(func.count(Document.id)).where(Document.status.in_(["rejected", "Rejected"]))) or 0
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
