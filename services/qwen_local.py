"""Qwen2.5-VL-7B extraction service via local Ollama.

Sends document images directly to a locally-running Qwen vision-language model
for simultaneous classification and structured data extraction. Zero outbound
API calls — everything runs through Ollama at http://localhost:11434.
"""

from __future__ import annotations

import base64
import json
import logging
import re
import time
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Any

import fitz  # PyMuPDF
from PIL import Image

from services.settings import get_settings

LOGGER = logging.getLogger(__name__)

# Maximum number of pages to send in a single request
MAX_PAGES = 10

EXTRACTION_PROMPT = (
    "You are an expert Intelligent Document Processing system.\n\n"
    "Analyze the document directly from the image or PDF.\n\n"
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
    "Do not use markdown.\n"
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
    """Result of a Qwen2.5-VL extraction call."""

    document_type: str
    extracted_json: dict[str, Any]
    raw_response: str
    confidence: float
    page_count: int
    processing_time: float = 0.0


@dataclass
class ProcessingTimings:
    """Tracks individual stage timings."""

    upload_time: float = 0.0
    qwen_time: float = 0.0
    validation_time: float = 0.0
    total_time: float = 0.0

    def to_dict(self) -> dict[str, float]:
        return {
            "upload_time": round(self.upload_time, 3),
            "qwen_time": round(self.qwen_time, 3),
            "validation_time": round(self.validation_time, 3),
            "total_time": round(self.total_time, 3),
        }


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


def _image_to_base64(image: Image.Image, max_size: int = 1568) -> str:
    """Encode a PIL image to a base64 string, resizing if needed."""
    width, height = image.size
    if max(width, height) > max_size:
        scale = max_size / max(width, height)
        image = image.resize((int(width * scale), int(height * scale)), Image.LANCZOS)
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode("ascii")


# ---------------------------------------------------------------------------
# JSON parsing
# ---------------------------------------------------------------------------

def _parse_json_response(text: str) -> dict[str, Any] | None:
    """Best-effort extraction of a JSON dict from raw model output."""
    # Strip markdown fences if the model ignored our instructions
    cleaned = re.sub(r"```(?:json)?", "", text).replace("```", "").strip()
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
    """Check that Ollama is running and the required model is available.

    Returns True if the model is found, False otherwise.
    Logs a clear error message when the model is unavailable.
    """
    from urllib import error, request as urllib_request
    import sys

    tags_url = f"{ollama_url.rstrip('/')}/api/tags"
    try:
        req = urllib_request.Request(tags_url, method="GET")
        with urllib_request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode("utf-8"))
    except Exception as exc:
        msg = "Qwen2.5-VL local model not running."
        print(msg, file=sys.stderr)
        LOGGER.error(
            "Ollama is not reachable at %s — %s. %s",
            tags_url, exc, msg,
        )
        return False

    models = data.get("models", [])
    available_names = [m.get("name", "") for m in models]
    # Ollama model names can be "qwen2.5vl:3b" or "qwen2.5vl:3b-..." etc.
    for name in available_names:
        if model_name in name or name.startswith(model_name.split(":")[0]):
            LOGGER.info("✓ Ollama model '%s' verified (matched '%s')", model_name, name)
            return True

    msg = "Qwen2.5-VL local model not running."
    print(msg, file=sys.stderr)
    LOGGER.error(
        "%s Model '%s' not found in Ollama. Available models: %s",
        msg, model_name, available_names,
    )
    return False


# ---------------------------------------------------------------------------
# Main extractor — Local Ollama
# ---------------------------------------------------------------------------

class QwenLocalExtractor:
    """Extracts structured data from documents using Qwen2.5-VL via local Ollama.

    Zero outbound APIqwen2.5vl:3b calls. The entire extraction pipeline runs locally.
    """

    def __init__(self) -> None:
        settings = get_settings()
        self.ollama_url: str = settings.ollama_url
        self.model: str = settings.qwen_model
        self._model_verified = False

    def verify_model(self) -> bool:
        """Run startup verification. Called once during app init."""
        self._model_verified = verify_ollama_model(self.ollama_url, self.model)
        return self._model_verified

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def extract(self, file_path: str | Path) -> ExtractionResult:
        """Run extraction on a single file and return the result."""
        file_path = Path(file_path)
        LOGGER.info("Qwen local extraction started file=%s", file_path.name)

        if not self._model_verified:
            # Re-check in case Ollama came up after initial startup
            self._model_verified = verify_ollama_model(self.ollama_url, self.model)

        pages = _render_pages(file_path)
        page_count = len(pages)

        start = time.perf_counter()
        raw_response, parsed_json = self._call_ollama(pages)
        inference_time = time.perf_counter() - start

        LOGGER.info("Inference time: %.2fs", inference_time)
        LOGGER.info("Qwen inference time: %.2fs for %s", inference_time, file_path.name)

        if parsed_json is None:
            LOGGER.warning("Qwen returned no valid JSON for %s", file_path.name)
            parsed_json = {}

        # Determine document type from the model's response
        doc_type_raw = parsed_json.pop("document_type", None) or "other_financial_document"
        doc_type = _normalise_doc_type(str(doc_type_raw))

        # Confidence heuristic based on field completeness
        non_null_fields = sum(1 for v in parsed_json.values() if v is not None and v != "")
        if non_null_fields >= 3:
            confidence = 0.92
        elif non_null_fields >= 1:
            confidence = 0.78
        else:
            confidence = 0.55

        LOGGER.info(
            "Qwen local extraction completed file=%s doc_type=%s fields=%d inference_time=%.2fs",
            file_path.name, doc_type, non_null_fields, inference_time,
        )

        return ExtractionResult(
            document_type=doc_type,
            extracted_json=parsed_json,
            raw_response=raw_response,
            confidence=confidence,
            page_count=page_count,
            processing_time=inference_time,
        )

    # ------------------------------------------------------------------
    # Ollama API call (local, no outbound network)
    # ------------------------------------------------------------------

    def _call_ollama(self, pages: list[Image.Image]) -> tuple[str, dict[str, Any] | None]:
        """Send images to local Ollama's /api/chat endpoint and return (raw, parsed)."""
        from urllib import error, request as urllib_request

        # Encode all page images as base64
        image_b64_list = [_image_to_base64(img) for img in pages]

        # Build the Ollama chat API payload
        # Ollama's /api/chat accepts "images" as a list of base64 strings in each message
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": EXTRACTION_PROMPT,
                    "images": image_b64_list,
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
            # Local inference can take a while on large documents
            with urllib_request.urlopen(req, timeout=300) as response:
                raw = response.read().decode("utf-8")
        except error.URLError as exc:
            LOGGER.error("Ollama request failed: %s", exc)
            return "", None

        # Parse the Ollama response structure
        try:
            api_response = json.loads(raw)
            message_content = api_response.get("message", {}).get("content", "")
        except (json.JSONDecodeError, KeyError) as exc:
            LOGGER.error("Failed to parse Ollama response: %s", exc)
            return raw, None

        parsed = _parse_json_response(message_content)
        return message_content, parsed
