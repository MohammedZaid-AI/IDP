import os

from langchain_core.documents import Document

from rag.vectorstore import get_db

def ingest_templates():

    docs = []

    for file in os.listdir("templates"):

        with open(
            f"templates/{file}",
            "r",
            encoding="utf-8"
        ) as f:

            docs.append(
                Document(
                    page_content=f.read()
                )
            )

    db = get_db()

    db.add_documents(docs)