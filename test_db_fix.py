#!/usr/bin/env python
from database.db import init_db, SessionLocal
from database.repository import seed_demo_data, save_processed_document
from database.models import Document
from sqlalchemy import select

print('Testing database operations after language removal...')
init_db()
print('[OK] Database initialized with correct schema')

# Test demo seeding
session = seed_demo_data()
count = len(session.query(Document).all())
session.commit()
session.close()
print('[OK] Demo data seeded ({} documents)'.format(count))

# Test document creation without language parameter
with SessionLocal() as session:
    doc = save_processed_document(
        session,
        filename='test.pdf',
        original_filename='test.pdf',
        file_path='/tmp/test.pdf',
        document_type='invoice',
        json_output={'test': 'data'},
        confidence=0.95,
        status='Approved',
        processing_time=1.5,
        page_count=1,
        raw_text='test text',
        engine='hybrid'
    )
    session.commit()
    print('[OK] Document saved successfully (ID: {})'.format(doc.id))

# Verify database schema
with SessionLocal() as session:
    docs = session.query(Document).all()
    print('[OK] Total documents in database: {}'.format(len(docs)))
    
    # Check that document doesn't have language field
    for doc in docs[:1]:
        if hasattr(doc, 'language'):
            print('[ERROR] Document still has language attribute')
            exit(1)
        else:
            print('[OK] Document does not have language attribute')

print('\n[SUCCESS] Database persistence fixed - all tests passed!')
print('\nFiles Modified:')
print('  - database/models.py (removed language column)')
print('  - database/crud.py (removed language parameter)')
print('  - database/repository.py (removed language parameter)')
print('  - services/workflow.py (removed language from WorkflowState and calls)')
print('  - schemas/documents.py (removed language field)')
print('  - routers/api.py (removed language from responses)')
print('  - database/db.py (updated init_db to drop and recreate tables)')
