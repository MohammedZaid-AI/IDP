"""Document processing workflow — Qwen2.5-VL single-shot pipeline.

Flow:  Upload → Qwen Extract → Validate → Score → Persist
"""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any, TypedDict

from agents.confidence_agent import confidence_score
from agents.validation_agent import validate_json
from database.db import SessionLocal
from database.repository import save_processed_document
from schemas.documents import ProcessingResult
from services.qwen_local import QwenLocalExtractor, ProcessingTimings

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


class DocumentWorkflow:
    """Simplified 4-step workflow: extract → validate → score → persist."""

    def __init__(self) -> None:
        self._extractor = QwenLocalExtractor()

    def process_file(self, file_path: str | Path, original_filename: str | None = None) -> ProcessingResult:
        original_filename = original_filename or Path(file_path).name
        LOGGER.info("Workflow started for %s", original_filename)

        state: WorkflowState = {
            "file_path": str(file_path),
            "filename": Path(file_path).name,
            "original_filename": original_filename,
            "started_at": time.perf_counter(),
            "timings": {},
        }

        # Step 1: Qwen extraction (classification + extraction in one call)
        state = self._extract_node(state)

        # Step 2: Validation
        state = self._validate_node(state)

        # Step 3: Confidence scoring
        state = self._score_node(state)

        # Step 4: Persist to database
        state = self._persist_node(state)

        elapsed = round(float(state.get("processing_time", 0.0)), 2)
        validation_payload = state.get("validation", {"valid": False, "issues": [], "score": 0.0, "required_fields": []})

        # Update total time in timings
        timings = state.get("timings", {})
        timings["total_time"] = elapsed

        LOGGER.info("Total processing time: %.2fs", elapsed)
        LOGGER.info(
            "Workflow completed for %s | status=%s confidence=%.2f engine=%s total_time=%.2fs",
            original_filename,
            state.get("status"),
            float(state.get("confidence", 0.0)),
            state.get("extraction_engine", "qwen2.5-vl"),
            elapsed,
        )

        return ProcessingResult(
            document_id=state.get("document_id"),
            filename=state.get("original_filename", state["filename"]),
            document_type=state.get("document_type", "other_financial_document"),
            status=state.get("status", "pending_review"),
            confidence=float(state.get("confidence", 0.0)),
            extraction_engine=state.get("extraction_engine", "qwen2.5-vl"),
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

    def _extract_node(self, state: WorkflowState) -> WorkflowState:
        LOGGER.info("Qwen extraction stage started for %s", state.get("original_filename", state["filename"]))
        t0 = time.perf_counter()

        result = self._extractor.extract(state["file_path"])

        qwen_time = time.perf_counter() - t0
        state["timings"]["qwen_time"] = round(qwen_time, 3)

        state["document_type"] = result.document_type
        state["json_output"] = result.extracted_json
        state["raw_text"] = result.raw_response
        state["raw_llm_response"] = result.raw_response
        state["extraction_engine"] = "qwen2.5-vl"
        state["page_count"] = result.page_count

        LOGGER.info("Inference time: %.2fs", qwen_time)
        LOGGER.info(
            "Qwen extraction completed for %s | doc_type=%s qwen_time=%.2fs",
            state.get("original_filename", state["filename"]),
            result.document_type,
            qwen_time,
        )
        return state

    def _validate_node(self, state: WorkflowState) -> WorkflowState:
        LOGGER.info("Validation stage started for %s", state.get("original_filename", state["filename"]))
        t0 = time.perf_counter()

        validation = validate_json(state.get("json_output", {}), state["document_type"])

        validation_time = time.perf_counter() - t0
        state["timings"]["validation_time"] = round(validation_time, 3)

        if validation.get("data") is not None:
            state["json_output"] = validation["data"]

        state["validation"] = {
            "valid": bool(validation.get("valid")),
            "issues": self._validation_issues(validation.get("issues", [])),
            "score": float(validation.get("score", 0.0)),
            "required_fields": [],
        }

        LOGGER.info(
            "Validation completed for %s | valid=%s score=%.2f validation_time=%.3fs",
            state.get("original_filename", state["filename"]),
            state["validation"]["valid"],
            state["validation"]["score"],
            validation_time,
        )
        return state

    def _score_node(self, state: WorkflowState) -> WorkflowState:
        LOGGER.info("Confidence scoring started for %s", state.get("original_filename", state["filename"]))
        conf = confidence_score(state.get("validation", {}))
        state["confidence"] = conf
        state["status"] = "Approved" if conf >= 0.90 else "Needs Review"
        LOGGER.info("Confidence scoring completed | confidence=%.2f status=%s", conf, state["status"])
        return state

    def _persist_node(self, state: WorkflowState) -> WorkflowState:
        LOGGER.info("Database save started for %s", state.get("original_filename", state["filename"]))
        elapsed = round(time.perf_counter() - float(state.get("started_at", time.perf_counter())), 2)
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
                engine=state.get("extraction_engine", "qwen2.5-vl"),
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


workflow = DocumentWorkflow()
