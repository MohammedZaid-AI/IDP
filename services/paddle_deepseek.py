"""PaddleOCR + DeepSeek-R1:8B extraction service via local Ollama.

Runs local OCR using PaddleOCR, then structures the extracted text into JSON
using a local DeepSeek-R1:8B reasoning model via Ollama.
"""

from __future__ import annotations

import json
import logging
import re
import time
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Any

import fitz  # PyMuPDF
import numpy as np
from PIL import Image

from services.settings import get_settings

LOGGER = logging.getLogger(__name__)

# Maximum number of pages to process
MAX_PAGES = 10

EXTRACTION_PROMPT = (
    "You are an expert Intelligent Document Processing system.\n\n"
    "Analyze the following OCR-extracted text from a document:\n\n"
    "--- START DOCUMENT TEXT ---\n"
    "{document_text}\n"
    "--- END DOCUMENT TEXT ---\n\n"
    "Identify the document type.\n\n"
    "Possible types:\n"
    "- Invoice\n"
    "- Receipt\n"
    "- Bank Statement\n"
    "- Credit Note\n"
    "- Purchase Order\n"
    "- Tax Document\n"
    "- Financial Report\n"
    "- Other Financial Document\n\n"
    "Extract all available information.\n\n"
    "Return ONLY valid JSON.\n"
    "Do not explain.\n"
    "Do not wrap with ```json.\n\n"
    "If a field is missing use null.\n\n"
    "Include:\n"
    "- document_type\n"
    "- document_number\n"
    "- document_date\n"
    "- vendor_name\n"
    "- customer_name\n"
    "- currency\n"
    "- subtotal\n"
    "- tax_amount\n"
    "- total_amount\n\n"
    "Add additional fields whenever available."
)


@dataclass
class ExtractionResult:
    """Result of a PaddleOCR + DeepSeek-R1 extraction call."""

    document_type: str
    extracted_json: dict[str, Any]
    raw_response: str
    ocr_text: str
    confidence: float
    page_count: int
    ocr_time: float = 0.0
    llm_time: float = 0.0
    processing_time: float = 0.0


# ---------------------------------------------------------------------------
# Document type normalisation
# ---------------------------------------------------------------------------

_DOC_TYPE_MAP: dict[str, str] = {
    "invoice": "invoice",
    "receipt": "receipt",
    "bank statement": "bank_statement",
    "bank_statement": "bank_statement",
    "credit note": "credit_note",
    "credit_note": "credit_note",
    "purchase order": "purchase_order",
    "purchase_order": "purchase_order",
    "tax document": "tax_document",
    "tax_document": "tax_document",
    "financial report": "financial_report",
    "financial_report": "financial_report",
    "other financial document": "other_financial_document",
    "other_financial_document": "other_financial_document",
    "debit note": "debit_note",
    "debit_note": "debit_note",
}


def _normalise_doc_type(raw: str) -> str:
    """Map a free-form document_type string to a canonical slug."""
    key = raw.strip().lower()
    return _DOC_TYPE_MAP.get(key, "other_financial_document")


# ---------------------------------------------------------------------------
# Image helpers
# ---------------------------------------------------------------------------

def _render_pages(file_path: Path) -> list[Image.Image]:
    """Convert a file to a list of PIL images (one per page)."""
    ext = file_path.suffix.lower()
    if ext == ".pdf":
        doc = fitz.open(str(file_path))
        images: list[Image.Image] = []
        for page_index, page in enumerate(doc):
            if page_index >= MAX_PAGES:
                LOGGER.info("Capped at %d pages for %s", MAX_PAGES, file_path.name)
                break
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
            images.append(Image.open(BytesIO(pix.tobytes("png"))).convert("RGB"))
        return images
    # Single image file
    return [Image.open(file_path).convert("RGB")]


# ---------------------------------------------------------------------------
# JSON parsing
# ---------------------------------------------------------------------------

def _parse_json_response(text: str) -> dict[str, Any] | None:
    """Best-effort extraction of a JSON dict from raw model output, handling thought tags."""
    # Strip think tags first
    cleaned = text
    if "<think>" in cleaned:
        parts = cleaned.split("</think>", 1)
        if len(parts) > 1:
            cleaned = parts[1].strip()

    # Strip markdown fences if the model ignored our instructions
    cleaned = re.sub(r"```(?:json)?", "", cleaned).replace("```", "").strip()
    try:
        parsed = json.loads(cleaned)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass

    # Fallback: find the first {...} block
    match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
    if match:
        try:
            parsed = json.loads(match.group(0))
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass
    return None


# ---------------------------------------------------------------------------
# Ollama health check
# ---------------------------------------------------------------------------

def verify_ollama_model(ollama_url: str, model_name: str) -> bool:
    """Check that Ollama is running and the required model is available."""
    from urllib import error, request as urllib_request
    import sys

    tags_url = f"{ollama_url.rstrip('/')}/api/tags"
    try:
        req = urllib_request.Request(tags_url, method="GET")
        with urllib_request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode("utf-8"))
    except Exception as exc:
        msg = f"Ollama model '{model_name}' not running."
        print(msg, file=sys.stderr)
        LOGGER.error("Ollama is not reachable at %s — %s. %s", tags_url, exc, msg)
        return False

    models = data.get("models", [])
    available_names = [m.get("name", "") for m in models]
    for name in available_names:
        if model_name in name or name.startswith(model_name.split(":")[0]):
            LOGGER.info("✓ Ollama model '%s' verified (matched '%s')", model_name, name)
            return True

    msg = f"Ollama model '{model_name}' not running."
    print(msg, file=sys.stderr)
    LOGGER.error("%s Model '%s' not found in Ollama. Available models: %s", msg, model_name, available_names)
    return False


# ---------------------------------------------------------------------------
# Main extractor — PaddleOCR + local Ollama DeepSeek-R1
# ---------------------------------------------------------------------------

class PaddleDeepSeekExtractor:
    """Extracts structured data using local PaddleOCR and DeepSeek-R1:8B via Ollama."""

    def __init__(self) -> None:
        settings = get_settings()
        self.ollama_url: str = settings.ollama_url
        self.model: str = settings.ollama_model
        self._model_verified = False
        self._ocr_engine = None

    def _init_ocr(self) -> None:
        """Lazily initialize PaddleOCR engine to speed up startup checks."""
        if self._ocr_engine is None:
            # pyrefly: ignore [missing-import]
            from paddleocr import PaddleOCR
            LOGGER.info("Initializing PaddleOCR engine...")
            self._ocr_engine = PaddleOCR(
                ocr_version="PP-OCRv4",
                lang="en",
                use_doc_orientation_classify=False,
                use_doc_unwarping=False,
                use_textline_orientation=False,
                enable_mkldnn=False
            )
            LOGGER.info("PaddleOCR engine initialized successfully.")

    def verify_model(self) -> bool:
        """Run startup verification for Ollama model and lazily initialize OCR."""
        self._model_verified = verify_ollama_model(self.ollama_url, self.model)
        if self._model_verified:
            try:
                self._init_ocr()
            except Exception as exc:
                LOGGER.error("Failed to initialize PaddleOCR during verification: %s", exc)
                return False
        return self._model_verified
    
    def ensure_initialized(self) -> None:
        """Ensure OCR and model are initialized once at startup."""
        if not self._model_verified:
            self.verify_model()
        self._init_ocr()

    def extract(self, file_path: str | Path) -> ExtractionResult:
        """Run PaddleOCR followed by local DeepSeek-R1:8B extraction."""
        file_path = Path(file_path)
        LOGGER.info("PaddleOCR + DeepSeek local extraction started for file=%s", file_path.name)

        # OCR and model verification happens once at startup

        # Page rendering
        pages = _render_pages(file_path)
        page_count = len(pages)

        # Stage 1: PaddleOCR
        ocr_start = time.perf_counter()
        ocr_texts = []
        for i, page_img in enumerate(pages):
            LOGGER.info("Running PaddleOCR on page %d/%d for %s", i + 1, page_count, file_path.name)
            img_np = np.array(page_img)
            # Convert RGBA to RGB if necessary
            if img_np.ndim == 3 and img_np.shape[2] == 4:
                img_np = np.array(page_img.convert("RGB"))
            
            # PaddleOCR expects numpy array
            result = self._ocr_engine.ocr(img_np)
            LOGGER.info("Raw PaddleOCR output on page %d: %s", i + 1, result)
            
            page_text_lines = []
            if result and result[0]:
                rec_texts = result[0].get("rec_texts", [])
                if rec_texts:
                    page_text_lines = [str(t) for t in rec_texts if t is not None]
            ocr_texts.append("\n".join(page_text_lines))

        raw_ocr_text = "\n\n--- PAGE BREAK ---\n\n".join(ocr_texts)
        ocr_time = time.perf_counter() - ocr_start
        LOGGER.info("PaddleOCR extraction completed in %.2fs", ocr_time)
        LOGGER.info("OCR Text Length: %d", len(raw_ocr_text))
        LOGGER.info("First 500 characters of OCR text:\n%s", raw_ocr_text[:500])

        # Stage 2: DeepSeek-R1 structuring via local Ollama
        llm_start = time.perf_counter()
        formatted_prompt = EXTRACTION_PROMPT.format(document_text=raw_ocr_text)
        
        raw_response, parsed_json = self._call_ollama(formatted_prompt)
        llm_time = time.perf_counter() - llm_start
        LOGGER.info("DeepSeek-R1 LLM structuring completed in %.2fs", llm_time)

        if parsed_json is None:
            LOGGER.warning("DeepSeek-R1 returned no valid JSON for %s", file_path.name)
            parsed_json = {}

        # Normalise document type
        doc_type_raw = parsed_json.pop("document_type", None) or "other_financial_document"
        doc_type = _normalise_doc_type(str(doc_type_raw))

        # Fix document number extraction: prefer numeric identifier over label text
        if "document_number" in parsed_json and parsed_json["document_number"]:
            doc_num = str(parsed_json["document_number"]).strip()
            # Check if the document number looks like a numeric identifier (contains only digits/numbers)
            if re.fullmatch(r"\d+", doc_num):
                # If it looks like a numeric identifier, keep it as is
                pass
            else:
                # If it looks like label text (e.g., "CREDIT INVOICE"), try to extract numeric identifier
                # Look for numeric patterns in the OCR text
                numeric_match = re.search(r'\b(\d{5,})\b', raw_ocr_text)
                if numeric_match:
                    parsed_json["document_number"] = numeric_match.group(1)

        # Confidence heuristic based on field completeness
        non_null_fields = sum(1 for v in parsed_json.values() if v is not None and v != "")
        if non_null_fields >= 4:
            confidence = 0.95
        elif non_null_fields >= 2:
            confidence = 0.82
        else:
            confidence = 0.58

        total_time = ocr_time + llm_time
        LOGGER.info(
            "Extraction complete file=%s doc_type=%s fields=%d ocr_time=%.2fs llm_time=%.2fs total_time=%.2fs",
            file_path.name, doc_type, non_null_fields, ocr_time, llm_time, total_time
        )

        return ExtractionResult(
            document_type=doc_type,
            extracted_json=parsed_json,
            raw_response=raw_response,
            ocr_text=raw_ocr_text,
            confidence=confidence,
            page_count=page_count,
            ocr_time=ocr_time,
            llm_time=llm_time,
            processing_time=total_time,
        )

    def _call_ollama(self, prompt: str) -> tuple[str, dict[str, Any] | None]:
        """Send prompt to local Ollama /api/chat endpoint."""
        from urllib import error, request as urllib_request

        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            "stream": False,
            "format": "json",
            "options": {
                "temperature": 0.1,
                "num_predict": 4096,
            },
        }

        body = json.dumps(payload).encode("utf-8")
        chat_url = f"{self.ollama_url.rstrip('/')}/api/chat"

        req = urllib_request.Request(
            chat_url,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urllib_request.urlopen(req, timeout=300) as response:
                raw = response.read().decode("utf-8")
        except error.URLError as exc:
            LOGGER.error("Ollama request failed: %s", exc)
            return "", None

        try:
            api_response = json.loads(raw)
            message_content = api_response.get("message", {}).get("content", "")
        except (json.JSONDecodeError, KeyError) as exc:
            LOGGER.error("Failed to parse Ollama response: %s", exc)
            return raw, None

        parsed = _parse_json_response(message_content)
        return message_content, parsed
