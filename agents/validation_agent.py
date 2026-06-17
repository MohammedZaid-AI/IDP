from __future__ import annotations

import json
from typing import Any

from services.validation import DocumentValidator


_validator = DocumentValidator()


def validate_json(data: str | dict[str, Any], document_type: str = "invoice") -> dict[str, Any]:
    try:
        payload = json.loads(data) if isinstance(data, str) else data
    except Exception as exc:
        return {"valid": False, "issues": [str(exc)], "data": None}
    result = _validator.validate(document_type, payload)
    return {
        "valid": result.valid,
        "issues": [f"{issue.field}: {issue.message}" for issue in result.issues],
        "data": payload,
        "score": result.score,
    }


def validate_json_with_qwen(data: str | dict[str, Any], document_type: str = "invoice") -> dict[str, Any]:
    """Validate extracted JSON using Qwen2.5:3B (legacy function for backward compatibility)."""
    return validate_json(data, document_type)
