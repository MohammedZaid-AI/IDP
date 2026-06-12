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
    created_at: datetime


class DocumentDetail(DocumentSummary):
    json_output: str
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
    processing_time: float
    page_count: int = 1


class ReviewDecision(BaseModel):
    action: str
    reviewer_name: str = "reviewer"
    notes: str = ""
    edited_json: dict[str, Any] | None = None


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


class AnalyticsPayload(BaseModel):
    documents_by_type: list[dict[str, Any]]
    daily_processing_trend: list[dict[str, Any]]
    confidence_distribution: list[float]
    user_activity: int
