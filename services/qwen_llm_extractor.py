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
    arabic_digits = "٠١٢٣٤٥٦٧٨٩"
    persian_digits = "۰۱۲۳۴۵۶۷٨٩"
    for i in range(10):
        text = text.replace(arabic_digits[i], str(i)).replace(persian_digits[i], str(i))
    return re.sub(r'[\W_]+', '', text, flags=re.UNICODE)


def normalize_number_str(s: str) -> str:
    # 1. Convert Arabic and Persian digits to English digits
    arabic_digits = "٠١٢٣٤٥٦٧٨٩"
    persian_digits = "۰۱۲۳۴۵۶۷٨٩"
    for i in range(10):
        s = s.replace(arabic_digits[i], str(i)).replace(persian_digits[i], str(i))
    
    # 2. Normalize Arabic decimal comma ٫
    s = s.replace("٫", ".")
    
    # 3. Remove spaces and other whitespace
    s = re.sub(r'\s+', '', s)
    
    # 4. Check for both period and comma
    if "." in s and "," in s:
        dot_idx = s.rfind(".")
        comma_idx = s.rfind(",")
        if dot_idx < comma_idx:
            # Period is thousands, comma is decimal (e.g. 28.100,31)
            s = s.replace(".", "")
            s = s.replace(",", ".")
        else:
            # Comma is thousands, period is decimal (e.g. 28,100.31)
            s = s.replace(",", "")
    elif "," in s:
        # Only comma present. Determine if thousands or decimal.
        if re.search(r',\d{1,2}$', s):
            s = s.replace(",", ".")
        else:
            s = s.replace(",", "")
            
    return s


def normalize_number(val: Any) -> float | None:
    if val is None or val == "":
        return None
    if isinstance(val, (int, float)):
        return float(val)
    try:
        s = str(val).strip()
        s = normalize_number_str(s)
        # Keep only digits, minus, and period
        s = re.sub(r'[^\d.-]', '', s)
        return float(s)
    except Exception:
        return None


def amount_exists_in_ocr(val: float, ocr_text: str) -> bool:
    # Find all potential number strings in OCR
    pattern = r'[\d\s.,٫\u0660-\u0669\u06f0-\u06f9]+'
    candidates = re.findall(pattern, ocr_text)
    target = round(val, 2)
    for cand in candidates:
        norm = normalize_number(cand)
        if norm is not None:
            if abs(round(norm, 2) - target) < 0.01:
                return True
    return False


def ocr_contains_field(field_name: str, ocr_text: str) -> bool:
    # Vendor is always present on an invoice, so we bypass checking keywords
    if field_name in ("vendor_name_ar", "vendor_name_en"):
        return True

    ocr_lower = ocr_text.lower()
    # Normalize Arabic digits in OCR for matching
    arabic_digits = "٠١٢٣٤٥٦٧٨٩"
    persian_digits = "۰۱۲۳۴۵۶۷٨٩"
    for i in range(10):
        ocr_lower = ocr_lower.replace(arabic_digits[i], str(i)).replace(persian_digits[i], str(i))

    keywords = {
        "document_number": [
            "invoice no", "invoice number", "inv no", "inv number", "invoice#", "invoice #",
            "فاتورة رقم", "رقم الفاتورة", "رقم", "رقم المستند"
        ],
        "vat_number": [
            "vat no", "vat number", "vat id", "الرقم الضريبي", "الرقم التعريفي الضريبي", "tin",
            "tax registration", "tax no", "tax number", "رقم التسجيل الضريبي"
        ],
        "document_date": [
            "date", "issue date", "invoice date", "التاريخ", "تاريخ الفاتورة", "تاريخ الاصدار", "تاريخ"
        ],
        "currency": [
            "sar", "riy", "ريال", "ر.س", "sr", "currency", "العملة"
        ],
        "subtotal": [
            "subtotal", "sub-total", "net amount", "before vat", "before tax", "الاجمالي قبل", "المجموع قبل",
            "المبلغ الخاضع للضريبة"
        ],
        "tax_amount": [
            "vat", "tax", "value added tax", "الضريبة", "قيمة الضريبة", "مبلغ الضريبة"
        ],
        "total_amount": [
            "total", "grand total", "total amount", "net total", "amount due", "المجموع", "الاجمالي", "الصافي",
            "المبلغ المستحق"
        ],
        "customer_name_ar": [
            "customer", "bill to", "sold to", "client", "العميل", "المشتري", "السادة", "إلى"
        ],
        "customer_name_en": [
            "customer", "bill to", "sold to", "client", "العميل", "المشتري", "السادة", "to"
        ],
        "address_ar": [
            "address", "location", "العنوان", "الموقع", "ص.ب"
        ],
        "address_en": [
            "address", "location", "العنوان", "الموقع", "p.o.box", "p.o. box"
        ],
        "purchase_order": [
            "po #", "po no", "po number", "purchase order", "طلب شراء", "p.o", "p.o."
        ],
        "payment_terms": [
            "payment terms", "payment term", "شروط الدفع", "تاريخ الاستحقاق", "due date"
        ],
        "customer_vat": [
            "customer vat", "customer's vat", "الرقم الضريبي للمشتري", "الرقم الضريبي للعميل"
        ]
    }
    
    if field_name not in keywords:
        field_clean = field_name.replace("_", " ")
        return field_clean in ocr_lower
        
    return any(kw in ocr_lower for kw in keywords[field_name])


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
        self.model = "gemma4:e4b"
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
        prompt = f"""You are an expert financial document analyst.

You are given the OCR transcription of a business document.

Read the document exactly as a human accountant would.

Understand the document.

Identify the important business information that should be stored in a financial document management system.

Ignore decorative text, repeated OCR artefacts, page layout information, HTML tags, OCR metadata, and product table formatting.

Return the structured information.

Determine:
* What type of document this is.
* Which information is important.
* Which information should be ignored.

You MUST return ONLY valid JSON matching the canonical schema below.
Never explain.
Never use markdown.
Never include comments.
Never include code blocks.
Never return anything except the JSON object.

CANONICAL SCHEMA:
{{
  "document_type": "",
  "document": {{
    "number": "",
    "date": "",
    "currency": ""
  }},
  "vendor": {{
    "name_ar": "",
    "name_en": "",
    "vat_number": "",
    "address_ar": "",
    "address_en": ""
  }},
  "customer": {{
    "name_ar": "",
    "name_en": "",
    "address_ar": "",
    "address_en": ""
  }},
  "financials": {{
    "subtotal": null,
    "tax_amount": null,
    "total_amount": null
  }},
  "metadata": {{
    "purchase_order": "",
    "reference_number": "",
    "payment_terms": "",
    "notes": ""
  }}
}}

OCR TEXT:
{ocr_text}"""

        extracted_json = {field: ("" if "name" in field or "address" in field or field in ("document_number", "vat_number", "document_date", "currency") else None) for field in FINAL_COLUMNS}
        extracted_json.update({
            "document_type": "invoice",
            "document": {
                "number": "",
                "date": "",
                "currency": ""
            },
            "vendor": {
                "name_ar": "",
                "name_en": "",
                "vat_number": "",
                "address_ar": "",
                "address_en": ""
            },
            "customer": {
                "name_ar": "",
                "name_en": "",
                "address_ar": "",
                "address_en": ""
            },
            "financials": {
                "subtotal": None,
                "tax_amount": None,
                "total_amount": None
            },
            "metadata": {
                "purchase_order": "",
                "reference_number": "",
                "payment_terms": "",
                "notes": ""
            }
        })
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
                        # Copy the canonical schema keys directly to extracted_json
                        extracted_json["document_type"] = parsed.get("document_type") or "invoice"
                        extracted_json["document"] = parsed.get("document") or {}
                        extracted_json["vendor"] = parsed.get("vendor") or {}
                        extracted_json["customer"] = parsed.get("customer") or {}
                        extracted_json["financials"] = parsed.get("financials") or {}
                        extracted_json["metadata"] = parsed.get("metadata") or {}
                        
                        # Populate flat fields for backward compatibility
                        doc_info = extracted_json["document"]
                        vendor_info = extracted_json["vendor"]
                        customer_info = extracted_json["customer"]
                        financial_info = extracted_json["financials"]
                        
                        def get_str(d, k):
                            if not isinstance(d, dict):
                                return ""
                            v = d.get(k)
                            return str(v).strip() if v is not None else ""
                            
                        extracted_json["document_number"] = get_str(doc_info, "number")
                        extracted_json["vat_number"] = get_str(vendor_info, "vat_number")
                        extracted_json["document_date"] = get_str(doc_info, "date")
                        extracted_json["currency"] = get_str(doc_info, "currency")
                        
                        extracted_json["vendor_name_ar"] = get_str(vendor_info, "name_ar")
                        extracted_json["vendor_name_en"] = get_str(vendor_info, "name_en")
                        extracted_json["address_ar"] = get_str(vendor_info, "address_ar")
                        extracted_json["address_en"] = get_str(vendor_info, "address_en")
                        
                        extracted_json["customer_name_ar"] = get_str(customer_info, "name_ar")
                        extracted_json["customer_name_en"] = get_str(customer_info, "name_en")
                        
                        if isinstance(financial_info, dict):
                            extracted_json["subtotal"] = parse_float_amount(financial_info.get("subtotal"))
                            extracted_json["tax_amount"] = parse_float_amount(financial_info.get("tax_amount"))
                            extracted_json["total_amount"] = parse_float_amount(financial_info.get("total_amount"))
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
            if "document" in payload and isinstance(payload["document"], dict):
                payload["document"]["currency"] = normalized_curr

        fields_to_validate = [
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
            "purchase_order",
            "customer_vat",
            "payment_terms"
        ]

        def get_field_value(f: str) -> Any:
            if f in payload:
                return payload[f]
            if f == "purchase_order":
                return payload.get("metadata", {}).get("purchase_order")
            if f == "payment_terms":
                return payload.get("metadata", {}).get("payment_terms")
            if f == "customer_vat":
                return payload.get("customer", {}).get("vat_number")
            return None

        field_states = {}

        print("\n================ INVOICE VALIDATION RUN ================", flush=True)

        for field in fields_to_validate:
            val = get_field_value(field)
            exists_in_ocr = ocr_contains_field(field, ocr_text)
            
            is_empty = val is None or str(val).strip() in ("", "null", "None")
            
            if not exists_in_ocr:
                state = "NOT_PRESENT_IN_SOURCE"
                validation_status = "NOT_PRESENT_IN_SOURCE"
                field_states[field] = state
                print(f"Field: {field}")
                print("OCR contains field: NO")
                print("Validation: NOT_PRESENT_IN_SOURCE")
                print("", flush=True)
                continue
                
            # Field exists in OCR
            if is_empty:
                state = "NOT_EXTRACTED"
                validation_status = "FAIL"
                field_states[field] = state
                
                severity = "error" if field in ("document_number", "total_amount") else "warning"
                issues.append({
                    "field": field,
                    "message": f"Field '{field}' exists in OCR but was not extracted.",
                    "severity": severity
                })
                
                # Penalize confidence
                if field == "document_number":
                    penalties += 0.2
                elif field in ("vat_number", "document_date"):
                    penalties += 0.15
                else:
                    penalties += 0.05
                    
                print(f"Field: {field}")
                print("OCR contains field: YES")
                print("OCR normalized value: Present in OCR")
                print("LLM normalized value: Empty")
                print("Validation: FAIL")
                print("", flush=True)
                continue
                
            # Field exists and is extracted
            grounded = False
            error_msg = ""
            ocr_val_str = "Not found"
            llm_val_str = str(val)
            
            # Numeric fields check
            if field in ("subtotal", "tax_amount", "total_amount"):
                num_val = normalize_number(val)
                if num_val is None:
                    grounded = False
                    error_msg = f"Value '{val}' is not a valid number."
                    llm_val_str = str(val)
                else:
                    grounded = amount_exists_in_ocr(num_val, ocr_text)
                    error_msg = f"Amount '{num_val}' for '{field}' not found in OCR text."
                    llm_val_str = str(num_val)
                    if grounded:
                        ocr_val_str = str(num_val)
                    
            # Date field check
            elif field == "document_date":
                if not is_valid_date(str(val)):
                    grounded = False
                    error_msg = f"Document date '{val}' is not a valid date format."
                else:
                    parts = re.findall(r"\d+", str(val))
                    if parts:
                        norm_ocr = normalize_for_check(ocr_text)
                        grounded = any(part in norm_ocr for part in parts)
                    else:
                        grounded = False
                    error_msg = f"Date digits from '{val}' are not grounded in OCR text."
                    if grounded:
                        ocr_val_str = str(val)
                
            # Currency check
            elif field == "currency":
                val_upper = str(val).strip().upper()
                if val_upper == "SAR":
                    grounded = any(term in ocr_text.lower() for term in ("sar", "riy", "ريال", "ر.س", "sr"))
                else:
                    grounded = normalize_for_check(str(val)) in normalize_for_check(ocr_text)
                error_msg = f"Currency '{val}' is not grounded in OCR text."
                if grounded:
                    ocr_val_str = str(val)
                
            # Text/Name/Address checks
            else:
                grounded = normalize_for_check(str(val)) in normalize_for_check(ocr_text)
                error_msg = f"Field '{field}' value '{val}' is not present in OCR text."
                if grounded:
                    ocr_val_str = str(val)
                
            if grounded:
                state = "FOUND_AND_VALID"
                validation_status = "PASS"
            else:
                state = "FOUND_BUT_INCORRECT"
                validation_status = "FAIL"
                
                severity = "error" if field == "document_number" else "warning"
                issues.append({
                    "field": field,
                    "message": error_msg,
                    "severity": severity
                })
                
                if field == "document_number":
                    penalties += 0.2
                elif field in ("vat_number", "document_date"):
                    penalties += 0.15
                else:
                    penalties += 0.05
                    
            field_states[field] = state
            
            print(f"Field: {field}")
            print("OCR contains field: YES")
            print(f"OCR normalized value: {ocr_val_str}")
            print(f"LLM normalized value: {llm_val_str}")
            print(f"Validation: {validation_status}")
            print("", flush=True)

        # 5. Math check
        subtotal = normalize_number(get_field_value("subtotal"))
        tax_amount = normalize_number(get_field_value("tax_amount"))
        total_amount = normalize_number(get_field_value("total_amount"))
        
        if subtotal is not None and tax_amount is not None and total_amount is not None:
            if abs((subtotal + tax_amount) - total_amount) > 0.05:
                issues.append({
                    "field": "total_amount",
                    "message": f"Math check failed: subtotal ({subtotal}) + tax ({tax_amount}) = {subtotal+tax_amount:.2f}, but total is {total_amount}.",
                    "severity": "error"
                })
                penalties += 0.2
                field_states["total_amount"] = "FOUND_BUT_INCORRECT"
                print("Math validation: FAIL", flush=True)
            else:
                print("Math validation: PASS", flush=True)
                
        print("========================================================\n", flush=True)

        # Confidence per field mapping
        field_confidences = {}
        for field, state in field_states.items():
            if state == "FOUND_AND_VALID":
                field_confidences[field] = 0.99 if field in ("subtotal", "tax_amount", "total_amount") else (0.98 if field == "document_date" else 0.97)
            elif state == "NOT_PRESENT_IN_SOURCE":
                field_confidences[field] = 1.00
            elif state == "NOT_EXTRACTED":
                field_confidences[field] = 0.10
            elif state == "FOUND_BUT_INCORRECT":
                field_confidences[field] = 0.40
            else:
                field_confidences[field] = 0.80

        # Calculate overall confidence based on present fields
        relevant_confs = [c for f, c in field_confidences.items() if field_states[f] != "NOT_PRESENT_IN_SOURCE"]
        if relevant_confs:
            final_confidence = round(sum(relevant_confs) / len(relevant_confs), 2)
        else:
            final_confidence = 1.00

        payload["_confidence"] = final_confidence
        validation_results = {
            "valid": len([i for i in issues if i["severity"] == "error"]) == 0,
            "issues": issues,
            "field_states": field_states,
            "field_confidences": field_confidences,
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
