from rag.vectorstore import get_db

def retrieve_template(
        doc_type
):

    db = get_db()

    docs = db.similarity_search(
        doc_type,
        k=1
    )

    return docs[0].page_content