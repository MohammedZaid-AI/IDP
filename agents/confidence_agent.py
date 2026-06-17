from __future__ import annotations


def confidence_score(validation: dict) -> float:
    """Calculate confidence score using Python rule engine (legacy function for backward compatibility)."""
    if not validation.get("valid", False):
        base = validation.get("score", 0.5)
        return round(float(min(base, 0.6)), 2)
    score = float(validation.get("score", 0.85))
    issue_count = len(validation.get("issues", []))
    adjusted = max(0.0, min(1.0, score - (issue_count * 0.03)))
    return round(adjusted, 2)


def calculate_confidence_python_rule_engine(validation_result: dict, extracted_json: dict, document_type: str) -> float:
    """Calculate confidence using Python rules (new implementation)."""
    from services.validation import DocumentValidator

    validator = DocumentValidator()
    validation = validator.validate(document_type, extracted_json)

    if not validation.valid:
        base = validation.score
        return round(float(min(base, 0.6)), 2)

    score = float(validation.score)
    issue_count = len(validation.issues)
    adjusted = max(0.0, min(1.0, score - (issue_count * 0.03)))
    return round(adjusted, 2)
