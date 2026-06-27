from __future__ import annotations

import json
import logging
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx
from PIL import Image
from rapidfuzz import fuzz

from services.settings import get_settings
from services.qari_ocr_service import QariOCRService
from services.ollama_extractor import deduplicate_tokens, clean_metadata_value
from services.merge_extractor import (
    count_chars_by_language,
    detect_field_language,
    is_invalid_customer_name,
    validate_field_value,
    recover_company_name,
    recover_address,
    find_arabic_company_name,
    find_english_company_name
)

LOGGER = logging.getLogger(__name__)

FINAL_COLUMNS = [
    "document_number",
    "vat_number",
    "document_date",
    "currency",
    "vendor_name_ar",
    "vendor_name_en",
    "customer_name_ar",
    "customer_name_en",
    "address_ar",
    "address_en",
    "subtotal",
    "tax_amount",
    "total_amount",
]

FIELD_WEIGHTS = {
    "document_number": 0.15,
    "vat_number": 0.15,
    "document_date": 0.10,
    "currency": 0.05,
    "vendor_name_ar": 0.10,
    "vendor_name_en": 0.10,
    "customer_name_ar": 0.08,
    "customer_name_en": 0.08,
    "address_ar": 0.06,
    "address_en": 0.06,
    "subtotal": 0.04,
    "tax_amount": 0.04,
    "total_amount": 0.04,
}

@dataclass
class QwenLlmExtractionResult:
    document_type: str
    extracted_json: dict[str, Any]
    raw_response: str
    ocr_text: str
    qari_ocr_text: str
    confidence: float
    page_count: int
    ocr_time: float
    qari_ocr_time: float
    llm_time: float
    validation_time: float
    processing_time: float


def detect_repetition_loop(text: str) -> bool:
    if not text:
        return False
    # Clean text and split into tokens of alphanumeric characters,
    # treating hyphens/punctuation as word boundaries.
    tokens = re.findall(r'[a-zA-Z0-9\u0600-\u06FF]+', text.lower())
    if not tokens:
        return False
    
    n = len(tokens)
    # Check for consecutive repetition of sub-sequences of size k
    # k can be from 1 up to 30 words
    for k in range(1, 31):
        if k * 3 > n:
            break
        # Slide through the tokens
        for i in range(n - 3 * k + 1):
            seq1 = tokens[i : i + k]
            seq2 = tokens[i + k : i + 2 * k]
            seq3 = tokens[i + 2 * k : i + 3 * k]
            if seq1 == seq2 == seq3:
                if k == 1:
                    # check if 4th one also matches
                    if i + 4 * k <= n and tokens[i + 3 * k : i + 4 * k] == seq1:
                        return True
                else:
                    return True
                    
    # Also check for character-level loops (e.g. a single character like '9' or 'الاسم' repeating without spaces)
    # If a single non-space character is repeated 15+ times consecutively:
    cleaned_chars = text.strip()
    if re.search(r'([^0\s])\1{14,}', cleaned_chars):
        return True

    return False


class QwenLlmExtractionService:
    """Qari OCR + Qwen 2.5 3B Extraction and Validation Pipeline with PaddleOCR Fallback."""

    def __init__(self) -> None:
        settings = get_settings()
        self.url = settings.ollama_url.rstrip("/")
        self.model = "qwen2.5:3b"
        self.qari = QariOCRService()

    def ensure_initialized(self) -> None:
        self.qari.ensure_initialized()
        try:
            res = httpx.get(f"{self.url}/api/tags", timeout=5.0)
            if res.status_code == 200:
                models = res.json().get("models", [])
                any(m.get("name") == self.model or m.get("name", "").startswith(f"{self.model}:") for m in models)
        except Exception:
            pass

    def extract(self, file_path: str | Path) -> QwenLlmExtractionResult:
        started = time.perf_counter()
        file_path = Path(file_path)

        # 1. Run Qari OCR
        qari_start = time.perf_counter()
        qari_text = self.qari.extract_text(file_path)
        qari_ocr_time = time.perf_counter() - qari_start

        # Loop detection & Fallback to PaddleOCR
        is_fallback = False
        final_ocr_text = ""
        
        if not qari_text or detect_repetition_loop(qari_text):
            LOGGER.warning("Repetition loop or empty text detected in Qari OCR output for %s. Falling back to PaddleOCR.", file_path.name)
            fallback_start = time.perf_counter()
            final_ocr_text = self._run_paddle_ocr(file_path)
            qari_ocr_time += (time.perf_counter() - fallback_start)
            is_fallback = True
        else:
            final_ocr_text = deduplicate_tokens(qari_text)

        # Count pages from PDF if applicable
        page_count = 1
        if file_path.suffix.lower() == ".pdf":
            try:
                import fitz
                doc = fitz.open(str(file_path))
                page_count = len(doc)
            except Exception:
                pass

        # 2. Run Qwen 2.5 3B structured JSON extraction
        llm_start = time.perf_counter()
        llm_response = self._run_qwen_extraction(final_ocr_text)
        llm_time = time.perf_counter() - llm_start

        # 3. Perform Validation (Dates, Amounts, VAT, Math, Grounding & Confidence)
        val_start = time.perf_counter()
        validated_json = self._validate_and_score(llm_response, final_ocr_text)
        validation_time = time.perf_counter() - val_start

        processing_time = time.perf_counter() - started

        return QwenLlmExtractionResult(
            document_type="invoice",
            extracted_json=validated_json,
            raw_response=json.dumps(llm_response, ensure_ascii=False, indent=2),
            ocr_text=final_ocr_text,
            qari_ocr_text=qari_text,
            confidence=validated_json.get("_confidence", 0.0),
            page_count=page_count,
            ocr_time=qari_ocr_time,
            qari_ocr_time=qari_ocr_time,
            llm_time=llm_time,
            validation_time=validation_time,
            processing_time=processing_time,
        )

    def _run_paddle_ocr(self, file_path: Path) -> str:
        from services.paddle_ocr_service import PaddleOCRService
        from services.merge_extractor import _render_pages
        import numpy as np
        
        paddle_service = PaddleOCRService()
        paddle_service.ensure_initialized()
        paddle_service._init_ocr()
        
        pages = _render_pages(file_path)
        page_texts = []
        for index, page_img in enumerate(pages):
            width, height = page_img.size
            max_size = 800
            if max(width, height) > max_size:
                if width > height:
                    new_width = max_size
                    new_height = int(height * (max_size / width))
                else:
                    new_height = max_size
                    new_width = int(width * (max_size / height))
                page_img = page_img.resize((new_width, new_height), Image.Resampling.LANCZOS if hasattr(Image, "Resampling") else Image.LANCZOS)
                
            image_np = np.array(page_img.convert("RGB"))
            result = paddle_service._ocr_engine.ocr(image_np)
            lines = []
            if result and result[0]:
                rec_texts = result[0].get("rec_texts", [])
                lines = [str(text) for text in rec_texts if text is not None]
            page_texts.append("\n".join(lines))
        return "\n\n--- PAGE BREAK ---\n\n".join(page_texts)

    def _run_qwen_extraction(self, ocr_text: str) -> dict[str, Any]:
        prompt = (
            "You are a bilingual invoice metadata extractor. Analyze the input OCR text and extract the values into the required JSON schema.\n\n"
            "### RULES:\n"
            "- Extract values exactly as they appear in the text.\n"
            "- Extract vendor_name_ar and vendor_name_en independently. Populate both if both exist. Do not combine them.\n"
            "- Extract customer_name_ar and customer_name_en independently. Populate both if both exist. Do not combine them.\n"
            "- For vendor_name_en and customer_name_en, you MUST extract the official English names as they appear in the source text (especially top headers, e.g., 'ABC TRADING EST', 'XYZ LLC'). Do NOT translate the Arabic names into English (for example, do NOT translate 'مؤسسة الأمل' to 'HOPE FOUNDATION' or 'Hope'). If the official English name is not present, return \"\".\n"
            "- vendor_name must be the company issuing the invoice. customer_name must be the buyer/client. Do NOT swap them.\n"
            "- If customer_name is not clearly present, return \"\". Do NOT generate placeholders (e.g. 'Unnamed customer', 'the name').\n"
            "- Copy addresses verbatim. Do NOT translate addresses. If only Arabic address exists, return \"\" for address_en.\n"
            "- Never change names of cities (e.g., do not change 'الرياض' to 'مكة المكرمة').\n"
            "- Extract subtotal, tax_amount, total_amount as numbers. If not present, return null.\n"
            "- Output MUST be a valid JSON object matching the SCHEMA below. No markdown fences or explanations.\n\n"
            "### SCHEMA:\n"
            "{\n"
            "  \"document_number\": \"\",\n"
            "  \"vat_number\": \"\",\n"
            "  \"document_date\": \"\",\n"
            "  \"currency\": \"\",\n"
            "  \"vendor_name_ar\": \"\",\n"
            "  \"vendor_name_en\": \"\",\n"
            "  \"customer_name_ar\": \"\",\n"
            "  \"customer_name_en\": \"\",\n"
            "  \"address_ar\": \"\",\n"
            "  \"address_en\": \"\",\n"
            "  \"subtotal\": null,\n"
            "  \"tax_amount\": null,\n"
            "  \"total_amount\": null\n"
            "}\n\n"
            f"### OCR TEXT:\n{ocr_text}"
        )

        extracted_json = {field: ("" if "name" in field or "address" in field or field in ("document_number", "vat_number", "document_date", "currency") else None) for field in FINAL_COLUMNS}

        try:
            with httpx.Client(timeout=300.0) as client:
                res = client.post(
                    f"{self.url}/api/generate",
                    json={
                        "model": self.model,
                        "prompt": prompt,
                        "stream": False,
                        "format": "json",
                        "options": {
                            "temperature": 0.0,
                            "top_p": 0.9,
                            "seed": 42
                        }
                    }
                )
                if res.status_code == 200:
                    raw_resp = res.json().get("response", "").strip()
                    parsed = self._parse_json(raw_resp)
                    if parsed:
                        for key in extracted_json:
                            val = parsed.get(key)
                            if val is not None:
                                if isinstance(val, str):
                                    extracted_json[key] = clean_metadata_value(val.strip())
                                else:
                                    extracted_json[key] = val
                else:
                    LOGGER.error("Ollama API failed status=%d response=%s", res.status_code, res.text)
        except Exception as exc:
            LOGGER.error("Ollama Qwen 2.5 3B extraction failed: %s", exc)

        return extracted_json

    def _parse_json(self, text: str) -> dict[str, Any] | None:
        cleaned = text.strip()
        cleaned = re.sub(r"```(?:json)?", "", cleaned).replace("```", "").strip()
        try:
            parsed = json.loads(cleaned)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass
        match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
        if match:
            try:
                parsed = json.loads(match.group(0))
                if isinstance(parsed, dict):
                    return parsed
            except json.JSONDecodeError:
                pass
        return None

    def _normalize_text(self, val: Any) -> str:
        text = str(val or "").strip().lower()
        return re.sub(r"[\W_]+", "", text, flags=re.UNICODE)

    def _validate_and_score(self, extracted: dict[str, Any], ocr_text: str) -> dict[str, Any] | None:
        payload = {k: v for k, v in extracted.items()}
        
        # Relocate misplaced values based on language
        for base in ("vendor_name", "customer_name", "address"):
            ar_val = payload.get(f"{base}_ar")
            en_val = payload.get(f"{base}_en")
            if ar_val:
                ar_ar_cnt, ar_en_cnt = count_chars_by_language(ar_val)
                if ar_en_cnt > ar_ar_cnt and ar_en_cnt > 0:
                    if not en_val:
                        payload[f"{base}_en"] = ar_val
                        payload[f"{base}_ar"] = ""
                        LOGGER.info(f"Relocated mostly English value for {base} from Arabic to English field: '{ar_val}'")
            # re-read after possible modification
            ar_val = payload.get(f"{base}_ar")
            en_val = payload.get(f"{base}_en")
            if en_val:
                en_ar_cnt, en_en_cnt = count_chars_by_language(en_val)
                if en_ar_cnt > en_en_cnt and en_ar_cnt > 0:
                    if not ar_val:
                        payload[f"{base}_ar"] = en_val
                        payload[f"{base}_en"] = ""
                        LOGGER.info(f"Relocated mostly Arabic value for {base} from English to Arabic field: '{en_val}'")

        # 1. Recover short company names
        for field in ("vendor_name_ar", "vendor_name_en", "customer_name_ar", "customer_name_en"):
            val = payload.get(field)
            if val:
                recovered_val = recover_company_name(val, ocr_text)
                if recovered_val != val:
                    LOGGER.info(f"Company name recovery for {field}: '{val}' -> '{recovered_val}'")
                    print(f"Company name recovery for {field}: '{val}' -> '{recovered_val}'", flush=True)
                    payload[field] = recovered_val

        # 2. Recover incomplete addresses
        for field in ("address_ar", "address_en"):
            val = payload.get(field)
            if val:
                recovered_val = recover_address(val, ocr_text)
                if recovered_val != val:
                    LOGGER.info(f"Address recovery for {field}: '{val}' -> '{recovered_val}'")
                    print(f"Address recovery for {field}: '{val}' -> '{recovered_val}'", flush=True)
                    payload[field] = recovered_val

        # 3. Validate languages, apply rejections and overrides
        forced_confidences = {}
        arabic_fields = ["vendor_name_ar", "vendor_name_en", "customer_name_ar", "customer_name_en", "address_ar", "address_en"]
        
        for field in arabic_fields:
            val = payload.get(field)
            if not val:
                continue
                
            ar_cnt, en_cnt = count_chars_by_language(val)
            det_lang = detect_field_language(val)
            print(f"Detected language for field {field}: {det_lang} (Arabic: {ar_cnt}, English: {en_cnt})", flush=True)
            LOGGER.info(f"Detected language for field {field}: {det_lang} (Arabic: {ar_cnt}, English: {en_cnt})")
            
            is_valid = True
            reject_reason = ""
            
            if field == "vendor_name_ar":
                if ar_cnt == 0 or (en_cnt > 0 and en_cnt > ar_cnt):
                    is_valid = False
                    reject_reason = "vendor_name_ar is mostly English"
            elif field == "vendor_name_en":
                if en_cnt == 0 or (ar_cnt > 0 and ar_cnt > en_cnt):
                    is_valid = False
                    reject_reason = "vendor_name_en is mostly Arabic"
            elif field == "address_ar":
                if ar_cnt == 0 or (en_cnt > 0 and en_cnt > ar_cnt):
                    is_valid = False
                    reject_reason = "address_ar is mostly English"
            elif field == "address_en":
                if en_cnt == 0 or (ar_cnt > 0 and ar_cnt > en_cnt):
                    is_valid = False
                    reject_reason = "address_en is mostly Arabic"
            elif field == "customer_name_ar":
                if ar_cnt == 0 or (en_cnt > 0 and en_cnt > ar_cnt):
                    is_valid = False
                    reject_reason = "customer_name_ar is mostly English"
                elif is_invalid_customer_name(val):
                    is_valid = False
                    reject_reason = "customer_name_ar contains invalid keywords or layout"
            elif field == "customer_name_en":
                if en_cnt == 0 or (ar_cnt > 0 and ar_cnt > en_cnt):
                    is_valid = False
                    reject_reason = "customer_name_en is mostly Arabic"
                elif is_invalid_customer_name(val):
                    is_valid = False
                    reject_reason = "customer_name_en contains invalid keywords or layout"

            # Check general validations (e.g. not invoice titles, total amounts etc.)
            if is_valid and not validate_field_value(field, val):
                is_valid = False
                reject_reason = f"value '{val}' did not pass general validation check for {field}"

            if not is_valid:
                print(f"Rejected value '{val}' for field {field}: {reject_reason}", flush=True)
                LOGGER.warning(f"Rejected value '{val}' for field {field}: {reject_reason}")
                
                # Perform company name recovery from OCR text if it's a vendor name field
                recovered = ""
                if field == "vendor_name_ar":
                    recovered = find_arabic_company_name(ocr_text)
                elif field == "vendor_name_en":
                    recovered = find_english_company_name(ocr_text)
                    
                if recovered:
                    print(f"Recovered replacement '{recovered}' for field {field} from OCR text", flush=True)
                    payload[field] = recovered
                    new_ar, new_en = count_chars_by_language(recovered)
                    if field == "vendor_name_ar" and new_ar > new_en:
                        forced_confidences[field] = 0.95
                    elif field == "vendor_name_en" and new_en > new_ar:
                        forced_confidences[field] = 0.95
                    else:
                        forced_confidences[field] = 0.0
                else:
                    payload[field] = ""
                    forced_confidences[field] = 0.0

        # Fallback/refinement using deterministic NumericExtractor for empty/missing numeric/metadata fields
        from services.numeric_extractor import NumericExtractor
        num_extractor = NumericExtractor()
        
        # 1. Amounts fallback
        if payload.get("subtotal") in (None, "") or payload.get("tax_amount") in (None, "") or payload.get("total_amount") in (None, ""):
            det_amounts = num_extractor._extract_amounts_via_regex(ocr_text)
            if det_amounts.get("total_amount") is not None:
                if payload.get("subtotal") in (None, ""):
                    payload["subtotal"] = det_amounts.get("subtotal")
                if payload.get("tax_amount") in (None, ""):
                    payload["tax_amount"] = det_amounts.get("tax_amount")
                if payload.get("total_amount") in (None, ""):
                    payload["total_amount"] = det_amounts.get("total_amount")
                    
        # 2. Document number fallback
        if not payload.get("document_number"):
            det_doc_num = num_extractor._extract_document_number(ocr_text)
            if det_doc_num:
                payload["document_number"] = det_doc_num
                
        # 3. VAT number fallback
        if not payload.get("vat_number"):
            det_vat = num_extractor._extract_vat_number(ocr_text)
            if det_vat:
                payload["vat_number"] = det_vat
                
        # 4. Document date fallback
        if not payload.get("document_date"):
            det_date = num_extractor._extract_document_date(ocr_text)
            if det_date:
                payload["document_date"] = det_date
                
        # 5. Currency fallback
        if not payload.get("currency"):
            det_curr = num_extractor._extract_currency(ocr_text)
            if det_curr:
                payload["currency"] = det_curr

        issues: list[dict[str, str]] = []

        # 1. Validate & Normalize Dates
        raw_date = payload.get("document_date")
        normalized_date, date_issues = self._validate_date(raw_date)
        payload["document_date"] = normalized_date
        issues.extend(date_issues)

        # 2. Validate & Normalize Amounts
        subtotal, sub_issues = self._parse_amount(payload.get("subtotal"), "subtotal")
        tax_amount, tax_issues = self._parse_amount(payload.get("tax_amount"), "tax_amount")
        total_amount, total_issues = self._parse_amount(payload.get("total_amount"), "total_amount")
        
        payload["subtotal"] = subtotal
        payload["tax_amount"] = tax_amount
        payload["total_amount"] = total_amount
        
        issues.extend(sub_issues)
        issues.extend(tax_issues)
        issues.extend(total_issues)

        # 3. Validate VAT format
        vat_num = payload.get("vat_number")
        if vat_num:
            vat_issues = self._validate_vat(vat_num)
            issues.extend(vat_issues)

        # 4. Math check
        math_issues = self._check_math(subtotal, tax_amount, total_amount)
        issues.extend(math_issues)

        # 5. Grounding check & Confidence Score
        confidences = {field: 0.0 for field in FINAL_COLUMNS}
        norm_ocr = self._normalize_text(ocr_text)

        for field in FINAL_COLUMNS:
            val = payload.get(field)
            if val in (None, ""):
                continue

            # Grounding logic
            is_grounded = False
            if field in ("subtotal", "tax_amount", "total_amount"):
                clean_digits = re.sub(r"\D", "", f"{float(val):.2f}")
                clean_digits_short = re.sub(r"\D", "", f"{float(val):.0f}")
                if (clean_digits and clean_digits in norm_ocr) or (clean_digits_short and clean_digits_short in norm_ocr):
                    is_grounded = True
            elif field == "document_date":
                date_str = str(val)
                parts = re.findall(r"\d+", date_str)
                if parts and all(part in norm_ocr for part in parts):
                    is_grounded = True
            elif field in ("vendor_name_ar", "vendor_name_en", "customer_name_ar", "customer_name_en", "address_ar", "address_en"):
                norm_val = self._normalize_text(val)
                fuzzy_score = fuzz.partial_ratio(norm_val, norm_ocr)
                if fuzzy_score >= 85.0:
                    is_grounded = True
            else:
                norm_val = self._normalize_text(val)
                if norm_val in norm_ocr:
                    is_grounded = True

            if is_grounded:
                confidences[field] = 1.0
            else:
                confidences[field] = 0.0
                issues.append({
                    "field": field,
                    "message": f"Field '{field}' value '{val}' is not grounded in the OCR text.",
                    "severity": "warning"
                })

        # Override confidences/values for rejected fields
        for field, conf in forced_confidences.items():
            confidences[field] = conf
            if conf == 0.0:
                payload[field] = ""

        # Calculate weighted confidence score
        base_confidence = sum(confidences[f] * FIELD_WEIGHTS[f] for f in FINAL_COLUMNS)
        
        # Penalties
        penalties = 0.0
        for issue in issues:
            if issue["severity"] == "error":
                penalties += 0.15
            elif issue["severity"] == "warning":
                penalties += 0.05
        
        final_confidence = max(0.0, min(1.0, base_confidence - penalties))
        payload["_confidences"] = confidences
        payload["_validation"] = {
            "valid": not any(issue["severity"] == "error" for issue in issues),
            "issues": issues,
        }
        payload["_confidence"] = round(final_confidence, 2)

        return payload

    def _validate_date(self, date_str: Any) -> tuple[str, list[dict[str, str]]]:
        date_str = str(date_str or "").strip()
        if not date_str:
            return "", []

        # Try YYYY-MM-DD pattern
        match_y = re.match(r"^(\d{4})[-/\.](\d{1,2})[-/\.](\d{1,2})$", date_str)
        if match_y:
            y, m, d = int(match_y.group(1)), int(match_y.group(2)), int(match_y.group(3))
            if 1 <= m <= 12 and 1 <= d <= 31:
                return f"{y:04d}-{m:02d}-{d:02d}", []

        # Try DD-MM-YYYY pattern
        match_d = re.match(r"^(\d{1,2})[-/\.](\d{1,2})[-/\.](\d{4})$", date_str)
        if match_d:
            d, m, y = int(match_d.group(1)), int(match_d.group(2)), int(match_d.group(3))
            if 1 <= m <= 12 and 1 <= d <= 31:
                return f"{y:04d}-{m:02d}-{d:02d}", []

        issues = [{
            "field": "document_date",
            "message": f"Document date '{date_str}' is not in YYYY-MM-DD or DD-MM-YYYY format.",
            "severity": "warning"
        }]
        return date_str, issues

    def _parse_amount(self, value: Any, field_name: str) -> tuple[float | None, list[dict[str, str]]]:
        if value in (None, ""):
            return None, []
        if isinstance(value, (int, float)):
            return float(value), []

        val_str = str(value).strip().replace(" ", "")
        val_str = re.sub(r"(?i)[a-z]+", "", val_str)
        val_str = val_str.replace("$", "").replace("€", "").replace("£", "")
        val_str = val_str.replace(",", "")
        
        try:
            return float(val_str), []
        except ValueError:
            return None, [{
                "field": field_name,
                "message": f"Failed to parse amount '{value}' to a valid number.",
                "severity": "warning"
            }]

    def _validate_vat(self, vat_number: str) -> list[dict[str, str]]:
        digits = re.sub(r"\D", "", str(vat_number or ""))
        if not digits:
            return []

        issues = []
        if len(digits) != 15:
            issues.append({
                "field": "vat_number",
                "message": f"VAT number '{vat_number}' is not 15 digits (got {len(digits)} digits).",
                "severity": "warning"
            })
        if not digits.startswith("3"):
            issues.append({
                "field": "vat_number",
                "message": f"VAT number '{vat_number}' does not match KSA format (must start with 3).",
                "severity": "warning"
            })
        return issues

    def _check_math(self, subtotal: float | None, tax_amount: float | None, total_amount: float | None) -> list[dict[str, str]]:
        if subtotal is None or tax_amount is None or total_amount is None:
            return []
        
        diff = abs(subtotal + tax_amount - total_amount)
        if diff >= 0.05:
            return [{
                "field": "total_amount",
                "message": f"Math check failed: Subtotal ({subtotal}) + Tax Amount ({tax_amount}) = {subtotal + tax_amount:.2f}, but Total Amount is {total_amount}.",
                "severity": "error"
            }]
        return []
