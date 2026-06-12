from __future__ import annotations

from database.db import SessionLocal
from database.repository import save_processed_document


def save_document(filename, document_type, language, confidence, extracted_data):
    with SessionLocal() as session:
        save_processed_document(
            session,
            filename=filename,
            original_filename=filename,
            file_path="",
            document_type=document_type,
            language=language,
            json_output=extracted_data,
            confidence=confidence,
            status="pending_review",
            processing_time=0.0,
            page_count=1,
            raw_text="",
            engine="legacy",
        )
