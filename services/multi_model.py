from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Any
import re
from datetime import datetime

import fitz  # PyMuPDF
import numpy as np
from PIL import Image

from services.settings import get_settings

LOGGER = logging.getLogger(__name__)

# Maximum number of pages to process
MAX_PAGES = 10


@dataclass
class OCRResult:
    """Result of PaddleOCR processing."""

    ocr_text: str
    page_count: int
    ocr_time: float
    processing_time: float


@dataclass
class ClassificationResult:
    """Result of document classification."""

    document_type: str
    classification_time: float
    processing_time: float


@dataclass
class ExtractionResult:
    """Result of field extraction."""

    extracted_json: dict[str, Any]
    raw_response: str
    extraction_time: float
    processing_time: float


@dataclass
class ValidationResult:
    """Result of JSON validation."""

    is_valid: bool
    issues: list[str]
    score: float
    required_fields_missing: list[str]
    validation_time: float
    processing_time: float


@dataclass
class ConfidenceResult:
    """Result of confidence calculation."""

    confidence: float
    confidence_time: float
    processing_time: float


@dataclass
class ProcessingResult:
    """Complete processing result."""

    ocr_result: OCRResult
    classification_result: ClassificationResult
    extraction_result: ExtractionResult
    validation_result: ValidationResult
    confidence_result: ConfidenceResult
    total_time: float
    raw_ocr_text: str
    document_type: str


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


def _clean_document_number(doc_number: str | None, ocr_text: str) -> str:
    doc_num_clean = str(doc_number or "").strip()
    
    # Check if doc_number is a label text (like "CREDIT INVOICE", "INVOICE", "CREDIT NOTE")
    # If it contains text but no digits, or matches known text labels, it's a label, not a number!
    has_digits = any(char.isdigit() for char in doc_num_clean)
    is_label = doc_num_clean.lower() in (
        "credit invoice", "invoice", "credit note", "receipt", 
        "debit note", "purchase order", "tax invoice", "statement", "credit_invoice", "creditnote"
    ) or (not has_digits and len(doc_num_clean) > 3)
    
    if not doc_num_clean or is_label:
        import re
        # Let's search for keywords first, including OCR typos
        keywords = [
            r"[iI]?[nN]voice\s*no", r"[iI]?[nN]voiceNo", r"[iI]?[nN]volceNo", 
            r"[mM]volceNo", r"[vV]oice\s*No", r"[vV]oiceNo",
            r"inv\s*no", r"document\s*no", r"reference\s*no", 
            r"ref\s*no", r"number", r"no\b", r"ref\b", r"credit\s*note\s*no", 
            r"credit\s*invoice\s*no"
        ]
        for kw in keywords:
            # Search for keyword followed by some separator and then a number/code (alphanumeric, at least 3 chars)
            pattern = kw + r"\s*[:\.\-#]?\s*([A-Za-z0-9\-]{3,20})"
            matches = re.findall(pattern, ocr_text, re.IGNORECASE)
            if matches:
                for m in matches:
                    m_clean = m.strip()
                    # Ensure it's not a label and has digits
                    if any(c.isdigit() for c in m_clean) and m_clean.lower() not in ("date", "tax", "tel", "fax"):
                        LOGGER.info("Found doc number '%s' near keyword matching pattern '%s'", m_clean, pattern)
                        return m_clean

        # Fallback: search for any sequence of 5 to 15 digits in the text
        matches = re.findall(r'\b\d{5,15}\b', ocr_text)
        if matches:
            filtered = [m for m in matches if m not in ("2020", "2021", "2022", "2023", "2024", "2025", "2026")]
            if filtered:
                # Return the longest numeric candidate (e.g. 300951375300003)
                best_match = max(filtered, key=len)
                LOGGER.info("Preferring numeric document identifier '%s' over label '%s'", best_match, doc_num_clean)
                return best_match
    
    return doc_num_clean


def _clean_extracted_fields(parsed_json: dict[str, Any]) -> dict[str, Any]:
    if not parsed_json:
        return {}
    
    # Reject amount values containing letters
    for field in ["total_amount", "subtotal", "tax_amount"]:
        val = parsed_json.get(field)
        if val is not None:
            val_str = str(val)
            if re.search(r'[A-Za-z]', val_str):
                parsed_json[field] = None

    # Validate document_number using regex
    doc_num = parsed_json.get("document_number")
    if doc_num is not None:
        doc_num_str = str(doc_num).strip()
        if not re.fullmatch(r"^[A-Za-z0-9\-\/\.\s]+$", doc_num_str) or not re.search(r"\d", doc_num_str):
            parsed_json["document_number"] = None

    # Normalize dates to YYYY-MM-DD
    for field in ["document_date"]:
        date_val = parsed_json.get(field)
        if date_val:
            date_str = str(date_val).strip()
            try:
                from dateutil import parser
                parsed = parser.parse(date_str, fuzzy=True)
                parsed_json[field] = parsed.strftime("%Y-%m-%d")
            except Exception:
                parsed_json[field] = None

    # Add confidence scoring per field
    confidences = {}
    for key, value in list(parsed_json.items()):
        if key == "_confidences":
            continue
        if value in (None, "", [], {}):
            confidences[key] = 0.0
        else:
            confidences[key] = 1.0
    parsed_json["_confidences"] = confidences

    return parsed_json


# ---------------------------------------------------------------------------
# PaddleOCR service
# ---------------------------------------------------------------------------


class PaddleOCRService:
    """Handles OCR processing using PaddleOCR."""

    def __init__(self) -> None:
        self._ocr_engine = None
        self._model_verified = False

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
                enable_mkldnn=False,
                cpu_threads=6,
                rec_batch_num=6
            )
            LOGGER.info("PaddleOCR engine initialized successfully.")

    def verify_model(self) -> bool:
        """Verify PaddleOCR is available."""
        try:
            self._init_ocr()
            LOGGER.info("✓ PaddleOCR verified")
            return True
        except Exception as exc:
            LOGGER.error("Failed to initialize PaddleOCR: %s", exc)
            return False
    
    def ensure_initialized(self) -> None:
        """Ensure OCR is initialized - called once at startup."""
        self._init_ocr()
        try:
            LOGGER.info("Warming up PaddleOCR engine...")
            import numpy as np
            dummy_img = np.zeros((100, 100, 3), dtype=np.uint8)
            self._ocr_engine.ocr(dummy_img)
            LOGGER.info("PaddleOCR engine warmed up successfully.")
        except Exception as exc:
            LOGGER.error("Failed to warm up PaddleOCR engine: %s", exc)

    def extract_text(self, file_path: str | Path) -> OCRResult:
        """Extract text from document using PaddleOCR."""
        # Ensure OCR is initialized
        self._init_ocr()
        file_path = Path(file_path)
        LOGGER.info("PaddleOCR extraction started for %s", file_path.name)

        # Page rendering
        pages = _render_pages(file_path)
        page_count = len(pages)

        # OCR processing
        ocr_start = time.perf_counter()
        ocr_texts = []
        for i, page_img in enumerate(pages):
            w, h = page_img.size
            LOGGER.info("Original image dimensions for page %d: %dx%d", i + 1, w, h)
            
            # Resize if either dimension is larger than 500px
            max_size = 500
            if max(w, h) > max_size:
                if w > h:
                    new_w = max_size
                    new_h = int(h * (max_size / w))
                else:
                    new_h = max_size
                    new_w = int(w * (max_size / h))
                LOGGER.info("Resizing page %d from %dx%d to %dx%d for OCR optimization", i + 1, w, h, new_w, new_h)
                page_img = page_img.resize((new_w, new_h), Image.Resampling.LANCZOS if hasattr(Image, "Resampling") else Image.LANCZOS)
                w, h = page_img.size

            LOGGER.info("Running PaddleOCR on page %d/%d (dimensions: %dx%d) for %s", i + 1, page_count, w, h, file_path.name)
            img_np = np.array(page_img)
            # Convert RGBA to RGB if necessary
            if img_np.ndim == 3 and img_np.shape[2] == 4:
                img_np = np.array(page_img.convert("RGB"))

            # PaddleOCR expects numpy array
            result = self._ocr_engine.ocr(img_np)
            
            page_text_lines = []
            if result and result[0]:
                rec_texts = result[0].get("rec_texts", [])
                if rec_texts:
                    page_text_lines = [str(t) for t in rec_texts if t is not None]
            ocr_texts.append("\n".join(page_text_lines))

        raw_ocr_text = "\n\n--- PAGE BREAK ---\n\n".join(ocr_texts)
        ocr_time = time.perf_counter() - ocr_start
        LOGGER.info("PaddleOCR extraction completed in %.2fs", ocr_time)

        total_time = ocr_time
        LOGGER.info(
            "OCR complete file=%s pages=%d ocr_time=%.2fs total_time=%.2fs",
            file_path.name, page_count, ocr_time, total_time
        )

        return OCRResult(
            ocr_text=raw_ocr_text,
            page_count=page_count,
            ocr_time=ocr_time,
            processing_time=total_time,
        )


# ---------------------------------------------------------------------------
# Document Classification service
# ---------------------------------------------------------------------------


class DocumentClassificationService:
    """Handles document classification using Qwen2.5:0.5B."""

    def __init__(self) -> None:
        settings = get_settings()
        self.ollama_url: str = settings.ollama_url
        self.model: str = settings.ollama_classification_model
        self._model_verified = False

    def verify_model(self) -> bool:
        """Check that Ollama is running and the required model is available."""
        from urllib import error, request as urllib_request
        import sys

        tags_url = f"{self.ollama_url.rstrip('/')}/api/tags"
        try:
            req = urllib_request.Request(tags_url, method="GET")
            with urllib_request.urlopen(req, timeout=5) as response:
                data = json.loads(response.read().decode("utf-8"))
        except Exception as exc:
            msg = f"Ollama model '{self.model}' not running."
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

        msg = f"Ollama model '{self.model}' not running."
        print(msg, file=sys.stderr)
        LOGGER.error("%s Model '%s' not found in Ollama. Available models: %s", msg, self.model, available_names)
        return False

    def classify(self, ocr_text: str) -> ClassificationResult:
        """Classify document type using fast Python heuristics, falling back to Qwen2.5:0.5B."""
        classification_start = time.perf_counter()
        
        # Fast Python-based keyword heuristics
        text_lower = ocr_text.lower()
        
        heuristics = [
            ("tax invoice", "invoice"),
            ("invoice", "invoice"),
            ("bill to", "invoice"),
            ("receipt", "receipt"),
            ("sales receipt", "receipt"),
            ("payment receipt", "receipt"),
            ("purchase order", "purchase_order"),
            ("po no", "purchase_order"),
            ("credit note", "credit_note"),
            ("credit memo", "credit_note"),
            ("bank statement", "bank_statement"),
            ("monthly statement", "bank_statement"),
            ("debit note", "debit_note"),
            ("tax document", "tax_document"),
            ("tax form", "tax_document"),
            ("balance sheet", "financial_report"),
            ("income statement", "financial_report"),
        ]
        
        for keyword, doc_type in heuristics:
            if keyword in text_lower:
                classification_time = time.perf_counter() - classification_start
                LOGGER.info("Document classification completed in %.4fs (heuristic): %s", classification_time, doc_type)
                return ClassificationResult(
                    document_type=doc_type,
                    classification_time=classification_time,
                    processing_time=classification_time,
                )

        LOGGER.info("Document classification started using Qwen2.5:0.5B (no heuristic match)")

        prompt = (
            "You are an expert Intelligent Document Processing system.\n\n"
            "Analyze the following OCR-extracted text from a document:\n\n"
            "--- START DOCUMENT TEXT ---\n"
            f"{ocr_text}\n"
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
            "Return ONLY the document type name.\n"
            "Do not explain.\n"
        )

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
            "keep_alive": 0,
            "options": {
                "temperature": 0.1,
                "num_predict": 512,
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
            LOGGER.error("Ollama classification request failed: %s", exc)
            return ClassificationResult(
                document_type="other_financial_document",
                classification_time=0.0,
                processing_time=0.0,
            )

        try:
            api_response = json.loads(raw)
            document_type = api_response.get("message", {}).get("content", "").strip().lower()
        except (json.JSONDecodeError, KeyError) as exc:
            LOGGER.error("Failed to parse Ollama classification response: %s", exc)
            document_type = "other_financial_document"

        # Normalize document type
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

        document_type = _DOC_TYPE_MAP.get(document_type, "other_financial_document")

        classification_time = time.perf_counter() - classification_start
        LOGGER.info("Document classification completed in %.2fs: %s", classification_time, document_type)

        return ClassificationResult(
            document_type=document_type,
            classification_time=classification_time,
            processing_time=classification_time,
        )


# ---------------------------------------------------------------------------
# Field Extraction service
# ---------------------------------------------------------------------------


class FieldExtractionService:
    """Handles field extraction using DeepSeek-R1:8B."""

    def __init__(self) -> None:
        settings = get_settings()
        self.ollama_url: str = settings.ollama_url
        self.model: str = settings.ollama_model
        self._model_verified = False

    def verify_model(self) -> bool:
        """Check that Ollama is running and the required model is available."""
        from urllib import error, request as urllib_request
        import sys

        tags_url = f"{self.ollama_url.rstrip('/')}/api/tags"
        try:
            req = urllib_request.Request(tags_url, method="GET")
            with urllib_request.urlopen(req, timeout=5) as response:
                data = json.loads(response.read().decode("utf-8"))
        except Exception as exc:
            msg = f"Ollama model '{self.model}' not running."
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

        msg = f"Ollama model '{self.model}' not running."
        print(msg, file=sys.stderr)
        LOGGER.error("%s Model '%s' not found in Ollama. Available models: %s", msg, self.model, available_names)
        return False

    def extract_fields(self, ocr_text: str, document_type: str) -> ExtractionResult:
        """Extract fields from document using Ollama model."""
        LOGGER.info("Field extraction started using %s", self.model)

        # Model verification happens once at startup

        extraction_start = time.perf_counter()

        prompt = (
            "You are an expert Intelligent Document Processing system.\n\n"
            "Analyze the following JSON extracted from a document by a vision model. It contains core fields and an 'amount_block' of raw text:\n\n"
            "--- START EXTRACTED JSON ---\n"
            f"{ocr_text}\n"
            "--- END EXTRACTED JSON ---\n\n"
            "Your task is to merge the core fields and apply financial reasoning to the 'amount_block' to extract final totals.\n\n"
            "Apply the following rules carefully:\n"
            "1. Map the directly extracted fields (document_number, document_date, vendor_name, customer_name, currency).\n"
            "2. Determine 'document_type' (e.g. Invoice, Receipt) based on the context.\n"
            "3. Tax Extraction (from amount_block):\n"
            "   - If you see 'VAT Amt', 'VAT Amount', 'Tax Amount', or 'VAT', extract the numeric value into tax_amount.\n"
            "   - If there are multiple VAT amounts, extract the HIGHEST numeric value as tax_amount.\n"
            "   - NEVER return null for tax_amount if a VAT amount explicitly exists.\n"
            "4. Total Extraction (from amount_block):\n"
            "   - Look for any phrase containing 'Total', 'Gross Amt', 'Gross Amount', or 'Invoice Total' (e.g. 'Total Price', 'Total in SAR', 'Total Price FCA').\n"
            "   - If found, extract the associated numeric value into total_amount.\n"
            "   - If multiple totals exist, extract the HIGHEST numeric value.\n"
            "   - NEVER return null for total_amount if one of those phrases exists.\n"
            "5. Subtotal Extraction (from amount_block):\n"
            "   - Extract into subtotal if explicitly present.\n"
            "6. Normalizations & Constraints:\n"
            "   - Convert European formatting (e.g. 276,00 -> 276.00, 20,085.71 -> 20085.71). Remove currency symbols.\n"
            "   - Never hallucinate values. If a value is not explicitly present, return null.\n\n"
            "Return ONLY valid JSON.\n"
            "Do not explain.\n"
            "Do not wrap with ```json.\n\n"
            "CRITICAL RULES FOR JSON OUTPUT:\n"
            "1. Your response MUST be a valid JSON object containing exactly the following keys, with NO extra keys and NO missing keys:\n"
            "   {\n"
            "     \"document_type\": <string or null>,\n"
            "     \"document_number\": <string or null>,\n"
            "     \"document_date\": <string (YYYY-MM-DD) or null>,\n"
            "     \"vendor_name\": <string or null>,\n"
            "     \"customer_name\": <string or null>,\n"
            "     \"currency\": <string (3-letter) or null>,\n"
            "     \"subtotal\": <number or null>,\n"
            "     \"tax_amount\": <number or null>,\n"
            "     \"total_amount\": <number or null>\n"
            "   }\n"
            "2. If you cannot extract a numeric value for subtotal, tax_amount, or total_amount, you MUST still output the key with a null value.\n\n"
            "CRITICAL: Keep your reasoning/thinking path (inside <think>...) brief."
        )

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
            "keep_alive": 0,
            "options": {
                "temperature": 0.1,
                "num_predict": 512,
            },
        }
        if "deepseek" not in self.model.lower():
            payload["format"] = "json"

        body = json.dumps(payload).encode("utf-8")
        chat_url = f"{self.ollama_url.rstrip('/')}/api/chat"

        req = urllib_request.Request(
            chat_url,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        import subprocess
        LOGGER.info("Starting inference with model: %s", self.model)
        try:
            ps_out = subprocess.check_output(["ollama", "ps"]).decode().strip()
            LOGGER.info("ollama ps during GPT-OSS inference start:\n%s", ps_out)
        except Exception as e:
            LOGGER.error("Failed to run ollama ps: %s", e)

        inference_start = time.perf_counter()
        try:
            with urllib_request.urlopen(req, timeout=300) as response:
                raw = response.read().decode("utf-8")
        except error.URLError as exc:
            LOGGER.error("Ollama extraction request failed: %s", exc)
            return ExtractionResult(
                extracted_json={},
                raw_response="",
                extraction_time=0.0,
                processing_time=0.0,
            )
        inference_end = time.perf_counter()
        inference_duration = inference_end - inference_start
        LOGGER.info("Inference completed with model %s in %.2fs", self.model, inference_duration)

        try:
            api_response = json.loads(raw)
            raw_response = api_response.get("message", {}).get("content", "")
            eval_count = api_response.get("eval_count", 0)
            prompt_eval_count = api_response.get("prompt_eval_count", 0)
            LOGGER.info("GPT-OSS - Prompt token count: %d, Completion token count: %d", prompt_eval_count, eval_count)
        except (json.JSONDecodeError, KeyError) as exc:
            LOGGER.error("Failed to parse Ollama extraction response: %s", exc)
            raw_response = ""

        # Parse JSON response
        parsed_json = self._parse_json_response(raw_response) or {}

        # Apply document number cleaning/post-processing
        if parsed_json is not None:
            parsed_json["document_number"] = _clean_document_number(
                parsed_json.get("document_number"), ocr_text
            )
            parsed_json = _clean_extracted_fields(parsed_json)

        extraction_time = time.perf_counter() - extraction_start
        LOGGER.info("Field extraction completed in %.2fs", extraction_time)

        return ExtractionResult(
            extracted_json=parsed_json,
            raw_response=raw_response,
            extraction_time=extraction_time,
            processing_time=extraction_time,
        )

    def _parse_json_response(self, text: str) -> dict[str, Any] | None:
        """Best-effort extraction of a JSON dict from raw model output, handling thought tags."""
        # Strip think tags first
        cleaned = text
        if "<think>" in cleaned:
            parts = cleaned.split("</think>", 1)
            if len(parts) > 1:
                cleaned = parts[1].strip()

        # Strip markdown fences if the model ignored our instructions
        import re
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
# Validation service
# ---------------------------------------------------------------------------


class ValidationService:
    """Handles JSON validation using pure Python DocumentValidator."""

    def __init__(self) -> None:
        self._model_verified = True

    def verify_model(self) -> bool:
        """Pure Python validation requires no model checks."""
        return True

    def validate_json(self, extracted_json: dict[str, Any], document_type: str) -> ValidationResult:
        """Validate extracted JSON using pure Python rules."""
        LOGGER.info("JSON validation started (pure Python)")
        validation_start = time.perf_counter()
        
        from services.validation import DocumentValidator, REQUIRED_FIELDS
        validator = DocumentValidator()
        result = validator.validate(document_type, extracted_json)
        
        # Calculate missing required fields
        required_fields = REQUIRED_FIELDS.get(document_type, [])
        missing = [f for f in required_fields if extracted_json.get(f) in (None, "", [])]
        
        validation_time = time.perf_counter() - validation_start
        LOGGER.info("JSON validation completed in %.6fs: valid=%s score=%.2f", validation_time, result.valid, result.score)
        
        return ValidationResult(
            is_valid=result.valid,
            issues=[f"{issue.field}: {issue.message}" for issue in result.issues],
            score=result.score,
            required_fields_missing=missing,
            validation_time=validation_time,
            processing_time=validation_time,
        )


# ---------------------------------------------------------------------------
# Confidence calculation service (Python rule engine)
# ---------------------------------------------------------------------------


class ConfidenceCalculationService:
    """Handles confidence calculation using Python rules (not LLM)."""

    def __init__(self) -> None:
        pass

    def calculate_confidence(self, validation_result: dict[str, Any], extracted_json: dict[str, Any], document_type: str) -> ConfidenceResult:
        """Calculate confidence using Python rules."""
        LOGGER.info("Confidence calculation started (Python rule engine)")

        confidence_start = time.perf_counter()

        # Core fields checklist for robust confidence scoring
        # Calculate confidence using user-specified weights
        weights = {
            "document_number": 0.20,
            "document_date": 0.15,
            "vendor_name": 0.15,
            "currency": 0.10,
            "subtotal": 0.15,
            "tax_amount": 0.10,
            "total_amount": 0.15,
        }

        base_score = 0.0
        for field, weight in weights.items():
            val = extracted_json.get(field)
            if val not in (None, "", [], {}):
                base_score += weight

        # Apply a penalty based on validation issues, max 30% deduction
        issues = validation_result.get("issues", [])
        issue_deduction = min(len(issues) * 0.05, 0.30)
        
        score = base_score - issue_deduction

        # Calculate final confidence rounded to 2 decimal places
        confidence = round(max(0.0, min(1.0, score)), 2)

        confidence_time = time.perf_counter() - confidence_start
        LOGGER.info(
            "Confidence calculation completed in %.2fs: confidence=%.2f | issues_count=%d",
            confidence_time, confidence, len(issues)
        )

        return ConfidenceResult(
            confidence=confidence,
            confidence_time=confidence_time,
            processing_time=confidence_time,
        )


# ---------------------------------------------------------------------------
# Main orchestrator
# ---------------------------------------------------------------------------


class MultiModelOrchestrator:
    """Orchestrates the multi-model IDP pipeline."""

    def __init__(self) -> None:
        self.ocr_service = PaddleOCRService()
        self.classification_service = DocumentClassificationService()
        self.extraction_service = FieldExtractionService()
        self.validation_service = ValidationService()
        self.confidence_service = ConfidenceCalculationService()
    
    def ensure_initialized(self) -> None:
        """Ensure all services are initialized once at startup."""
        # Ollama models are verified in their respective verify_model() methods
        # which are called during startup in backend/main.py

    def process_file(self, file_path: str | Path) -> ProcessingResult:
        """Process a document through the complete multi-model pipeline."""
        file_path = Path(file_path)
        LOGGER.info("Multi-model processing started for %s", file_path.name)

        # Stage 1: OCR
        LOGGER.info("OCR started")
        ocr_start = time.perf_counter()
        ocr_result = self.ocr_service.extract_text(file_path)
        ocr_time = time.perf_counter() - ocr_start
        LOGGER.info("OCR completed")

        # DEBUG: Verify OCR text before sending to DeepSeek
        LOGGER.info("OCR Text Length: %d", len(ocr_result.ocr_text))
        LOGGER.info("First 500 characters of OCR text:\n%s", ocr_result.ocr_text[:500])

        # Stage 2: Classification
        LOGGER.info("Classification started")
        classification_start = time.perf_counter()
        classification_result = self.classification_service.classify(ocr_result.ocr_text)
        classification_time = time.perf_counter() - classification_start

        # Stage 3: Field Extraction
        LOGGER.info("Extraction started")
        extraction_start = time.perf_counter()
        extraction_result = self.extraction_service.extract_fields(ocr_result.ocr_text, classification_result.document_type)
        extraction_time = time.perf_counter() - extraction_start

        # Stage 4: Validation
        validation_start = time.perf_counter()
        validation_result = self.validation_service.validate_json(extraction_result.extracted_json, classification_result.document_type)
        validation_time = time.perf_counter() - validation_start

        # Stage 5: Confidence Calculation
        confidence_start = time.perf_counter()
        confidence_result = self.confidence_service.calculate_confidence(
            validation_result.__dict__,
            extraction_result.extracted_json,
            classification_result.document_type,
        )
        confidence_time = time.perf_counter() - confidence_start

        # Calculate total time
        total_time = ocr_time + classification_time + extraction_time + validation_time + confidence_time

        LOGGER.info(
            "Multi-model processing completed for %s | total_time=%.2fs ocr=%.2fs classification=%.2fs extraction=%.2fs validation=%.2fs confidence=%.2fs",
            file_path.name, total_time, ocr_time, classification_time, extraction_time, validation_time, confidence_time
        )
        LOGGER.info(
            "Processing details for %s | doc_type=%s confidence=%.2f fields_extracted=%d",
            file_path.name, classification_result.document_type, confidence_result.confidence, len(extraction_result.extracted_json) if extraction_result.extracted_json else 0
        )

        return ProcessingResult(
            ocr_result=ocr_result,
            classification_result=classification_result,
            extraction_result=extraction_result,
            validation_result=validation_result,
            confidence_result=confidence_result,
            total_time=total_time,
            raw_ocr_text=ocr_result.ocr_text,
            document_type=classification_result.document_type,
        )


# Singleton instance
orchestrator = MultiModelOrchestrator()
