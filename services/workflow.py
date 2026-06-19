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


@contextmanager
def get_workflow_session():
    """Optimized database session manager for workflow processing."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


class MultiModelDocumentWorkflow:
    """Multi-model workflow: PaddleOCR → Classification → Extraction → Validation → Confidence → Persist."""

    def __init__(self) -> None:
        self._orchestrator = orchestrator
        from services.paddle_deepseek import PaddleDeepSeekExtractor
        from services.paddle_qwen import PaddleQwenExtractor
        self._paddle_deepseek_extractor = PaddleDeepSeekExtractor()
        self._paddle_qwen_extractor = PaddleQwenExtractor()

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

        # Step 2: Persist to database (using same session for efficiency)
        state = self._persist_node(state)

        elapsed = round(float(state.get("processing_time", 0.0)), 2)
        validation_payload = state.get("validation", {"valid": False, "issues": [], "score": 0.0, "required_fields": []})

        # Update total time in timings
        timings = state.get("timings", {})
        timings["total_time"] = elapsed

        # Log detailed timing breakdown
        LOGGER.info(
            "Processing timing breakdown for %s | OCR=%.2fs Classification=%.2fs Extraction=%.2fs Validation=%.2fs Database Save=%.4fs Total=%.2fs",
            original_filename,
            timings.get("ocr_time", 0.0),
            timings.get("classification_time", 0.0),
            timings.get("extraction_time", 0.0),
            timings.get("validation_time", 0.0),
            timings.get("database_save_time", 0.0),
            elapsed,
        )
        
        # Print timings to stdout
        print(f"Timing - OCR: {timings.get('ocr_time', 0.0):.4f}s")
        print(f"Timing - Classification: {timings.get('classification_time', 0.0):.4f}s")
        print(f"Timing - Extraction: {timings.get('extraction_time', 0.0):.4f}s")
        print(f"Timing - Validation: {timings.get('validation_time', 0.0):.4f}s")
        print(f"Timing - Database Save: {timings.get('database_save_time', 0.0):.4f}s")
        
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
        import os
        from services.settings import get_settings
        engine = os.environ.get("EXTRACTION_ENGINE", get_settings().extraction_engine)
        if engine == "qwen_vl":
            return self._process_qwen_vl(state)
        elif engine == "qwen_llm":
            return self._process_qwen_llm(state)
        elif engine == "deepseek_llm":
            return self._process_deepseek_llm(state)
        elif engine == "paddle_deepseek":
            return self._process_paddle_deepseek(state)
        elif engine == "paddle_qwen":
            return self._process_paddle_qwen(state)
        else:
            return self._process_ocr(state)

    def _process_paddle_deepseek(self, state: WorkflowState) -> WorkflowState:
        LOGGER.info("PaddleOCR + DeepSeek local extraction started for %s", state.get("original_filename", state["filename"]))
        
        self._paddle_deepseek_extractor.ensure_initialized()
        ext_result = self._paddle_deepseek_extractor.extract(state["file_path"])
        
        val_svc = self._orchestrator.validation_service
        conf_svc = self._orchestrator.confidence_service
        
        val_result = val_svc.validate_json(ext_result.extracted_json, ext_result.document_type)
        
        conf_result = conf_svc.calculate_confidence(
            {"issues": val_result.issues, "score": val_result.score},
            ext_result.extracted_json,
            ext_result.document_type
        )
        
        total_time = ext_result.processing_time + val_result.processing_time + conf_result.processing_time
        
        timings = {
            "ocr_time": ext_result.ocr_time,
            "classification_time": 0.0,
            "extraction_time": ext_result.llm_time,
            "validation_time": val_result.processing_time,
            "confidence_time": conf_result.processing_time,
            "total_time": total_time,
        }
        
        state["timings"].update(timings)
        state["document_type"] = ext_result.document_type
        state["json_output"] = ext_result.extracted_json
        state["raw_text"] = ext_result.ocr_text
        state["raw_llm_response"] = ext_result.raw_response
        state["extraction_engine"] = "paddle_deepseek"
        state["page_count"] = ext_result.page_count
        
        state["validation"] = {
            "valid": val_result.is_valid,
            "issues": self._validation_issues(val_result.issues),
            "score": val_result.score,
            "required_fields": val_result.required_fields_missing,
        }
        state["confidence"] = conf_result.confidence
        return state

    def _process_paddle_qwen(self, state: WorkflowState) -> WorkflowState:
        LOGGER.info("PaddleOCR + Qwen2.5:3b extraction stage started for %s", state.get("original_filename", state["filename"]))
        
        self._paddle_qwen_extractor.ensure_initialized()
        ext_result = self._paddle_qwen_extractor.extract(state["file_path"])
        
        val_svc = self._orchestrator.validation_service
        conf_svc = self._orchestrator.confidence_service
        
        val_result = val_svc.validate_json(ext_result.extracted_json, ext_result.document_type)
        
        conf_result = conf_svc.calculate_confidence(
            {"issues": val_result.issues, "score": val_result.score},
            ext_result.extracted_json,
            ext_result.document_type
        )
        
        total_time = ext_result.processing_time + val_result.processing_time + conf_result.processing_time
        
        timings = {
            "ocr_time": ext_result.ocr_time,
            "classification_time": 0.0,
            "extraction_time": ext_result.llm_time,
            "validation_time": val_result.processing_time,
            "confidence_time": conf_result.processing_time,
            "total_time": total_time,
        }
        
        state["timings"].update(timings)
        state["document_type"] = ext_result.document_type
        state["json_output"] = ext_result.extracted_json
        state["raw_text"] = ext_result.ocr_text
        state["raw_llm_response"] = ext_result.raw_response
        state["extraction_engine"] = "paddle_qwen"
        state["page_count"] = ext_result.page_count
        
        state["validation"] = {
            "valid": val_result.is_valid,
            "issues": self._validation_issues(val_result.issues),
            "score": val_result.score,
            "required_fields": val_result.required_fields_missing,
        }
        state["confidence"] = conf_result.confidence
        
        # Calculate validation corrections
        try:
            from services.paddle_qwen import _parse_json_response
            raw_qwen_json = _parse_json_response(ext_result.raw_response) or {}
        except Exception:
            raw_qwen_json = {}
            
        corrections = {}
        for key, val in ext_result.extracted_json.items():
            if key == "_confidences":
                continue
            raw_val = raw_qwen_json.get(key)
            if raw_val != val:
                corrections[key] = {"raw_model_value": raw_val, "final_cleaned_value": val}
                
        # Detailed Debug Logging:
        # - Raw OCR
        # - Raw Qwen JSON
        # - Validation corrections
        # - Final JSON
        LOGGER.info("OCR latency: %.4fs", ext_result.ocr_time)
        LOGGER.info("Qwen latency: %.4fs", ext_result.llm_time)
        LOGGER.info("Total latency: %.4fs", total_time)
        LOGGER.info("--- DEBUG LOGGING ---")
        LOGGER.info("Raw OCR text:\n%s", ext_result.ocr_text)
        LOGGER.info("Raw Qwen response:\n%s", ext_result.raw_response)
        LOGGER.info("Raw Qwen JSON:\n%s", json.dumps(raw_qwen_json, indent=2))
        LOGGER.info("Validation corrections:\n%s", json.dumps(corrections, indent=2))
        LOGGER.info("Final JSON:\n%s", json.dumps(state["json_output"], indent=2))
        LOGGER.info("---------------------")

        # Runtime Path Evidence Log & Print
        from datetime import datetime
        diagnostics_str = (
            f"\n==================================================\n"
            f"PADDLEOCR RUNTIME PATH EVIDENCE & METRICS\n"
            f"==================================================\n"
            f"1. PaddleOCR Object ID:          {ext_result.ocr_object_id}\n"
            f"2. Object Created Timestamp:     {datetime.fromtimestamp(ext_result.ocr_created_timestamp).isoformat() if ext_result.ocr_created_timestamp else 'N/A'}\n"
            f"3. OCR Inference Start:          {datetime.fromtimestamp(ext_result.ocr_inference_start).isoformat() if ext_result.ocr_inference_start else 'N/A'}\n"
            f"4. OCR Inference End:            {datetime.fromtimestamp(ext_result.ocr_inference_end).isoformat() if ext_result.ocr_inference_end else 'N/A'}\n"
            f"5. Warmup Run at Startup?        {ext_result.warmup_executed_at_startup}\n"
            f"6. Reused Across Requests?       {ext_result.ocr_reused}\n"
            f"7. Exact Latency Breakdown:\n"
            f"   - OCR Model Load Time:        {ext_result.ocr_model_load_time:.4f}s\n"
            f"   - OCR Pure Inference Time:    {ext_result.ocr_pure_inference_time:.4f}s\n"
            f"   - Qwen Latency:               {ext_result.llm_time:.4f}s\n"
            f"   - Validation Latency:         {val_result.processing_time:.4f}s\n"
            f"8. Image Resolution Details:\n"
            f"   - Original Resolution:        {ext_result.orig_resolution}\n"
            f"   - Resized Resolution:         {ext_result.resized_resolution}\n"
            f"=================================================="
        )
        print(diagnostics_str, flush=True)
        LOGGER.info(diagnostics_str)
        
        return state

    def _process_deepseek_llm(self, state: WorkflowState) -> WorkflowState:
        LOGGER.info("DeepSeek-LLM processing stage started for %s", state.get("original_filename", state["filename"]))
        from services.deepseek_vision_ocr import deepseek_ocr_service
        
        # Stage 1: DeepSeek-VL2 OCR
        ocr_result = deepseek_ocr_service.extract_text(state["file_path"])
        
        # Use orchestrator's services for the rest
        class_svc = self._orchestrator.classification_service
        ext_svc = self._orchestrator.extraction_service
        val_svc = self._orchestrator.validation_service
        conf_svc = self._orchestrator.confidence_service
        
        # Stage 2: Classification
        class_result = class_svc.classify(ocr_result.ocr_text)
        
        # Stage 3: Extraction
        ext_result = ext_svc.extract_fields(ocr_result.ocr_text, class_result.document_type)
        
        # Stage 4: Validation
        val_result = val_svc.validate_json(ext_result.extracted_json, class_result.document_type)
        
        # Stage 5: Confidence
        conf_result = conf_svc.calculate_confidence(
            {"issues": val_result.issues, "score": val_result.score},
            ext_result.extracted_json,
            class_result.document_type
        )
        
        total_time = ocr_result.ocr_time + class_result.processing_time + ext_result.processing_time + val_result.processing_time + conf_result.processing_time
        
        timings = {
            "ocr_time": ocr_result.ocr_time,
            "classification_time": class_result.processing_time,
            "extraction_time": ext_result.processing_time,
            "validation_time": val_result.processing_time,
            "confidence_time": conf_result.processing_time,
            "total_time": total_time,
            "deepseek_eval_count": getattr(ocr_result, "eval_count", 0),
            "deepseek_text_length": getattr(ocr_result, "text_length", 0),
        }
        
        state["timings"].update(timings)
        state["document_type"] = class_result.document_type
        state["json_output"] = ext_result.extracted_json
        state["raw_text"] = ocr_result.ocr_text
        state["raw_llm_response"] = ext_result.raw_response
        state["extraction_engine"] = "deepseek_llm"
        state["page_count"] = ocr_result.page_count
        
        # Stash custom metrics for benchmarking
        state["deepseek_eval_count"] = getattr(ocr_result, "eval_count", 0)
        state["deepseek_text_length"] = getattr(ocr_result, "text_length", 0)
        
        state["validation"] = {
            "valid": val_result.is_valid,
            "issues": self._validation_issues(val_result.issues),
            "score": val_result.score,
            "required_fields": val_result.required_fields_missing,
        }
        state["confidence"] = conf_result.confidence
        return state

    def _process_qwen_llm(self, state: WorkflowState) -> WorkflowState:
        LOGGER.info("Qwen-LLM processing stage started for %s", state.get("original_filename", state["filename"]))
        from services.qwen_vision_ocr import qwen_ocr_service
        import os
        
        enable_cropping = os.environ.get("ENABLE_CROPPING", "false").lower() == "true"
        
        # Stage 1: Qwen-VL OCR
        ocr_result = qwen_ocr_service.extract_text(state["file_path"], crop=enable_cropping)
        
        # Use orchestrator's services for the rest
        class_svc = self._orchestrator.classification_service
        ext_svc = self._orchestrator.extraction_service
        val_svc = self._orchestrator.validation_service
        conf_svc = self._orchestrator.confidence_service
        
        # Clean markdown wrappers if Qwen wrapped the JSON
        clean_ocr_text = ocr_result.ocr_text
        if clean_ocr_text.startswith("```json"):
            clean_ocr_text = clean_ocr_text[7:]
        if clean_ocr_text.startswith("```"):
            clean_ocr_text = clean_ocr_text[3:]
        if clean_ocr_text.endswith("```"):
            clean_ocr_text = clean_ocr_text[:-3]
        clean_ocr_text = clean_ocr_text.strip()
        
        # Stage 2: Classification
        class_result = class_svc.classify(clean_ocr_text)
        
        # Stage 3: Extraction
        ext_result = ext_svc.extract_fields(clean_ocr_text, class_result.document_type)
        
        # Stage 4: Validation
        val_result = val_svc.validate_json(ext_result.extracted_json, class_result.document_type)
        
        # Stage 5: Confidence
        conf_result = conf_svc.calculate_confidence(
            {"issues": val_result.issues, "score": val_result.score},
            ext_result.extracted_json,
            class_result.document_type
        )
        
        total_time = ocr_result.ocr_time + class_result.processing_time + ext_result.processing_time + val_result.processing_time + conf_result.processing_time
        
        timings = {
            "ocr_time": ocr_result.ocr_time,
            "classification_time": class_result.processing_time,
            "extraction_time": ext_result.processing_time,
            "validation_time": val_result.processing_time,
            "confidence_time": conf_result.processing_time,
            "total_time": total_time,
            "qwen_eval_count": getattr(ocr_result, "eval_count", 0),
            "qwen_prompt_eval_count": getattr(ocr_result, "prompt_eval_count", 0),
            "qwen_text_length": getattr(ocr_result, "text_length", 0),
            "qwen_load_duration": getattr(ocr_result, "load_duration", 0.0),
            "qwen_prompt_eval_duration": getattr(ocr_result, "prompt_eval_duration", 0.0),
            "qwen_eval_duration": getattr(ocr_result, "eval_duration", 0.0),
            "orig_resolution": getattr(ocr_result, "orig_resolution", ""),
            "resized_resolution": getattr(ocr_result, "resized_resolution", ""),
        }
        
        state["timings"].update(timings)
        state["document_type"] = class_result.document_type
        state["json_output"] = ext_result.extracted_json
        state["raw_text"] = ocr_result.ocr_text
        state["raw_llm_response"] = ext_result.raw_response
        state["extraction_engine"] = "qwen_llm"
        state["page_count"] = ocr_result.page_count
        
        # Stash qwen_vl custom metrics for benchmarking
        state["qwen_eval_count"] = getattr(ocr_result, "eval_count", 0)
        state["qwen_text_length"] = getattr(ocr_result, "text_length", 0)
        
        state["validation"] = {
            "valid": val_result.is_valid,
            "issues": self._validation_issues(val_result.issues),
            "score": val_result.score,
            "required_fields": val_result.required_fields_missing,
        }
        state["confidence"] = conf_result.confidence
        return state

    def _process_qwen_vl(self, state: WorkflowState) -> WorkflowState:
        LOGGER.info("Qwen-VL processing stage started for %s", state.get("original_filename", state["filename"]))
        from services.qwen_vision_extractor import qwen_extractor
        from services.multi_model import ValidationService, ConfidenceCalculationService
        
        ext_result = qwen_extractor.extract(state["file_path"])
        
        val_service = ValidationService()
        val_result = val_service.validate_json(ext_result.extracted_json, ext_result.document_type)
        
        conf_service = ConfidenceCalculationService()
        conf_result = conf_service.calculate_confidence(
            {"issues": val_result.issues, "score": val_result.score},
            ext_result.extracted_json,
            ext_result.document_type
        )
        
        total_time = ext_result.processing_time + val_result.processing_time + conf_result.processing_time
        
        timings = {
            "ocr_time": 0.0,
            "classification_time": 0.0,
            "extraction_time": ext_result.processing_time,
            "validation_time": val_result.processing_time,
            "confidence_time": conf_result.processing_time,
            "total_time": total_time,
        }
        
        state["timings"].update(timings)
        state["document_type"] = ext_result.document_type
        state["json_output"] = ext_result.extracted_json
        state["raw_text"] = ""
        state["raw_llm_response"] = ext_result.raw_response
        state["extraction_engine"] = "qwen_vl"
        state["page_count"] = ext_result.page_count
        
        state["validation"] = {
            "valid": val_result.is_valid,
            "issues": self._validation_issues(val_result.issues),
            "score": val_result.score,
            "required_fields": val_result.required_fields_missing,
        }
        state["confidence"] = conf_result.confidence
        return state

    def _process_ocr(self, state: WorkflowState) -> WorkflowState:
        LOGGER.info("Multi-model (OCR) processing stage started for %s", state.get("original_filename", state["filename"]))

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
        state["extraction_engine"] = "ocr"
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
        LOGGER.info("Database save started")
        LOGGER.info("Database save started for %s", state.get("original_filename", state["filename"]))
        db_start = time.perf_counter()
        elapsed = round(time.perf_counter() - float(state.get("started_at", time.perf_counter())), 2)

        # Populate total time in timings
        timings = state.get("timings", {})
        timings["total_time"] = elapsed

        # Use optimized session manager for database operations
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
                engine=state.get("extraction_engine", "multi-model"),
                processing_timings=timings,
            )
            state["document_id"] = document.id
        
        db_time = time.perf_counter() - db_start
        state["timings"]["database_save_time"] = db_time
        state["processing_time"] = elapsed
        LOGGER.info("Database saved | document_id=%s total_time=%.2fs db_save_time=%.4fs", state.get("document_id"), elapsed, db_time)
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
