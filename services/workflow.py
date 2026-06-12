from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any, TypedDict

from agents.classification_agent import classify_document
from agents.confidence_agent import confidence_score
from agents.extraction_agent import extract_data
from agents.ocr_agent import extract_text
from agents.retrieval_agent import get_template
from agents.validation_agent import validate_json
from database.db import SessionLocal
from database.repository import save_processed_document
from schemas.documents import ProcessingResult

LOGGER = logging.getLogger(__name__)

try:
    from langgraph.graph import END, START, StateGraph
except Exception:  # pragma: no cover - fallback if the graph package API differs
    END = "END"
    START = "START"
    StateGraph = None


class WorkflowState(TypedDict, total=False):
    file_path: str
    filename: str
    original_filename: str
    document_type: str
    language: str
    json_output: dict[str, Any]
    raw_text: str
    raw_llm_response: str
    schema_template: str
    validation: dict[str, Any]
    confidence: float
    processing_time: float
    page_count: int
    status: str
    extraction_engine: str
    document_id: int
    started_at: float


class DocumentWorkflow:
    def __init__(self) -> None:
        self._graph = self._build_graph()

    def _build_graph(self):
        if StateGraph is None:
            return None
        try:
            graph = StateGraph(WorkflowState)
            graph.add_node("ocr", self._ocr_node)
            graph.add_node("classify", self._classify_node)
            graph.add_node("schema", self._schema_node)
            graph.add_node("extract", self._extract_node)
            graph.add_node("validate", self._validate_node)
            graph.add_node("score", self._score_node)
            graph.add_node("persist", self._persist_node)
            graph.add_edge(START, "ocr")
            graph.add_edge("ocr", "classify")
            graph.add_edge("classify", "schema")
            graph.add_edge("schema", "extract")
            graph.add_edge("extract", "validate")
            graph.add_edge("validate", "score")
            graph.add_edge("score", "persist")
            graph.add_edge("persist", END)
            return graph.compile()
        except Exception:
            LOGGER.warning("LangGraph unavailable, using sequential workflow")
            return None

    def process_file(self, file_path: str | Path, original_filename: str | None = None) -> ProcessingResult:
        original_filename = original_filename or Path(file_path).name
        LOGGER.info("Workflow started for %s", original_filename)
        state: WorkflowState = {
            "file_path": str(file_path),
            "filename": Path(file_path).name,
            "original_filename": original_filename,
            "started_at": time.perf_counter(),
        }
        if self._graph is not None:
            final_state = self._graph.invoke(state)
        else:
            final_state = self._run_sequential(state)
        elapsed = round(float(final_state.get("processing_time", 0.0)), 2)
        validation_payload = final_state.get("validation", {"valid": False, "issues": [], "score": 0.0, "required_fields": []})
        LOGGER.info(
            "Workflow completed for %s with status=%s confidence=%.2f engine=%s",
            original_filename,
            final_state.get("status"),
            float(final_state.get("confidence", 0.0)),
            final_state.get("extraction_engine", "hybrid"),
        )
        return ProcessingResult(
            document_id=final_state.get("document_id"),
            filename=final_state["filename"],
            document_type=final_state.get("document_type", "invoice"),
            language=final_state.get("language", "english"),
            status=final_state.get("status", "pending_review"),
            confidence=float(final_state.get("confidence", 0.0)),
            extraction_engine=final_state.get("extraction_engine", "hybrid"),
            validation=validation_payload if isinstance(validation_payload, dict) else validation_payload.model_dump(),
            json_output=final_state.get("json_output", {}),
            raw_text=final_state.get("raw_text", ""),
            raw_llm_response=final_state.get("raw_llm_response", ""),
            processing_time=elapsed,
            page_count=final_state.get("page_count", 1),
        )

    def _run_sequential(self, state: WorkflowState) -> WorkflowState:
        for handler in (
            self._ocr_node,
            self._classify_node,
            self._schema_node,
            self._extract_node,
            self._validate_node,
            self._score_node,
            self._persist_node,
        ):
            state = handler(state)
        return state

    def _ocr_node(self, state: WorkflowState) -> WorkflowState:
        LOGGER.info("OCR stage started for %s", state.get("original_filename", state["filename"]))
        ocr_text = extract_text(state["file_path"])
        state["raw_text"] = ocr_text
        LOGGER.info("OCR Completed")
        return state

    def _classify_node(self, state: WorkflowState) -> WorkflowState:
        LOGGER.info("Classification stage started for %s", state.get("original_filename", state["filename"]))
        sample_text = state.get("raw_text", "").strip() or f"{Path(state['file_path']).stem} {state['filename']}"
        document_type = classify_document(sample_text)
        state["document_type"] = document_type
        state["language"] = "english"
        LOGGER.info("Classification Completed")
        LOGGER.info("Classification stage completed with document_type=%s", document_type)
        return state

    def _schema_node(self, state: WorkflowState) -> WorkflowState:
        LOGGER.info("Schema selection started for %s", state.get("original_filename", state["filename"]))
        state["schema_template"] = get_template(state["document_type"])
        LOGGER.info("Schema Selected")
        return state

    def _extract_node(self, state: WorkflowState) -> WorkflowState:
        LOGGER.info("Extraction stage started for %s", state.get("original_filename", state["filename"]))
        raw_llm_response = extract_data(state.get("raw_text", ""), state.get("schema_template", "{}"))
        state["raw_llm_response"] = raw_llm_response
        state["json_output"] = self._parse_json_output(raw_llm_response)
        state["extraction_engine"] = "easyocr-groq-llama-3.3-70b"
        state["page_count"] = 1
        LOGGER.info("Extraction Completed")
        LOGGER.info("Extraction stage completed with engine=%s", state["extraction_engine"])
        return state

    def _validate_node(self, state: WorkflowState) -> WorkflowState:
        LOGGER.info("Validation stage started for %s", state.get("original_filename", state["filename"]))
        validation = validate_json(state.get("raw_llm_response", "{}"), state["document_type"])
        if validation.get("data") is not None:
            state["json_output"] = validation["data"]
        state["validation"] = {
            "valid": bool(validation.get("valid")),
            "issues": self._validation_issues(validation.get("issues", [])),
            "score": float(validation.get("score", 0.0)),
            "required_fields": [],
        }
        LOGGER.info("Validation Completed")
        LOGGER.info("Validation stage completed valid=%s score=%.2f", state["validation"]["valid"], state["validation"]["score"])
        return state

    def _score_node(self, state: WorkflowState) -> WorkflowState:
        LOGGER.info("Confidence scoring started for %s", state.get("original_filename", state["filename"]))
        confidence = confidence_score(state.get("validation", {}))
        state["confidence"] = confidence
        state["status"] = "Approved" if confidence >= 0.90 else "Needs Review"
        LOGGER.info("Confidence scoring completed confidence=%.2f status=%s", confidence, state["status"])
        return state

    def _persist_node(self, state: WorkflowState) -> WorkflowState:
        LOGGER.info("Database save started for %s", state.get("original_filename", state["filename"]))
        elapsed = round(time.perf_counter() - float(state.get("started_at", time.perf_counter())), 2)
        with SessionLocal() as session:
            document = save_processed_document(
                session,
                filename=state["filename"],
                original_filename=state["original_filename"],
                file_path=state["file_path"],
                document_type=state["document_type"],
                language=state.get("language", "english"),
                json_output=state.get("json_output", {}),
                confidence=state.get("confidence", 0.0),
                status=state.get("status", "pending_review"),
                processing_time=elapsed,
                page_count=state.get("page_count", 1),
                raw_text=state.get("raw_text", ""),
                engine=state.get("extraction_engine", "hybrid"),
            )
            state["document_id"] = document.id
        state["processing_time"] = elapsed
        LOGGER.info("Database Saved")
        LOGGER.info("Database save completed document_id=%s", state.get("document_id"))
        return state

    @staticmethod
    def _parse_json_output(raw_output: str) -> dict[str, Any]:
        cleaned = raw_output.strip().removeprefix("```json").removesuffix("```").strip()
        try:
            parsed = json.loads(cleaned)
            return parsed if isinstance(parsed, dict) else {}
        except Exception:
            return {}

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
