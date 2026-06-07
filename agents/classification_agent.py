from langchain_groq import ChatGroq
from dotenv import load_dotenv
load_dotenv()

llm = ChatGroq(
    model="llama-3.3-70b-versatile"
)

def classify_document(text):

    prompt = f"""
    Classify this document.

    Options:

    invoice
    receipt
    bank_statement
    financial_report

    Return only one value.

    Text:

    {text}
    """

    response = llm.invoke(prompt)

    return response.content.strip().lower()