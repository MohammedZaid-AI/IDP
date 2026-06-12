from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from schemas.documents import ValidationIssue, ValidationResult


REQUIRED_FIELDS = {
    "invoice": ["invoice_number", "invoice_date", "vendor_name", "total_amount"],
    "receipt": ["receipt_number", "merchant_name", "amount"],
    "bank_statement": ["account_number", "bank_name"],
    "financial_report": ["reporting_period", "currency"],
    "purchase_order": ["po_number", "vendor_name", "order_date"],
    "credit_note": ["credit_note_number", "vendor_name", "amount"],
    "debit_note": ["debit_note_number", "vendor_name", "amount"],
}


class DocumentValidator:
    def validate(self, document_type: str, payload: dict[str, Any]) -> ValidationResult:
        required_fields = REQUIRED_FIELDS.get(document_type, [])
        issues: list[ValidationIssue] = []
        missing_fields: list[str] = []

        print("VALIDATION INCOMING JSON")
        print(payload)

        for field_name in required_fields:
            value = payload.get(field_name)
            if value in (None, "", []):
                missing_fields.append(field_name)
                issues.append(ValidationIssue(field=field_name, message="Missing required field"))

        print("MISSING FIELDS")
        print(missing_fields)

        amount_fields = [key for key in payload if "amount" in key.lower()]
        for field_name in amount_fields:
            if payload.get(field_name) not in (None, ""):
                if not self._looks_like_amount(payload.get(field_name)):
                    issues.append(ValidationIssue(field=field_name, message="Invalid amount format"))

        date_fields = [key for key in payload if "date" in key.lower() or "period" in key.lower()]
        for field_name in date_fields:
            if payload.get(field_name) not in (None, ""):
                if "period" in field_name.lower() and re.fullmatch(r"\d{4}", str(payload.get(field_name)).strip()):
                    continue
                if not self._looks_like_date(str(payload.get(field_name))):
                    issues.append(ValidationIssue(field=field_name, message="Invalid date or period format"))

        valid = len(issues) == 0
        score = self._score(required_fields, payload, issues)
        return ValidationResult(valid=valid, issues=issues, score=score, required_fields=required_fields)

    def _score(self, required_fields: list[str], payload: dict[str, Any], issues: list[ValidationIssue]) -> float:
        if not required_fields:
            return 0.6
        filled = sum(1 for field_name in required_fields if payload.get(field_name) not in (None, "", []))
        completeness = filled / max(len(required_fields), 1)
        deduction = min(len(issues) * 0.08, 0.5)
        return round(max(0.0, min(1.0, completeness - deduction + 0.15)), 2)

    @staticmethod
    def _looks_like_amount(value: Any) -> bool:
        try:
            float(str(value).replace(",", "").strip())
            return True
        except Exception:
            return bool(re.search(r"\d", str(value)))

    @staticmethod
    def _looks_like_date(value: str) -> bool:
        patterns = [
            r"\d{4}-\d{2}-\d{2}",
            r"\d{2}/\d{2}/\d{4}",
            r"\d{2}-\d{2}-\d{4}",
            r"\d{2}\.\d{2}\.\d{4}",
            r"\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\s+\d{4}",
            r"\bQ[1-4]\s+\d{4}\b",
        ]
        if any(re.search(pattern, value) for pattern in patterns):
            return True
        try:
            datetime.fromisoformat(value)
            return True
        except Exception:
            return False
