from dotenv import load_dotenv
load_dotenv()

from langchain_groq import ChatGroq

llm = ChatGroq(
    model="llama-3.3-70b-versatile"
)

def extract_data(
        text,
        template
):

    prompt = f"""
        You are an expert financial document extraction system.

        Extract ALL available information from the document.

        Return ONLY valid JSON.

        Do not wrap in markdown.
        Do not use ```json.
        Do not explain.

        If a field is missing, use null.

        OCR TEXT:

        {text}
            """

    response = llm.invoke(prompt)

    return response.content