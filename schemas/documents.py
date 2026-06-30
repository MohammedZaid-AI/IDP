from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ValidationIssue(BaseModel):
    field: str
    message: str
    severity: str = "warning"


class ValidationResult(BaseModel):
    valid: bool
    issues: list[ValidationIssue] = Field(default_factory=list)
    score: float = 0.0
    required_fields: list[str] = Field(default_factory=list)


class ProcessingResult(BaseModel):
    document_id: int | None = None
    filename: str
    document_type: str
    status: str
    confidence: float
    extraction_engine: str
    validation: ValidationResult
    json_output: dict[str, Any]
    raw_text: str
    raw_llm_response: str = ""
    excel_file_path: str = ""
    processing_time: float
    page_count: int = 1
    processing_timings: dict[str, Any] = Field(default_factory=dict)
