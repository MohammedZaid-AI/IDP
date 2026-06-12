from __future__ import annotations

from agents.schemas import BANK_SCHEMA, INVOICE_SCHEMA, RECEIPT_SCHEMA


TEMPLATES = {
    "invoice": INVOICE_SCHEMA,
    "receipt": RECEIPT_SCHEMA,
    "bank_statement": BANK_SCHEMA,
    "financial_report": """
{
    "reporting_period": null,
    "entity_name": null,
    "currency": null,
    "revenue": null,
    "profit": null
}
""",
    "purchase_order": """
{
    "po_number": null,
    "vendor_name": null,
    "order_date": null,
    "total_amount": null
}
""",
    "credit_note": """
{
    "credit_note_number": null,
    "vendor_name": null,
    "date": null,
    "amount": null
}
""",
    "debit_note": """
{
    "debit_note_number": null,
    "vendor_name": null,
    "date": null,
    "amount": null
}
""",
}


def get_template(doc_type: str) -> str:
    return TEMPLATES.get(doc_type.lower().strip(), INVOICE_SCHEMA)
