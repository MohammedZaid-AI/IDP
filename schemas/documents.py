from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ExportFormat(str, Enum):
    excel = "xlsx"
    csv = "csv"
    json = "json"


class DocumentSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    filename: str
    document_type: str
    status: str
    confidence: float
    excel_file_path: str = ""
    created_at: datetime


class DocumentDetail(DocumentSummary):
    json_output: str
    ocr_text: str = ""
    raw_llm_response: str = ""
    extracted_json: str = "{}"
    validation_result: str = "{}"
    language: str = "unknown"
    processing_time: float = 0.0
    page_count: int = 1


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
    language: str
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


class DashboardMetrics(BaseModel):
    total_documents: int
    approved: int
    pending_review: int
    rejected: int
    average_confidence: float
    documents_today: int
    extraction_accuracy: float
    processing_time: float
    validation_failures: int
