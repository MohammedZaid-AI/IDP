"""Vision-first extraction pipeline using Qwen2.5-VL via local Ollama.

Sends document images directly to a locally-running Qwen vision-language model
for simultaneous classification and structured data extraction.
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
    "1. Read the entire document directly from the image or PDF.\n"
    "2. Identify the document type.\n"
    "Possible types:\n"
    "- Invoice\n"
    "- Receipt\n"
    "- Bank Statement\n"
    "- Credit Note\n"
    "- Purchase Order\n"
    "- Tax Document\n"
    "- Financial Report\n"
    "- Other Financial Document\n\n"
    "3. Identify the following fields: document number, invoice date, vendor, customer, currency, subtotal, VAT amount, total amount.\n\n"
    "4. For financial amounts:\n"
    "   - prioritize values near: \"Gross Amount\", \"Total\", \"Invoice Total\", \"VAT Amount\", \"Subtotal\", \"Amt (SAR)\".\n"
    "   - ignore product codes and item numbers.\n"
    "   - Extract totals from invoice summary sections and table totals before returning null.\n\n"
    "5. Return null instead of guessing.\n\n"
    "6. Return JSON only.\n"
    "   - Do not output reasoning.\n"
    "   - Do not output thinking.\n"
    "   - Do not explain decisions.\n"
    "   - Do not output markdown.\n"
    "   - Do not output analysis.\n\n"
    "Strict JSON schema:\n"
    "{\n"
    '  "document_type": null,\n'
    '  "document_number": null,\n'
    '  "document_date": null,\n'
    '  "vendor_name": null,\n'
    '  "customer_name": null,\n'
    '  "currency": null,\n'
    '  "subtotal": null,\n'
    '  "tax_amount": null,\n'
    '  "total_amount": null\n'
    "}\n"
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
# Main extractor
# ---------------------------------------------------------------------------

class QwenVisionExtractor:
    """Extracts structured data directly from document images using Qwen2.5-VL via local Ollama."""

    def __init__(self) -> None:
        settings = get_settings()
        self.ollama_url: str = settings.ollama_url
        self.model: str = "qwen2.5vl:7b"  # Fixed model requirement
        self._model_verified = False

    def verify_model(self) -> bool:
        """Run startup verification."""
        from urllib import error, request as urllib_request
        import sys

        tags_url = f"{self.ollama_url.rstrip('/')}/api/tags"
        try:
            req = urllib_request.Request(tags_url, method="GET")
            with urllib_request.urlopen(req, timeout=5) as response:
                data = json.loads(response.read().decode("utf-8"))
        except Exception as exc:
            msg = "Qwen2.5-VL local model not running."
            print(msg, file=sys.stderr)
            LOGGER.error("Ollama is not reachable at %s — %s. %s", tags_url, exc, msg)
            return False

        models = data.get("models", [])
        available_names = [m.get("name", "") for m in models]
        for name in available_names:
            if self.model in name or name.startswith(self.model.split(":")[0]):
                LOGGER.info("✓ Ollama model '%s' verified (matched '%s')", self.model, name)
                self._model_verified = True
                return True

        msg = "Qwen2.5-VL local model not running."
        print(msg, file=sys.stderr)
        LOGGER.error("%s Model '%s' not found in Ollama. Available models: %s", msg, self.model, available_names)
        return False

    def extract(self, file_path: str | Path) -> ExtractionResult:
        """Run extraction on a single file and return the result."""
        file_path = Path(file_path)
        LOGGER.info("Qwen vision extraction started file=%s", file_path.name)

        if not self._model_verified:
            # Re-check in case Ollama came up
            self.verify_model()

        pages = _render_pages(file_path)
        page_count = len(pages)

        start = time.perf_counter()
        raw_response, parsed_json = self._call_ollama(pages)
        inference_time = time.perf_counter() - start

        LOGGER.info("Qwen vision inference time: %.2fs for %s", inference_time, file_path.name)

        if parsed_json is None:
            LOGGER.warning("Qwen returned no valid JSON for %s", file_path.name)
            parsed_json = {}

        # Determine document type
        doc_type_raw = parsed_json.pop("document_type", None) or "other_financial_document"
        doc_type = _normalise_doc_type(str(doc_type_raw))

        # Re-inject normalized document type
        parsed_json["document_type"] = doc_type

        # Basic confidence heuristic
        non_null_fields = sum(1 for v in parsed_json.values() if v is not None and v != "")
        if non_null_fields >= 3:
            confidence = 0.92
        elif non_null_fields >= 1:
            confidence = 0.78
        else:
            confidence = 0.55

        LOGGER.info(
            "Qwen vision extraction completed file=%s doc_type=%s fields=%d inference_time=%.2fs",
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

    def _call_ollama(self, pages: list[Image.Image]) -> tuple[str, dict[str, Any] | None]:
        """Send images to local Ollama's /api/chat endpoint."""
        from urllib import error, request as urllib_request

        image_b64_list = [_image_to_base64(img) for img in pages]

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
                "temperature": 0.0,
                "num_predict": 150,
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

qwen_extractor = QwenVisionExtractor()
