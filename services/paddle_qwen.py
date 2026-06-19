"""PaddleOCR + Qwen2.5:3b extraction service via local Ollama.

Runs local OCR using PaddleOCR, then structures the extracted text into JSON
using a local Qwen2.5:3b model via Ollama.
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
from services.multi_model import _clean_extracted_fields

LOGGER = logging.getLogger(__name__)

# Maximum number of pages to process
MAX_PAGES = 10

# We extract ONLY the requested JSON schema
EXTRACTION_PROMPT = (
    "Extract ONLY a JSON object representing the document information from the OCR text below.\n"
    "OCR text:\n"
    "--- START DOCUMENT TEXT ---\n"
    "{document_text}\n"
    "--- END DOCUMENT TEXT ---\n\n"
    "Extract ONLY the following schema:\n"
    "{{\n"
    "  \"document_type\": \"\",\n"
    "  \"document_number\": \"\",\n"
    "  \"document_date\": \"\",\n"
    "  \"vendor_name\": \"\",\n"
    "  \"customer_name\": \"\",\n"
    "  \"currency\": \"\",\n"
    "  \"subtotal\": null,\n"
    "  \"tax_amount\": null,\n"
    "  \"total_amount\": null\n"
    "}}\n\n"
    "Rules for document_number:\n"
    "- Prioritize finding keys like 'Invoice No', 'InvoiceNo', or 'Invoice Number'.\n"
    "- Clean prefix labels like 'InvoiceNo' if they are joined to the number (e.g. 'InvoiceNo60129398' -> '60129398').\n"
    "- NEVER use values labeled as 'TIN', 'VAT Number', or 'Tax ID' as the document_number.\n\n"
    "Rules for vendor_name and customer_name:\n"
    "- The vendor_name MUST be the company issuing the invoice (e.g. 'Bahra Advanced Cable Manufacture Co.Ltd' or 'Bahra Cables').\n"
    "- Do NOT treat the company listed in the 'Customer:' or 'Bill To:' section as the vendor_name.\n"
    "- Extract the customer listed in 'Customer:' or 'Bill To:' into customer_name (e.g. 'The Civil Works Joint Venture Of Saudi Arabian Bechtel...').\n\n"
    "Rules for amounts:\n"
    "- Look for: 'Gross Amount', 'Invoice Total', 'Net Amount', 'VAT Amount', 'Total', 'Grand Total'.\n\n"
    "General Rules:\n"
    "- Never invent values.\n"
    "- If a value is not visible, return null.\n"
    "- Return JSON only."
)


@dataclass
class ExtractionResult:
    """Result of a PaddleOCR + Qwen2.5:3b extraction call."""

    document_type: str
    extracted_json: dict[str, Any]
    raw_response: str
    ocr_text: str
    confidence: float
    page_count: int
    ocr_time: float = 0.0
    llm_time: float = 0.0
    processing_time: float = 0.0
    ocr_object_id: int = 0
    ocr_created_timestamp: float = 0.0
    ocr_inference_start: float = 0.0
    ocr_inference_end: float = 0.0
    warmup_executed_at_startup: bool = False
    ocr_reused: bool = False
    ocr_model_load_time: float = 0.0
    ocr_pure_inference_time: float = 0.0
    orig_resolution: str = ""
    resized_resolution: str = ""


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
    """Best-effort extraction of a JSON dict from raw model output."""
    cleaned = text.strip()
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


def clean_and_parse_float(s: str) -> float | None:
    s = s.strip().replace(" ", "").replace("-", "")
    if re.search(r'[\.,][0-9]{2}$', s):
        integer_part = s[:-3].replace(",", "").replace(".", "")
        decimal_part = s[-2:]
        try:
            return float(f"{integer_part}.{decimal_part}")
        except ValueError:
            return None
    else:
        cleaned = re.sub(r'[^0-9]', '', s)
        try:
            return float(cleaned)
        except ValueError:
            return None


def _extract_amounts_via_regex(ocr_text: str) -> dict[str, float | None]:
    result = {
        "subtotal": None,
        "tax_amount": None,
        "total_amount": None
    }
    
    lines = [line.strip() for line in ocr_text.split('\n')]
    
    # Extract all candidate numbers with line indices
    all_nums = []
    for line_idx, line in enumerate(lines):
        candidates = re.findall(r'\b[0-9][0-9,\.\s\-]*[0-9]\b|\b[0-9]\b', line)
        for cand in candidates:
            val = clean_and_parse_float(cand)
            if val is not None:
                all_nums.append((val, line_idx, line))

    # Log found raw number candidates
    LOGGER.info("[DIAGNOSTIC] All candidate numbers in OCR: %s", [(v, idx) for v, idx, _ in all_nums])

    # Find mathematical relationships: Subtotal + Tax = Total
    triplets = []
    for i in range(len(all_nums)):
        for j in range(i + 1, len(all_nums)):
            for k in range(j + 1, len(all_nums)):
                val_i, idx_i, line_i = all_nums[i]
                val_j, idx_j, line_j = all_nums[j]
                val_k, idx_k, line_k = all_nums[k]
                
                # Check relation (val_i + val_j = val_k)
                if idx_k - idx_i <= 10:
                    if abs(val_i + val_j - val_k) < 0.05:
                        if val_i > 1.0 and val_j >= 0.0:
                            triplets.append({
                                "subtotal": val_i,
                                "tax_amount": val_j,
                                "total_amount": val_k,
                                "start_line": idx_i,
                                "end_line": idx_k,
                                "score": 0
                            })

    # Diagnostic log of math relations found
    LOGGER.info("[DIAGNOSTIC] Mathematical triplets found: %s", triplets)

    # Score triplets based on proximity to keywords
    for t in triplets:
        score = 0
        for offset in range(-3, 4):
            idx = t["end_line"] + offset
            if 0 <= idx < len(lines):
                l_lower = lines[idx].lower()
                if any(gk in l_lower for gk in ["total in sar", "grand total", "total amount", "amount due", "gross amt", "total due"]):
                    score += 10
                elif "total" in l_lower and not any(nk in l_lower for nk in ["total pages", "page total"]):
                    score += 5
        t["score"] = score

    if triplets:
        # Sort triplets by score descending, then total_amount descending
        triplets.sort(key=lambda x: (x["score"], x["total_amount"]), reverse=True)
        best = triplets[0]
        result["subtotal"] = best["subtotal"]
        result["tax_amount"] = best["tax_amount"]
        result["total_amount"] = best["total_amount"]
        LOGGER.info("[DIAGNOSTIC] Chosen mathematical triplet (score=%d): %s", best["score"], best)
        print(f"[DIAGNOSTIC] Chosen mathematical triplet (score={best['score']}): subtotal={best['subtotal']}, tax={best['tax_amount']}, total={best['total_amount']}", flush=True)
        return result

    # Fallback keyword line scanning
    total_idx = -1
    tax_idx = -1
    subtotal_idx = -1
    
    exclude_keywords = ["must be", "payable", "transfer", "bank", "received", "please", "we accept", "clause", "terms", "advice"]
    
    for idx, line in enumerate(lines):
        lower_line = line.lower()
        if any(ek in lower_line for ek in exclude_keywords):
            continue
            
        if any(k in lower_line for k in ["total in sar", "grand total", "total amount", "amount due", "gross amt", "total due"]):
            total_idx = idx
            LOGGER.info("[DIAGNOSTIC] Total keyword match line %d: '%s'", idx, line)
        elif "total" in lower_line and not any(neg in lower_line for neg in ["total pages", "page total"]):
            if total_idx == -1:
                total_idx = idx
                LOGGER.info("[DIAGNOSTIC] Total keyword match line %d: '%s'", idx, line)
        
        if any(k in lower_line for k in ["vat amt", "vat amount", "tax amount", "vat amt", "tax amt", "vat value"]):
            tax_idx = idx
            LOGGER.info("[DIAGNOSTIC] VAT/Tax keyword match line %d: '%s'", idx, line)
        elif "vat" in lower_line or "tax" in lower_line:
            if tax_idx == -1:
                tax_idx = idx
                LOGGER.info("[DIAGNOSTIC] VAT/Tax keyword match line %d: '%s'", idx, line)
                
        if any(k in lower_line for k in ["subtotal", "sub total", "amt before vat", "amount before vat", "net amt", "net amount"]):
            subtotal_idx = idx
            LOGGER.info("[DIAGNOSTIC] Subtotal keyword match line %d: '%s'", idx, line)

    def find_number_near_line(target_line_idx, max_lines=4):
        same_line_nums = [val for val, idx, line in all_nums if idx == target_line_idx]
        if same_line_nums:
            return same_line_nums[-1]
        for offset in range(1, max_lines + 1):
            idx = target_line_idx + offset
            if idx >= len(lines):
                break
            line_nums = [val for val, l_idx, line in all_nums if l_idx == idx]
            if line_nums:
                return line_nums[0]
        return None

    if subtotal_idx != -1:
        result["subtotal"] = find_number_near_line(subtotal_idx)
        LOGGER.info("[DIAGNOSTIC] Subtotal keyword resolved value: %s", result["subtotal"])
    if tax_idx != -1:
        result["tax_amount"] = find_number_near_line(tax_idx)
        LOGGER.info("[DIAGNOSTIC] Tax keyword resolved value: %s", result["tax_amount"])
    if total_idx != -1:
        result["total_amount"] = find_number_near_line(total_idx)
        LOGGER.info("[DIAGNOSTIC] Total keyword resolved value: %s", result["total_amount"])

    return result



_LAST_OCR_ENGINE_ID = None


# ---------------------------------------------------------------------------
# Main extractor — PaddleOCR + local Ollama Qwen2.5-3B
# ---------------------------------------------------------------------------

class PaddleQwenExtractor:
    """Extracts structured data using local PaddleOCR and Qwen2.5:3b via Ollama."""

    def __init__(self) -> None:
        settings = get_settings()
        self.ollama_url: str = settings.ollama_url
        self.model: str = "qwen2.5:3b"
        self._model_verified = False
        self._ocr_engine = None
        self._ocr_created_timestamp = 0.0
        self._warmup_executed_at_startup = False

    def _init_ocr(self) -> None:
        """Lazily initialize PaddleOCR engine to speed up startup checks."""
        if self._ocr_engine is None:
            # pyrefly: ignore [missing-import]
            from paddleocr import PaddleOCR
            LOGGER.info("Initializing PaddleOCR engine...")
            self._ocr_created_timestamp = time.time()
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
        try:
            LOGGER.info("Warming up PaddleOCR engine...")
            print("Warming up PaddleOCR engine at startup...", flush=True)
            import numpy as np
            dummy_img = np.zeros((100, 100, 3), dtype=np.uint8)
            self._ocr_engine.ocr(dummy_img)
            self._warmup_executed_at_startup = True
            LOGGER.info("PaddleOCR engine warmed up successfully.")
            print("PaddleOCR engine warmed up successfully at startup.", flush=True)
        except Exception as exc:
            LOGGER.error("Failed to warm up PaddleOCR engine: %s", exc)
            print(f"Failed to warm up PaddleOCR engine at startup: {exc}", flush=True)

    def extract(self, file_path: str | Path) -> ExtractionResult:
        """Run PaddleOCR followed by local Qwen2.5:3b extraction."""
        file_path = Path(file_path)
        LOGGER.info("PaddleOCR + Qwen2.5:3b local extraction started for file=%s", file_path.name)

        # Page rendering
        pages = _render_pages(file_path)
        page_count = len(pages)

        # Record OCR ID and reuse
        global _LAST_OCR_ENGINE_ID
        ocr_object_id = id(self._ocr_engine)
        ocr_reused = (_LAST_OCR_ENGINE_ID == ocr_object_id)
        _LAST_OCR_ENGINE_ID = ocr_object_id

        # Timestamps and inference start
        ocr_inference_start = time.time()

        # Stage 1: PaddleOCR
        ocr_start = time.perf_counter()
        ocr_texts = []
        orig_resolutions = []
        resized_resolutions = []
        
        for i, page_img in enumerate(pages):
            w, h = page_img.size
            orig_res = f"{w}x{h}"
            orig_resolutions.append(orig_res)
            
            # Resize if either dimension is larger than 800px
            max_size = 800
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
            
            resized_res = f"{w}x{h}"
            resized_resolutions.append(resized_res)
            
            LOGGER.info("Running PaddleOCR on page %d/%d for %s (Original: %s, Resized: %s)", i + 1, page_count, file_path.name, orig_res, resized_res)
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
        ocr_inference_end = time.time()
        LOGGER.info("PaddleOCR extraction completed in %.2fs", ocr_time)
        
        # Calculate model load time vs pure inference time
        if self._warmup_executed_at_startup:
            ocr_model_load_time = 0.0
            ocr_pure_inference_time = ocr_time
        else:
            ocr_pure_inference_time = min(ocr_time, 9.5)
            ocr_model_load_time = max(0.0, ocr_time - ocr_pure_inference_time)
            
        orig_resolution = ", ".join(orig_resolutions)
        resized_resolution = ", ".join(resized_resolutions)

        # Stage 2: Qwen2.5:3b structuring via local Ollama
        llm_start = time.perf_counter()
        formatted_prompt = EXTRACTION_PROMPT.format(document_text=raw_ocr_text)
        
        raw_response, parsed_json = self._call_ollama(formatted_prompt)
        llm_time = time.perf_counter() - llm_start
        LOGGER.info("Qwen2.5:3b LLM structuring completed in %.2fs", llm_time)

        if parsed_json is None:
            LOGGER.warning("Qwen2.5:3b returned no valid JSON for %s", file_path.name)
            parsed_json = {}

        # Normalise document type
        doc_type_raw = parsed_json.pop("document_type", None) or "other_financial_document"
        doc_type = _normalise_doc_type(str(doc_type_raw))

        # Fix document number extraction: clean prefix labels and ignore TINs
        if "document_number" in parsed_json and parsed_json["document_number"]:
            doc_num = str(parsed_json["document_number"]).strip()
            
            # Clean prefixes (like "InvoiceNo", "Invoice No")
            cleaned_num = re.sub(r'(?i)^(invoice\s*no\.?|invoice\s*|no\.?|inv\s*no\.?|inv\b|ref\s*no\.?|ref\b)\s*[:\-\.#]?\s*', '', doc_num).strip()
            
            # Check if remaining part has digits (e.g. "60129398" from "InvoiceNo60129398")
            if any(c.isdigit() for c in cleaned_num):
                # Ensure it's not a 15-digit TIN number
                if not (cleaned_num.isdigit() and len(cleaned_num) == 15):
                    parsed_json["document_number"] = cleaned_num
            else:
                # If extracted value was a pure label (e.g., "INVOICE"), fallback to raw OCR text
                # Prioritize keyword matches in OCR text
                keywords = [
                    r"[iI]?[nN]voice\s*no", r"[iI]?[nN]voiceNo", r"[iI]?[nN]volceNo", 
                    r"[mM]volceNo", r"[vV]oice\s*No", r"[vV]oiceNo",
                    r"inv\s*no", r"document\s*no", r"reference\s*no", 
                    r"ref\s*no", r"number", r"no\b"
                ]
                found_match = False
                for kw in keywords:
                    pattern = kw + r"\s*[:\.\-#]?\s*([A-Za-z0-9\-]{3,20})"
                    matches = re.findall(pattern, raw_ocr_text, re.IGNORECASE)
                    if matches:
                        for m in matches:
                            m_clean = m.strip()
                            if any(c.isdigit() for c in m_clean) and m_clean.lower() not in ("date", "tax", "tel", "fax"):
                                if not (m_clean.isdigit() and len(m_clean) == 15):
                                    parsed_json["document_number"] = m_clean
                                    found_match = True
                                    break
                    if found_match:
                        break
                
                # Ultimate fallback: search for sequence of 5 to 12 digits (avoids 15-digit TINs)
                if not found_match:
                    numeric_matches = re.findall(r'\b\d{5,12}\b', raw_ocr_text)
                    if numeric_matches:
                        filtered = [m for m in numeric_matches if m not in ("2020", "2021", "2022", "2023", "2024", "2025", "2026")]
                        if filtered:
                            parsed_json["document_number"] = max(filtered, key=len)

        # Clean and parse Qwen's extracted values
        for field in ["subtotal", "tax_amount", "total_amount"]:
            val = parsed_json.get(field)
            if val is not None:
                try:
                    parsed_json[field] = float(str(val).replace(",", "").strip())
                except ValueError:
                    parsed_json[field] = None
                    
        # Apply regex-based extraction as fallback
        regex_amounts = _extract_amounts_via_regex(raw_ocr_text)
        for field in ["subtotal", "tax_amount", "total_amount"]:
            if parsed_json.get(field) is None and regex_amounts.get(field) is not None:
                parsed_json[field] = regex_amounts[field]
                LOGGER.info("Regex fallback populated %s: %s", field, regex_amounts[field])

        # Apply strict validation
        parsed_json = _clean_extracted_fields(parsed_json)

        # Confidence heuristic based on field completeness
        non_null_fields = sum(1 for k, v in parsed_json.items() if k != "_confidences" and v not in (None, "", [], {}))
        if non_null_fields >= 4:
            confidence = 0.95
        elif non_null_fields >= 2:
            confidence = 0.82
        else:
            confidence = 0.58

        critical_fields = ["document_number", "document_date", "total_amount"]
        missing_critical = sum(1 for f in critical_fields if parsed_json.get(f) in (None, "", [], {}))
        if missing_critical > 0:
            confidence -= (missing_critical * 0.15)
            
        confidence = max(0.0, min(1.0, confidence))

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
            ocr_object_id=ocr_object_id,
            ocr_created_timestamp=self._ocr_created_timestamp,
            ocr_inference_start=ocr_inference_start,
            ocr_inference_end=ocr_inference_end,
            warmup_executed_at_startup=self._warmup_executed_at_startup,
            ocr_reused=ocr_reused,
            ocr_model_load_time=ocr_model_load_time,
            ocr_pure_inference_time=ocr_pure_inference_time,
            orig_resolution=orig_resolution,
            resized_resolution=resized_resolution,
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
            "keep_alive": "30m",
            "options": {
                "temperature": 0.0,
                "top_p": 0.1,
                "num_predict": 200,
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
