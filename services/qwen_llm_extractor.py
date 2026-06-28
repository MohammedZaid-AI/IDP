from __future__ import annotations

import json
import logging
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx

from services.settings import get_settings
from services.qari_ocr_service import QariOCRService

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


def normalize_for_check(text: str) -> str:
    if not text:
        return ""
    text = text.lower()
    return re.sub(r'[\W_]+', '', text, flags=re.UNICODE)


def amount_exists_in_ocr(val: float, ocr_text: str) -> bool:
    clean_ocr = normalize_for_check(ocr_text)
    clean_digits = re.sub(r'\D', '', f"{val:.2f}")
    clean_digits_short = re.sub(r'\D', '', f"{val:.0f}")
    return (clean_digits in clean_ocr) or (clean_digits_short in clean_ocr)


def normalize_currency(val: Any) -> str:
    if not val:
        return ""
    val_str = str(val).strip().lower()
    if any(term in val_str for term in ("sar", "riy", "ريال", "ر.س", "sr")):
        return "SAR"
    return str(val).strip()


def is_valid_date(date_str: str) -> bool:
    if not date_str:
        return False
    for fmt in (
        "%Y-%m-%d", "%d-%m-%Y", "%Y/%m/%d", "%d/%m/%Y", 
        "%m/%d/%Y", "%Y.%m.%d", "%d.%m.%Y", "%Y-%m-%dT%H:%M:%S"
    ):
        try:
            time.strptime(date_str, fmt)
            return True
        except ValueError:
            pass
    return False


def parse_float_amount(value: Any) -> float | None:
    if value in (None, ""):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    try:
        val_str = str(value).strip().replace(" ", "")
        val_str = re.sub(r"(?i)[a-z]+", "", val_str)
        val_str = val_str.replace("$", "").replace("€", "").replace("£", "").replace(",", "")
        return float(val_str)
    except ValueError:
        return None


class QwenLlmExtractionService:
    """Qari OCR + Qwen 2.5 3B Extraction and Validation Pipeline."""

    def __init__(self) -> None:
        settings = get_settings()
        self.url = settings.ollama_url.rstrip("/")
        self.model = "qwen2.5:3b"
        self.qari = QariOCRService()

    @property
    def is_available(self) -> bool:
        try:
            res = httpx.get(f"{self.url}/api/tags", timeout=3.0)
            if res.status_code == 200:
                models = res.json().get("models", [])
                return any(m.get("name") == self.model or m.get("name", "").startswith(f"{self.model}:") for m in models)
        except Exception:
            pass
        return False

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
        ocr_time = time.perf_counter() - qari_start

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
        extracted_json, llm_response_text, prompt = self._run_qwen_extraction(qari_text)
        llm_time = time.perf_counter() - llm_start

        # 3. Perform Validation and Confidence Scoring
        val_start = time.perf_counter()
        validated_json = self._validate_and_score(extracted_json, qari_text, llm_response_text, prompt, started)
        validation_time = time.perf_counter() - val_start

        processing_time = time.perf_counter() - started

        return QwenLlmExtractionResult(
            document_type="invoice",
            extracted_json=validated_json,
            raw_response=llm_response_text,
            ocr_text=qari_text,
            qari_ocr_text=qari_text,
            confidence=validated_json.get("_confidence", 0.0),
            page_count=page_count,
            ocr_time=ocr_time,
            qari_ocr_time=ocr_time,
            llm_time=llm_time,
            validation_time=validation_time,
            processing_time=processing_time,
        )

    def _run_qwen_extraction(self, ocr_text: str) -> tuple[dict[str, Any], str, str]:
        prompt = f"""You are a highly accurate invoice extraction engine.

Your job is to extract structured information from OCR text.

You MUST return ONLY valid JSON.
Never explain.
Never use markdown.
Never include comments.
Never include code blocks.
Never return anything except the JSON object.

GENERAL RULES:
The OCR text may contain:
- Arabic
- English
- Mixed Arabic and English
- Tables
- Product descriptions
- Headers
- Footers
- Phone numbers
- VAT numbers
- CR numbers
- PO numbers

Your job is to identify ONLY the requested invoice entities.
Never guess.
If uncertain, return an empty string or null.

VERY IMPORTANT:
For every field, return ONLY the value.
Never include labels.
Never include neighbouring lines.
Never include surrounding paragraphs.

Example:
OCR:
Vendor Name
ABC Trading Company
PO Box 123

Correct:
"vendor_name_en": "ABC Trading Company"

Wrong:
"vendor_name_en": "Vendor Name\nABC Trading Company\nPO Box 123"

DOCUMENT NUMBER:
Choose ONLY the actual invoice number.
Ignore:
- Revenue Number
- Customer Number
- CR Number
- PO Number
- Delivery Number
- Reference Number
- Serial Number
- Item Code
- Product Code
If the invoice number is empty on the document, return "".
Never guess.

VENDOR:
Return ONLY the company name.
Do NOT include:
- Address
- Phone
- Fax
- VAT
- Email
- Website
- PO Box

Correct: ABC Trading Company
Wrong:
ABC Trading Company
PO Box 123
Riyadh
Saudi Arabia

CUSTOMER:
Return ONLY the customer name.
Never include:
- Address
- PO Box
- VAT
- Reference
- Invoice Number

ADDRESS:
Return ONLY the address.
Do not include:
- Vendor name
- Customer name
- Phone
- Email
- VAT
- Invoice Number

VAT NUMBER:
Return ONLY the VAT registration number.
Never return:
- CR
- PO
- Invoice Number

DATE:
Return ONLY the invoice date.
Prefer:
- Invoice Date
- Issue Date
- Tax Invoice Date
Do NOT use:
- Delivery Date
- Supply Date
- Due Date
unless the invoice date is missing.

AMOUNTS:
Extract ONLY:
- subtotal
- tax_amount
- total_amount
Ignore:
- Unit Price
- Quantity
- Line Total
- Product Total
- Discount %

LANGUAGE:
If the text is Arabic, store it in the Arabic field.
If the text is English, store it in the English field.
Never translate.
Never duplicate Arabic into English.
Never duplicate English into Arabic.

NEGATIVE EXAMPLES:

Wrong vendor_name:
ABC Trading
PO Box 123
Riyadh
Correct vendor_name:
ABC Trading

Wrong document_number:
Invoice Number
PO Box 123
Correct document_number:
736

Wrong address:
ABC Trading
PO Box
VAT Number
Phone
Correct address:
PO Box 123
Riyadh
Saudi Arabia

OUTPUT FORMAT:
Return EXACTLY a JSON object with this structure:
{{
    "document_number": "",
    "vat_number": "",
    "document_date": "",
    "currency": "",
    "vendor_name_ar": "",
    "vendor_name_en": "",
    "customer_name_ar": "",
    "customer_name_en": "",
    "address_ar": "",
    "address_en": "",
    "subtotal": null,
    "tax_amount": null,
    "total_amount": null
}}

OCR TEXT:
{ocr_text}"""

        extracted_json = {field: ("" if "name" in field or "address" in field or field in ("document_number", "vat_number", "document_date", "currency") else None) for field in FINAL_COLUMNS}
        raw_response = ""

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
                        }
                    }
                )
                if res.status_code == 200:
                    raw_response = res.json().get("response", "").strip()
                    parsed = self._parse_json(raw_response)
                    if parsed:
                        for key in extracted_json:
                            val = parsed.get(key)
                            if val is not None:
                                if isinstance(val, str):
                                    extracted_json[key] = val.strip()
                                else:
                                    extracted_json[key] = val
                else:
                    LOGGER.error("Ollama API failed status=%d response=%s", res.status_code, res.text)
        except Exception as exc:
            LOGGER.error("Ollama Qwen 2.5 3B extraction failed: %s", exc)

        return extracted_json, raw_response, prompt

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

    def _validate_and_score(
        self, 
        extracted: dict[str, Any], 
        ocr_text: str, 
        llm_response: str, 
        prompt: str, 
        started_time: float
    ) -> dict[str, Any]:
        payload = {k: v for k, v in extracted.items()}
        issues = []
        penalties = 0.0

        # Normalization (Currency)
        if "currency" in payload and payload["currency"]:
            normalized_curr = normalize_currency(payload["currency"])
            payload["currency"] = normalized_curr

        # 1. Invoice Number Check
        doc_num = payload.get("document_number")
        if not doc_num:
            issues.append({
                "field": "document_number",
                "message": "Invoice number is missing or empty.",
                "severity": "error"
            })
            penalties += 0.2
        else:
            norm_doc = normalize_for_check(doc_num)
            norm_ocr = normalize_for_check(ocr_text)
            if norm_doc not in norm_ocr:
                issues.append({
                    "field": "document_number",
                    "message": f"Invoice number '{doc_num}' does not exist in OCR text.",
                    "severity": "error"
                })
                penalties += 0.2

        # 2. VAT Number Check
        vat_num = payload.get("vat_number")
        if not vat_num:
            issues.append({
                "field": "vat_number",
                "message": "VAT number is missing or empty.",
                "severity": "warning"
            })
            penalties += 0.15
        else:
            norm_vat = normalize_for_check(vat_num)
            norm_ocr = normalize_for_check(ocr_text)
            if norm_vat not in norm_ocr:
                issues.append({
                    "field": "vat_number",
                    "message": f"VAT number '{vat_num}' does not exist in OCR text.",
                    "severity": "warning"
                })
                penalties += 0.15

        # 3. Other fields existence check
        for field in ("vendor_name_ar", "vendor_name_en", "customer_name_ar", "customer_name_en", "address_ar", "address_en", "currency"):
            val = payload.get(field)
            if val:
                norm_val = normalize_for_check(str(val))
                norm_ocr = normalize_for_check(ocr_text)
                if norm_val not in norm_ocr:
                    issues.append({
                        "field": field,
                        "message": f"Field '{field}' value '{val}' is not present in OCR text.",
                        "severity": "warning"
                    })
                    penalties += 0.05

        # 4. Date validation
        doc_date = payload.get("document_date")
        if not doc_date:
            issues.append({
                "field": "document_date",
                "message": "Document date is missing or empty.",
                "severity": "warning"
            })
            penalties += 0.15
        else:
            if not is_valid_date(doc_date):
                issues.append({
                    "field": "document_date",
                    "message": f"Document date '{doc_date}' is not a valid date.",
                    "severity": "warning"
                })
                penalties += 0.15
            
            # Grounding check of date numbers in OCR
            date_digits = "".join(re.findall(r"\d+", doc_date))
            if date_digits:
                norm_ocr = normalize_for_check(ocr_text)
                if not any(part in norm_ocr for part in re.findall(r"\d+", doc_date)):
                    issues.append({
                        "field": "document_date",
                        "message": f"Date digits from '{doc_date}' are not grounded in OCR text.",
                        "severity": "warning"
                    })
                    penalties += 0.05

        # 5. Money validation
        subtotal = parse_float_amount(payload.get("subtotal"))
        tax_amount = parse_float_amount(payload.get("tax_amount"))
        total_amount = parse_float_amount(payload.get("total_amount"))

        # Grounding checks for amounts
        for field, amt in (("subtotal", subtotal), ("tax_amount", tax_amount), ("total_amount", total_amount)):
            if amt is not None:
                if not amount_exists_in_ocr(amt, ocr_text):
                    issues.append({
                        "field": field,
                        "message": f"Amount '{amt}' for '{field}' not found in OCR text.",
                        "severity": "warning"
                    })
                    penalties += 0.05
            else:
                issues.append({
                    "field": field,
                    "message": f"Amount field '{field}' is missing or empty.",
                    "severity": "warning"
                })
                penalties += 0.05

        # Math check
        if subtotal is not None and tax_amount is not None and total_amount is not None:
            if abs((subtotal + tax_amount) - total_amount) > 0.05:
                issues.append({
                    "field": "total_amount",
                    "message": f"Math check failed: subtotal ({subtotal}) + tax ({tax_amount}) = {subtotal+tax_amount:.2f}, but total is {total_amount}.",
                    "severity": "error"
                })
                penalties += 0.2

        # Final score
        final_confidence = max(0.0, round(1.0 - penalties, 2))

        payload["_confidence"] = final_confidence
        validation_results = {
            "valid": len([i for i in issues if i["severity"] == "error"]) == 0,
            "issues": issues,
        }
        payload["_validation"] = validation_results

        processing_time = time.perf_counter() - started_time

        # Print debug logging
        print("\n================ INVOICE EXTRACTION DEBUG LOGS ================", flush=True)
        print(f"OCR Length: {len(ocr_text)} characters", flush=True)
        print(f"LLM Prompt Length: {len(prompt)} characters", flush=True)
        print(f"LLM Response:\n{llm_response}", flush=True)
        print(f"Parsed JSON:\n{json.dumps(extracted, ensure_ascii=False, indent=2)}", flush=True)
        print(f"Validation Results:\n{json.dumps(validation_results, ensure_ascii=False, indent=2)}", flush=True)
        print(f"Processing Time: {processing_time:.4f}s", flush=True)
        print("===============================================================\n", flush=True)

        return payload
