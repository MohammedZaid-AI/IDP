import sqlite3
import json

def main():
    conn = sqlite3.connect("database/idp.sqlite3")
    cursor = conn.cursor()
    
    # Check documents table count
    cursor.execute("SELECT COUNT(*) FROM documents")
    print(f"Total documents in database: {cursor.fetchone()[0]}")
    
    # Check documents status
    cursor.execute("SELECT status, COUNT(*) FROM documents GROUP BY status")
    print("Documents status counts:", cursor.fetchall())
    
    # Query documents and reviews
    cursor.execute("""
        SELECT d.id, d.filename, d.status, r.edited_json 
        FROM documents d
        LEFT JOIN reviews r ON d.id = r.document_id
    """)
    rows = cursor.fetchall()
    
    print("\nDocuments in DB:")
    for row in rows:
        doc_id, filename, status, edited_json = row
        print(f"ID: {doc_id} | Filename: {filename} | Status: {status} | Has Edited JSON: {bool(edited_json)}")
        if edited_json:
            try:
                ej = json.loads(edited_json)
                if ej:
                    print("  Edited JSON keys:", list(ej.keys()))
            except Exception as e:
                print("  Failed to parse edited_json:", e)
                
    conn.close()

if __name__ == "__main__":
    main()
