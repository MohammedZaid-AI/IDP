from __future__ import annotations

import re

from dotenv import load_dotenv
from langchain_groq import ChatGroq


load_dotenv()

llm = ChatGroq(model="llama-3.3-70b-versatile")


def extract_data(text: str, template: str) -> str:
    prompt = f"""
You are an expert financial document extraction system.

Extract ALL available information from the document.

Return ONLY valid JSON.
Do not wrap in markdown.
Do not use ```json.
Do not explain.

If a field is missing, use null.

Use this JSON schema:

{template}

OCR TEXT:

{text}
"""

    response = llm.invoke(prompt)
    result = response.content.strip()
    result = re.sub(r"```json", "", result)
    result = re.sub(r"```", "", result)
    return result.strip()
