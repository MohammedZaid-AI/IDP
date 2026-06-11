from dotenv import load_dotenv
import re

load_dotenv()

from langchain_groq import ChatGroq

llm = ChatGroq(
    model="llama-3.3-70b-versatile"
)

def extract_data(text, template):

    prompt = f"""
You are an invoice extraction system.

Extract the following fields.

Return ONLY valid JSON.

{{
  "invoice_number": null,
  "invoice_date": null,
  "vendor_name": null,
  "customer_name": null,
  "customer_number": null,
  "purchase_order_number": null,
  "vat_registration_number": null,
  "currency": null,
  "subtotal": null,
  "tax_amount": null,
  "total_amount": null
}}

OCR TEXT:

{text}
"""

    response = llm.invoke(prompt)

    result = response.content.strip()

    result = re.sub(r"```json", "", result)
    result = re.sub(r"```", "", result)

    return result.strip()