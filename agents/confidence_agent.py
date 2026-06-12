from __future__ import annotations


def confidence_score(validation: dict) -> float:
    if not validation.get("valid", False):
        base = validation.get("score", 0.5)
        return round(float(min(base, 0.6)), 2)
    score = float(validation.get("score", 0.85))
    issue_count = len(validation.get("issues", []))
    adjusted = max(0.0, min(1.0, score - (issue_count * 0.03)))
    return round(adjusted, 2)
