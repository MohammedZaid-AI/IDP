"""Document processing workflow — Multi-model pipeline.

Flow: Upload → PaddleOCR → Classification → Extraction → Validation → Confidence → Persist
"""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any, TypedDict

from database.db import SessionLocal
from database.repository import save_processed_document
from schemas.documents import ProcessingResult
from services.multi_model import ProcessingResult as MultiModelProcessingResult, orchestrator

LOGGER = logging.getLogger(__name__)


class WorkflowState(TypedDict, total=False):
    file_path: str
    filename: str
    original_filename: str
    document_type: str
    json_output: dict[str, Any]
    raw_text: str
    raw_llm_response: str
    validation: dict[str, Any]
    confidence: float
    processing_time: float
    page_count: int
    status: str
    extraction_engine: str
    document_id: int
    started_at: float
    timings: dict[str, float]


class MultiModelDocumentWorkflow:
    """Multi-model workflow: PaddleOCR → Classification → Extraction → Validation → Confidence → Persist."""

    def __init__(self) -> None:
        self._orchestrator = orchestrator

    def process_file(self, file_path: str | Path, original_filename: str | None = None) -> ProcessingResult:
        original_filename = original_filename or Path(file_path).name
        LOGGER.info("Multi-model workflow started for %s", original_filename)

        state: WorkflowState = {
            "file_path": str(file_path),
            "filename": Path(file_path).name,
            "original_filename": original_filename,
            "started_at": time.perf_counter(),
            "timings": {},
        }

        # Step 1: Multi-model processing
        state = self._process_node(state)

        # Step 2: Persist to database
        state = self._persist_node(state)

        elapsed = round(float(state.get("processing_time", 0.0)), 2)
        validation_payload = state.get("validation", {"valid": False, "issues": [], "score": 0.0, "required_fields": []})

        # Update total time in timings
        timings = state.get("timings", {})
        timings["total_time"] = elapsed

        # Log detailed timing breakdown
        LOGGER.info(
            "Processing timing breakdown for %s | OCR=%.2fs Classification=%.2fs Extraction=%.2fs Validation=%.2fs Confidence=%.2fs Total=%.2fs",
            original_filename,
            timings.get("ocr_time", 0.0),
            timings.get("classification_time", 0.0),
            timings.get("extraction_time", 0.0),
            timings.get("validation_time", 0.0),
            timings.get("confidence_time", 0.0),
            elapsed,
        )
        
        # Log field extraction summary
        if state.get("json_output"):
            extracted_fields = state["json_output"]
            non_null_fields = sum(1 for v in extracted_fields.values() if v not in (None, "", []))
            LOGGER.info(
                "Field extraction summary for %s | document_type=%s fields_extracted=%d/%d confidence=%.2f",
                original_filename,
                state.get("document_type", "unknown"),
                non_null_fields,
                len(extracted_fields),
                float(state.get("confidence", 0.0)),
            )

        LOGGER.info("Total processing time: %.2fs", elapsed)
        LOGGER.info(
            "Multi-model workflow completed for %s | status=%s confidence=%.2f engine=%s total_time=%.2fs",
            original_filename,
            state.get("status"),
            float(state.get("confidence", 0.0)),
            state.get("extraction_engine", "multi-model"),
            elapsed,
        )

        return ProcessingResult(
            document_id=state.get("document_id"),
            filename=state.get("original_filename", state["filename"]),
            document_type=state.get("document_type", "other_financial_document"),
            status=state.get("status", "pending_review"),
            confidence=float(state.get("confidence", 0.0)),
            extraction_engine=state.get("extraction_engine", "multi-model"),
            validation=validation_payload if isinstance(validation_payload, dict) else validation_payload.model_dump(),
            json_output=state.get("json_output", {}),
            raw_text=state.get("raw_text", ""),
            raw_llm_response=state.get("raw_llm_response", ""),
            excel_file_path=state.get("excel_file_path", ""),
            processing_time=elapsed,
            page_count=state.get("page_count", 1),
            processing_timings=timings,
        )

    # ------------------------------------------------------------------
    # Pipeline nodes
    # ------------------------------------------------------------------

    def _process_node(self, state: WorkflowState) -> WorkflowState:
        LOGGER.info("Multi-model processing stage started for %s", state.get("original_filename", state["filename"]))

        result = self._orchestrator.process_file(state["file_path"])

        # Extract stage timings
        timings = {
            "ocr_time": result.ocr_result.ocr_time,
            "classification_time": result.classification_result.classification_time,
            "extraction_time": result.extraction_result.extraction_time,
            "validation_time": result.validation_result.validation_time,
            "confidence_time": result.confidence_result.confidence_time,
            "total_time": result.total_time,
        }

        state["timings"].update(timings)
        state["document_type"] = result.document_type
        state["json_output"] = result.extraction_result.extracted_json
        state["raw_text"] = result.raw_ocr_text
        state["raw_llm_response"] = result.extraction_result.raw_response
        state["extraction_engine"] = "multi-model"
        state["page_count"] = result.ocr_result.page_count
        # Map validation result to schema expectation
        val_res = result.validation_result
        state["validation"] = {
            "valid": val_res.is_valid,
            "issues": self._validation_issues(val_res.issues),
            "score": val_res.score,
            "required_fields": val_res.required_fields_missing,
        }
        state["confidence"] = result.confidence_result.confidence

        LOGGER.info(
            "Multi-model processing completed for %s | doc_type=%s total_time=%.2fs ocr=%.2fs classification=%.2fs extraction=%.2fs validation=%.2fs confidence=%.2fs",
            state.get("original_filename", state["filename"]),
            result.document_type,
            result.total_time,
            result.ocr_result.ocr_time,
            result.classification_result.classification_time,
            result.extraction_result.extraction_time,
            result.validation_result.validation_time,
            result.confidence_result.confidence_time,
        )
        return state

    def _persist_node(self, state: WorkflowState) -> WorkflowState:
        LOGGER.info("Database save started for %s", state.get("original_filename", state["filename"]))
        elapsed = round(time.perf_counter() - float(state.get("started_at", time.perf_counter())), 2)

        # Populate total time in timings
        timings = state.get("timings", {})
        timings["total_time"] = elapsed

        with SessionLocal() as session:
            document = save_processed_document(
                session,
                filename=state["original_filename"],
                original_filename=state["original_filename"],
                file_path=state["file_path"],
                document_type=state["document_type"],
                json_output=state.get("json_output", {}),
                confidence=state.get("confidence", 0.0),
                status=state.get("status", "pending_review"),
                processing_time=elapsed,
                page_count=state.get("page_count", 1),
                raw_text=state.get("raw_text", ""),
                raw_llm_response=state.get("raw_llm_response", ""),
                validation_result=state.get("validation", {}),
                engine=state.get("extraction_engine", "multi-model"),
                processing_timings=timings,
            )
            state["document_id"] = document.id
        state["processing_time"] = elapsed
        LOGGER.info("Database saved | document_id=%s total_time=%.2fs", state.get("document_id"), elapsed)
        return state

    @staticmethod
    def _validation_issues(issues: Any) -> list[dict[str, str]]:
        normalized: list[dict[str, str]] = []
        if not isinstance(issues, list):
            return normalized
        for issue in issues:
            if isinstance(issue, dict):
                normalized.append(
                    {
                        "field": str(issue.get("field", "document")),
                        "message": str(issue.get("message", issue)),
                        "severity": str(issue.get("severity", "warning")),
                    }
                )
                continue
            text = str(issue)
            if ":" in text:
                field, message = text.split(":", 1)
                normalized.append({"field": field.strip(), "message": message.strip(), "severity": "warning"})
            else:
                normalized.append({"field": "document", "message": text, "severity": "warning"})
        return normalized


workflow = MultiModelDocumentWorkflow()
