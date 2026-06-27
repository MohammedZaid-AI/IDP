from __future__ import annotations

import json
import logging
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, TypedDict

from database.db import SessionLocal
from database.repository import save_processed_document
from schemas.documents import ProcessingResult
from services.merge_extractor import HybridInvoiceExtractionService

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

@contextmanager
def get_workflow_session():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()

class MultiModelDocumentWorkflow:
    """Orchestrates document processing using PaddleOCR, Qari OCR, and local Ollama."""

    def __init__(self) -> None:
        self._hybrid_invoice_extractor = HybridInvoiceExtractionService()

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

        # Run extraction pipeline
        state = self._process_node(state)

        # Save to database
        state = self._persist_node(state)

        elapsed = round(float(state.get("processing_time", 0.0)), 4)
        validation_payload = state.get("validation", {"valid": False, "issues": [], "score": 0.0, "required_fields": []})

        timings = state.get("timings", {})
        timings["total_time"] = elapsed

        # Print latency as requested by user
        print(f"OCR latency: {timings.get('ocr_time', 0.0):.4f}s", flush=True)
        print(f"Ollama latency: {timings.get('extraction_time', 0.0):.4f}s", flush=True)
        print(f"Merge latency: {timings.get('validation_time', 0.0):.4f}s", flush=True)
        print(f"Total latency: {elapsed:.4f}s", flush=True)

        # Print final JSON
        clean_json = {k: v for k, v in state.get("json_output", {}).items() if not k.startswith("_")}
        print("\nFinal JSON:", flush=True)
        print(json.dumps(clean_json, ensure_ascii=False, indent=2), flush=True)

        return ProcessingResult(
            document_id=state.get("document_id"),
            filename=state.get("original_filename", state["filename"]),
            document_type=state.get("document_type", "invoice"),
            status=state.get("status", "pending_review"),
            confidence=float(state.get("confidence", 0.0)),
            extraction_engine=state.get("extraction_engine", "ollama"),
            validation=validation_payload,
            json_output=state.get("json_output", {}),
            raw_text=state.get("raw_text", ""),
            raw_llm_response=state.get("raw_llm_response", ""),
            excel_file_path=state.get("excel_file_path", ""),
            processing_time=elapsed,
            page_count=state.get("page_count", 1),
            processing_timings=timings,
        )

    def _process_node(self, state: WorkflowState) -> WorkflowState:
        from services.settings import get_settings
        import os
        active_engine = os.environ.get("EXTRACTION_ENGINE", get_settings().extraction_engine)

        if active_engine == "qwen_llm":
            if not hasattr(self, "_qwen_llm_extractor"):
                from services.qwen_llm_extractor import QwenLlmExtractionService
                self._qwen_llm_extractor = QwenLlmExtractionService()
            self._qwen_llm_extractor.ensure_initialized()
            ext_result = self._qwen_llm_extractor.extract(state["file_path"])
            engine_name = "qwen_llm"
        else:
            self._hybrid_invoice_extractor.ensure_initialized()
            ext_result = self._hybrid_invoice_extractor.extract(state["file_path"])
            engine_name = "ollama"

        timings = {
            "ocr_time": ext_result.ocr_time,
            "classification_time": 0.0,
            "extraction_time": ext_result.llm_time,
            "validation_time": ext_result.validation_time,
            "confidence_time": 0.0,
            "total_time": ext_result.processing_time,
        }

        state["timings"].update(timings)
        state["document_type"] = ext_result.document_type
        state["json_output"] = ext_result.extracted_json
        state["raw_text"] = ext_result.ocr_text
        state["raw_llm_response"] = ext_result.raw_response
        state["extraction_engine"] = engine_name
        state["page_count"] = ext_result.page_count
        
        validation_payload = ext_result.extracted_json.get("_validation", {})
        state["validation"] = {
            "valid": bool(validation_payload.get("valid", False)),
            "issues": self._validation_issues(validation_payload.get("issues", [])),
            "score": ext_result.confidence,
            "required_fields": [],
        }
        state["confidence"] = ext_result.confidence
        return state

    def _persist_node(self, state: WorkflowState) -> WorkflowState:
        db_start = time.perf_counter()
        elapsed = round(time.perf_counter() - float(state.get("started_at", time.perf_counter())), 4)

        timings = state.get("timings", {})
        timings["total_time"] = elapsed

        with get_workflow_session() as session:
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
                engine=state.get("extraction_engine", "ollama"),
                processing_timings=timings,
            )
            state["document_id"] = document.id
        
        db_time = time.perf_counter() - db_start
        state["timings"]["database_save_time"] = db_time
        state["processing_time"] = elapsed
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
        return normalized

workflow = MultiModelDocumentWorkflow()
