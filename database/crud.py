from database.db import SessionLocal
from database.models import Document

def save_document(
        filename,
        document_type,
        language,
        confidence,
        extracted_data
):

    db = SessionLocal()

    doc = Document(
        filename=filename,
        document_type=document_type,
        language=language,
        confidence=confidence,
        extracted_data=extracted_data
    )

    db.add(doc)

    db.commit()

    db.close()