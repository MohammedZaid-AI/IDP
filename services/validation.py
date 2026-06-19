from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from schemas.documents import ValidationIssue, ValidationResult


REQUIRED_FIELDS = {
    "invoice": ["document_number", "document_date", "vendor_name", "total_amount"],
    "receipt": ["document_number", "document_date", "total_amount"],
    "bank_statement": ["document_number", "document_date"],
    "financial_report": ["document_date"],
    "purchase_order": ["document_number", "vendor_name", "document_date"],
    "credit_note": ["document_number", "vendor_name", "total_amount"],
    "debit_note": ["document_number", "vendor_name", "total_amount"],
    "tax_document": ["document_number", "document_date", "total_amount"],
    "other_financial_document": [],
}


class DocumentValidator:
    def validate(self, document_type: str, payload: dict[str, Any]) -> ValidationResult:
        required_fields = REQUIRED_FIELDS.get(document_type, [])
        issues: list[ValidationIssue] = []
        missing_fields: list[str] = []

        for field_name in required_fields:
            value = payload.get(field_name)
            if value in (None, "", []):
                missing_fields.append(field_name)
                issues.append(ValidationIssue(field=field_name, message="Missing required field"))

        # Validate document_number field
        if "document_number" in payload and payload.get("document_number") not in (None, ""):
            if not self._is_valid_invoice_number(payload.get("document_number")):
                issues.append(ValidationIssue(field="document_number", message="Invalid document number format"))

        # Validate amount fields
        amount_fields = [key for key in payload if "amount" in key.lower() or key in ("subtotal",)]
        for field_name in amount_fields:
            if payload.get(field_name) not in (None, ""):
                if not self._looks_like_amount(payload.get(field_name)):
                    issues.append(ValidationIssue(field=field_name, message="Invalid amount format"))

        # Validate date fields
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
        val_str = str(value).strip()
        # Reject if there are alphabetic characters mixed in (unless it's just currency symbols which were supposed to be stripped)
        if re.search(r'[a-zA-Z]', val_str):
            return False
        # Must contain digits
        if not re.search(r'\d', val_str):
            return False
        try:
            # Check if it parses as float after removing commas
            float(val_str.replace(",", ""))
            return True
        except ValueError:
            return False

    @staticmethod
    def _is_valid_invoice_number(value: Any) -> bool:
        val_str = str(value).strip()
        if not val_str:
            return False
        # Accept alphanumeric, dashes, slashes, but must have at least one digit
        if not re.search(r'\d', val_str):
            return False
        if not re.fullmatch(r'[A-Za-z0-9\-\/\\]+', val_str):
            return False
        return True

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
