from __future__ import annotations

import sys
try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except Exception:
    pass

import json
import logging
import re
import time
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Any

import fitz
import numpy as np
from PIL import Image
from rapidfuzz import fuzz

from services.settings import get_settings
from services.paddle_ocr_service import PaddleOCRService
from services.numeric_extractor import NUMERIC_FIELDS, NumericExtractor
from services.ollama_extractor import OllamaExtractor
from services.qari_ocr_service import QariOCRService

LOGGER = logging.getLogger(__name__)
MAX_PAGES = 10

ARABIC_FIELDS = [
    "vendor_name_ar",
    "vendor_name_en",
    "customer_name_ar",
    "customer_name_en",
    "address_ar",
    "address_en",
]

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
class HybridExtractionResult:
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

def _render_pages(file_path: Path) -> list[Image.Image]:
    if file_path.suffix.lower() == ".pdf":
        doc = fitz.open(str(file_path))
        pages = []
        for page_index, page in enumerate(doc):
            if page_index >= MAX_PAGES:
                break
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
            pages.append(Image.open(BytesIO(pix.tobytes("png"))).convert("RGB"))
        return pages
    return [Image.open(file_path).convert("RGB")]

def _normalize_for_match(value: Any) -> str:
    # Basic normalization to clean up text comparison
    text = str(value or "").strip().lower()
    return re.sub(r"[\W_]+", "", text, flags=re.UNICODE)

def _normalize_amount_for_match(val: Any) -> list[str]:
    try:
        f_val = float(val)
        s1 = f"{f_val:.2f}"
        s2 = f"{f_val:.0f}"
        s3 = f"{f_val:.1f}"
        return [re.sub(r"[\W_]+", "", s, flags=re.UNICODE) for s in (s1, s2, s3)]
    except (ValueError, TypeError):
        return [re.sub(r"[\W_]+", "", str(val).strip().lower(), flags=re.UNICODE)]

def _normalize_date_for_match(val: str) -> list[str]:
    match = re.match(r"^(\d{4})-(\d{1,2})-(\d{1,2})$", val.strip())
    if not match:
        return [re.sub(r"[\W_]+", "", val.lower(), flags=re.UNICODE)]
    year, month, day = match.groups()
    y_val, m_val, d_val = int(year), int(month), int(day)
    return [
        f"{d_val:02d}{m_val:02d}{y_val}",
        f"{y_val}{m_val:02d}{d_val:02d}",
        f"{d_val}{m_val}{y_val}",
        f"{y_val}{m_val}{d_val}",
    ]

def count_chars_by_language(text: str) -> tuple[int, int]:
    arabic_pattern = re.compile(r'[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]')
    english_pattern = re.compile(r'[a-zA-Z]')
    arabic_count = len(arabic_pattern.findall(text))
    english_count = len(english_pattern.findall(text))
    return arabic_count, english_count


def detect_field_language(text: str) -> str:
    if not text.strip():
        return "Empty"
    numeric_stripped = re.sub(r'[\d\s.,:/\\#\-–—$€£¥SAReur]', '', text)
    if not numeric_stripped.strip():
        return "Numeric"
    ar, en = count_chars_by_language(text)
    if ar > 0 and en == 0:
        return "Arabic"
    elif en > 0 and ar == 0:
        return "English"
    elif ar > 0 and en > 0:
        total = ar + en
        if ar / total >= 0.7:
            return "Arabic"
        elif en / total >= 0.7:
            return "English"
        else:
            return "Mixed"
    else:
        return "Symbols"


def is_invalid_customer_name(value: str) -> bool:
    if not value:
        return True
    val_lower = value.lower().strip()
    numeric_stripped = re.sub(r'[\d\s.,:/\\#\-–—$€£¥SAReur]', '', value)
    if not numeric_stripped.strip():
        return True
    invalid_keywords = [
        'invoice', 'bill', 'receipt', 'date', 'total', 'subtotal', 'amount', 'price', 'qty', 'quantity',
        'vat', 'tax', 'tin', 'cr', 'number', 'no', 'ref', 'reference', 'serial', 'sn', 's/n',
        'فترة', 'فاتورة', 'مجموع', 'إجمالي', 'تاريخ', 'رقم', 'الرقم', 'ضريبة', 'الضريبة', 'عميل', 'زبون'
    ]
    # Check for exact word matches using re.findall to extract words
    val_words = re.findall(r'[\w/]+', val_lower)
    if any(k in val_words for k in invalid_keywords):
        return True
    words = value.split()
    if len(words) > 25:
        return True
    return False


def validate_field_value(field: str, value: str) -> bool:
    if not value:
        return False
    val_lower = value.lower().strip()
    rejections = ["vat invoice", "tax invoice", "commercial invoice", "invoice", "فاتورة", "فاتورة ضريبية", "فاتورة تبسيطية"]
    if val_lower in rejections:
        return False
    if "vendor_name" in field:
        if val_lower in ["vat invoice", "tax invoice", "invoice", "commercial invoice", "فاتورة", "فاتورة ضريبية"]:
            return False
    if "customer_name" in field:
        if is_invalid_customer_name(value):
            return False
    if "address" in field:
        exclude = ['total', 'grand total', 'subtotal', 'amount', 'qty', 'price', 'description', 'المجموع', 'الاجمالي', 'الكمية']
        if any(e in val_lower for e in exclude):
            return False
    return True


def recover_company_name(short_name: str, ocr_text: str) -> str:
    if not short_name or len(short_name.split()) > 1:
        return short_name
    short_lower = short_name.lower()
    lines = ocr_text.splitlines()
    for line in lines:
        line_strip = line.strip()
        if re.search(r'\b' + re.escape(short_name) + r'\b', line_strip, re.IGNORECASE):
            words = line_strip.split()
            if len(words) >= 3:
                clean_line = re.sub(r'^(?:invoice|tin|date|page|description|qty|price|amount|المجموع|الوصف|الكمية|السعر|رقم)\s*[:.-]*\s*', '', line_strip, flags=re.IGNORECASE)
                return clean_line.strip()
    best_line = None
    max_len = 0
    for line in lines:
        line_strip = line.strip()
        line_lower = line_strip.lower()
        if any(short_lower in w or w in short_lower for w in line_lower.split() if len(w) > 3):
            words = line_strip.split()
            if len(words) >= 3 and len(line_strip) > max_len:
                if not any(k in line_lower for k in ['invoice', 'date', 'total', 'subtotal', 'due', 'amount', 'box', 'road', 'street', 'بند', 'تاريخ', 'رقم']):
                    best_line = line_strip
                    max_len = len(line_strip)
    if best_line:
        clean_line = re.sub(r'^(?:invoice|tin|date|page|description|qty|price|amount|المجموع|الوصف|الكمية|السعر|رقم)\s*[:.-]*\s*', '', best_line, flags=re.IGNORECASE)
        return clean_line.strip()
    return short_name


def is_address_like(line: str) -> bool:
    line_lower = line.lower()
    addr_keywords = [
        'street', 'road', 'building', 'bldg', 'box', 'p.o.', 'po box', 'district', 'kingdom',
        'riyadh', 'jeddah', 'dammam', 'khobar', 'suburb', 'floor', 'city', 'country', 'postal', 'zip',
        'شارع', 'طريق', 'ص.ب', 'ص ب', 'ص. ب.', 'الرمز', 'البريدي', 'المملكة', 'العربية', 'السعودية',
        'جدة', 'الرياض', 'الدمام', 'الخبر', 'حي', 'منطقة', 'الدور', 'مبنى'
    ]
    if any(k in line_lower for k in addr_keywords):
        exclude_keywords = [
            'invoice', 'bill', 'receipt', 'date', 'total', 'subtotal', 'amount', 'price', 'qty', 'quantity',
            'description', 'vat', 'tax', 'tin', 'cr', 'الكمية', 'الوصف', 'السعر', 'المبلغ', 'ضريبة', 'فاتورة',
            'التاريخ', 'المجموع', 'رقم'
        ]
        if not any(k in line_lower for k in exclude_keywords):
            return True
    return False


def recover_address(short_addr: str, ocr_text: str) -> str:
    if not short_addr or len(short_addr.split()) >= 4:
        return short_addr
    lines = ocr_text.splitlines()
    addr_line_index = -1
    short_addr_lower = short_addr.lower().strip()
    for idx, line in enumerate(lines):
        if short_addr_lower in line.lower():
            addr_line_index = idx
            break
    if addr_line_index == -1:
        return short_addr
    address_lines = [lines[addr_line_index].strip()]
    for idx in range(addr_line_index - 1, -1, -1):
        line = lines[idx].strip()
        if is_address_like(line):
            address_lines.insert(0, line)
        else:
            break
    for idx in range(addr_line_index + 1, len(lines)):
        line = lines[idx].strip()
        if is_address_like(line):
            address_lines.append(line)
        else:
            break
    recovered = " ".join(address_lines).strip()
    return recovered if len(recovered) > len(short_addr) else short_addr


def find_arabic_company_name(ocr_text: str) -> str:
    lines = ocr_text.splitlines()
    for line in lines:
        line_strip = line.strip()
        if len(line_strip) < 4:
            continue
        ar_cnt, en_cnt = count_chars_by_language(line_strip)
        if ar_cnt > 0 and ar_cnt > en_cnt:
            line_lower = line_strip.lower()
            exclude_keywords = ['رقم', 'تاريخ', 'فاتورة', 'مجموع', 'إجمالي', 'تلفون', 'هاتف', 'بريد', 'ص.ب']
            if not any(k in line_lower for k in exclude_keywords):
                company_keywords = ['شركة', 'مؤسسة', 'مصنع', 'مجموعة', 'مكتب', 'محدودة']
                if any(k in line_strip for k in company_keywords):
                    return line_strip
    for line in lines:
        line_strip = line.strip()
        if len(line_strip) < 4:
            continue
        ar_cnt, en_cnt = count_chars_by_language(line_strip)
        if ar_cnt > 0 and ar_cnt > en_cnt * 2:
            line_lower = line_strip.lower()
            exclude_keywords = ['رقم', 'تاريخ', 'فاتورة', 'مجموع', 'إجمالي', 'تلفون', 'هاتف', 'بريد', 'ص.ب', 'ص ب']
            if not any(k in line_lower for k in exclude_keywords):
                return line_strip
    return ""


def find_english_company_name(ocr_text: str) -> str:
    lines = ocr_text.splitlines()
    for line in lines:
        line_strip = line.strip()
        if len(line_strip) < 4:
            continue
        ar_cnt, en_cnt = count_chars_by_language(line_strip)
        if en_cnt > 0 and en_cnt > ar_cnt:
            line_lower = line_strip.lower()
            exclude_keywords = ['invoice', 'date', 'total', 'subtotal', 'amount', 'tax', 'vat', 'page', 'tel', 'phone', 'box', 'street', 'road']
            if not any(k in line_lower for k in exclude_keywords):
                company_keywords = ['company', 'co.', 'ltd.', 'corp', 'corporation', 'inc', 'incorporated', 'establishment', 'est.', 'cables', 'factory', 'group']
                if any(k in line_lower for k in company_keywords):
                    return line_strip
    for line in lines:
        line_strip = line.strip()
        if len(line_strip) < 4:
            continue
        ar_cnt, en_cnt = count_chars_by_language(line_strip)
        if en_cnt > 0 and en_cnt > ar_cnt * 2:
            line_lower = line_strip.lower()
            exclude_keywords = ['invoice', 'date', 'total', 'subtotal', 'amount', 'tax', 'vat', 'page', 'tel', 'phone', 'box', 'street', 'road']
            if not any(k in line_lower for k in exclude_keywords):
                return line_strip
    return ""


class MergeExtractor:
    """Combines and validates outputs from NumericExtractor (PaddleOCR) and OllamaExtractor (Qari OCR)."""

    def merge(
        self,
        numeric_result: dict[str, Any],
        arabic_result: dict[str, Any],
        paddle_ocr_text: str,
        qari_ocr_text: str,
    ) -> dict[str, Any]:
        validation_start = time.perf_counter()
        
        payload: dict[str, Any] = {field: "" for field in FINAL_COLUMNS}
        for field in ("subtotal", "tax_amount", "total_amount"):
            payload[field] = None

        # Numeric fields from NumericExtractor
        for field in NUMERIC_FIELDS:
            payload[field] = numeric_result.get(field)
            
        # Arabic/English fields from Ollama
        for field in ARABIC_FIELDS:
            payload[field] = arabic_result.get(field, "")

        # Relocate misplaced values based on language
        for base in ("vendor_name", "customer_name", "address"):
            ar_val = payload[f"{base}_ar"]
            en_val = payload[f"{base}_en"]
            if ar_val:
                ar_ar_cnt, ar_en_cnt = count_chars_by_language(ar_val)
                if ar_en_cnt > ar_ar_cnt and ar_en_cnt > 0:
                    if not en_val:
                        payload[f"{base}_en"] = ar_val
                        payload[f"{base}_ar"] = ""
                        LOGGER.info(f"Relocated mostly English value for {base} from Arabic to English field: '{ar_val}'")
            # re-read after possible modification
            ar_val = payload[f"{base}_ar"]
            en_val = payload[f"{base}_en"]
            if en_val:
                en_ar_cnt, en_en_cnt = count_chars_by_language(en_val)
                if en_ar_cnt > en_en_cnt and en_ar_cnt > 0:
                    if not ar_val:
                        payload[f"{base}_ar"] = en_val
                        payload[f"{base}_en"] = ""
                        LOGGER.info(f"Relocated mostly Arabic value for {base} from English to Arabic field: '{en_val}'")

        ocr_combined = (qari_ocr_text + "\n" + paddle_ocr_text) if paddle_ocr_text else qari_ocr_text

        # 1. Recover short company names (e.g. CABLES -> Bahra...)
        for field in ("vendor_name_ar", "vendor_name_en", "customer_name_ar", "customer_name_en"):
            val = payload[field]
            if val:
                recovered_val = recover_company_name(val, ocr_combined)
                if recovered_val != val:
                    LOGGER.info(f"Company name recovery for {field}: '{val}' -> '{recovered_val}'")
                    print(f"Company name recovery for {field}: '{val}' -> '{recovered_val}'", flush=True)
                    payload[field] = recovered_val

        # 2. Recover incomplete addresses
        for field in ("address_ar", "address_en"):
            val = payload[field]
            if val:
                recovered_val = recover_address(val, ocr_combined)
                if recovered_val != val:
                    LOGGER.info(f"Address recovery for {field}: '{val}' -> '{recovered_val}'")
                    print(f"Address recovery for {field}: '{val}' -> '{recovered_val}'", flush=True)
                    payload[field] = recovered_val

        # 3. Validate languages, apply rejections and overrides
        forced_confidences = {}
        for field in ARABIC_FIELDS:
            val = payload[field]
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
                    recovered = find_arabic_company_name(ocr_combined)
                elif field == "vendor_name_en":
                    recovered = find_english_company_name(ocr_combined)
                    
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

        payload["_confidences"] = {field: 0.0 for field in FINAL_COLUMNS}
        payload["_validation"] = {"valid": True, "issues": []}

        # Perform grounding & validation
        self._validate_and_score(payload, paddle_ocr_text, qari_ocr_text)
        
        # Override confidences/values for rejected fields
        for field, conf in forced_confidences.items():
            payload["_confidences"][field] = conf
            if conf == 0.0:
                payload[field] = ""

        payload["_validation"]["processing_time"] = round(time.perf_counter() - validation_start, 4)
        return payload

    def _validate_and_score(self, payload: dict[str, Any], paddle_text: str, qari_text: str) -> None:
        issues: list[dict[str, str]] = []
        confidences: dict[str, float] = payload["_confidences"]
        norm_paddle = _normalize_for_match(paddle_text)

        # Validate numeric fields against PaddleOCR text
        for field in NUMERIC_FIELDS:
            val = payload.get(field)
            if val in (None, ""):
                continue
            
            is_grounded = False
            if field in ("subtotal", "tax_amount", "total_amount"):
                candidates = _normalize_amount_for_match(val)
                if any(cand and cand in norm_paddle for cand in candidates):
                    is_grounded = True
            elif field == "document_date":
                candidates = _normalize_date_for_match(str(val))
                if any(cand and cand in norm_paddle for cand in candidates):
                    is_grounded = True
            else:
                norm_val = _normalize_for_match(val)
                if norm_val and norm_val in norm_paddle:
                    is_grounded = True
            
            if is_grounded:
                confidences[field] = 1.0
            else:
                # If amount or field is not grounded in PaddleOCR text, clean it
                payload[field] = None if field in ("subtotal", "tax_amount", "total_amount") else ""
                confidences[field] = 0.0
                issues.append({
                    "field": field,
                    "message": f"Numeric field {field} value not found in Paddle OCR text.",
                    "severity": "error"
                })

        # Validate Arabic/English company fields against Qari OCR text (and PaddleOCR text as fallback)
        for field in ARABIC_FIELDS:
            val = payload.get(field)
            if not val:
                continue
                
            norm_val = _normalize_for_match(val)
            norm_qari = _normalize_for_match(qari_text)
            norm_paddle = _normalize_for_match(paddle_text)
            
            # Fuzzy match with RapidFuzz partial_ratio >= 85 against both texts
            fuzzy_score_qari = fuzz.partial_ratio(norm_val, norm_qari)
            fuzzy_score_paddle = fuzz.partial_ratio(norm_val, norm_paddle)
            is_grounded = (fuzzy_score_qari >= 70.0) or (fuzzy_score_paddle >= 70.0)
            
            if is_grounded:
                confidences[field] = 0.95
            else:
                payload[field] = ""
                confidences[field] = 0.0
                issues.append({
                    "field": field,
                    "message": f"Arabic/English field {field} value not found in Qari or Paddle OCR text (fuzzy score Qari {fuzzy_score_qari:.2f}%, Paddle {fuzzy_score_paddle:.2f}%).",
                    "severity": "error"
                })

        payload["_validation"] = {
            "valid": not any(issue["severity"] == "error" for issue in issues),
            "issues": issues,
        }

    def confidence(self, payload: dict[str, Any]) -> float:
        confidences = payload.get("_confidences", {})
        weights = {
            "document_number": 0.14,
            "vat_number": 0.14,
            "document_date": 0.07,
            "currency": 0.05,
            "vendor_name_ar": 0.10,
            "vendor_name_en": 0.08,
            "customer_name_ar": 0.08,
            "customer_name_en": 0.06,
            "address_ar": 0.06,
            "address_en": 0.04,
            "subtotal": 0.06,
            "tax_amount": 0.06,
            "total_amount": 0.06,
        }
        score = sum(weights[f] * float(confidences.get(f, 0.0)) for f in weights)
        issues = payload.get("_validation", {}).get("issues", [])
        score -= min(sum(1 for issue in issues if issue.get("severity") == "error") * 0.04, 0.2)
        return round(max(0.0, min(1.0, score)), 2)

class HybridInvoiceExtractionService:
    """PaddleOCR + Qari OCR + local Ollama extraction pipeline."""

    def __init__(self) -> None:
        self.paddle = PaddleOCRService()
        self.numeric_extractor = NumericExtractor()
        self.ollama_extractor = OllamaExtractor()
        self.qari = QariOCRService()
        self.merge_extractor = MergeExtractor()

    def ensure_initialized(self) -> None:
        self.paddle.ensure_initialized()
        self.ollama_extractor.ensure_initialized()
        self.qari.ensure_initialized()

    def extract(self, file_path: str | Path) -> HybridExtractionResult:
        started = time.perf_counter()
        file_path = Path(file_path)
        pages = _render_pages(file_path)

        # 1. Run PaddleOCR for NumericExtractor
        ocr_start = time.perf_counter()
        paddle_text, paddle_ocr_time = self._run_paddle_ocr(pages, file_path.name)
        
        # 2. Run Qari OCR for OllamaExtractor
        qari_start = time.perf_counter()
        qari_text = self.qari.extract_text(file_path)
        qari_ocr_time = time.perf_counter() - qari_start

        # ADD DIAGNOSTICS requested by user
        print("\n--- DIAGNOSTICS START ---", flush=True)
        
        paddle_lines = paddle_text.splitlines()
        print("First 20 lines of PaddleOCR text:", flush=True)
        for line in paddle_lines[:20]:
            print(f"  {line}", flush=True)
        print("", flush=True)

        qari_lines = qari_text.splitlines()
        print("First 20 lines of Qari OCR text:", flush=True)
        for line in qari_lines[:20]:
            print(f"  {line}", flush=True)
        print("", flush=True)

        # Extract LLM values from Qari text
        llm_start = time.perf_counter()
        
        # Print exact text sent to Ollama
        print("Exact text sent to Ollama:", flush=True)
        print(qari_text, flush=True)
        print("", flush=True)

        ollama_result = self.ollama_extractor.extract_entities(qari_text, paddle_text=paddle_text)
        llm_time = time.perf_counter() - llm_start

        # Print JSON returned by Ollama
        print("JSON returned by Ollama:", flush=True)
        print(ollama_result["raw_response"], flush=True)
        print("--- DIAGNOSTICS END ---\n", flush=True)

        # Run numeric extraction on PaddleOCR text
        numeric_result = self.numeric_extractor.extract(paddle_text)

        # 3. Merge outputs
        validation_start = time.perf_counter()
        merged = self.merge_extractor.merge(
            numeric_result.extracted_json,
            ollama_result["extracted_json"],
            paddle_text,
            qari_text,
        )
        final_confidence = self.merge_extractor.confidence(merged)
        validation_time = time.perf_counter() - validation_start
        processing_time = time.perf_counter() - started

        raw_response = json.dumps(
            {
                "numeric_raw_response": numeric_result.raw_response,
                "ollama_raw_response": ollama_result["raw_response"],
            },
            ensure_ascii=False,
            indent=2,
        )

        LOGGER.info(
            "Extraction complete file=%s paddle_ocr=%.2fs qari_ocr=%.2fs llm=%.2fs confidence=%.2f",
            file_path.name,
            paddle_ocr_time,
            qari_ocr_time,
            llm_time,
            final_confidence,
        )

        return HybridExtractionResult(
            document_type="invoice",
            extracted_json=merged,
            raw_response=raw_response,
            ocr_text=paddle_text,
            qari_ocr_text=qari_text,
            confidence=final_confidence,
            page_count=len(pages),
            ocr_time=paddle_ocr_time,
            qari_ocr_time=qari_ocr_time,
            llm_time=llm_time,
            validation_time=validation_time,
            processing_time=processing_time,
        )

    def _run_paddle_ocr(self, pages: list[Image.Image], filename: str) -> tuple[str, float]:
        self.paddle._init_ocr()
        ocr_start = time.perf_counter()
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

            LOGGER.info("PaddleOCR page %d/%d for %s", index + 1, len(pages), filename)
            image_np = np.array(page_img.convert("RGB"))
            result = self.paddle._ocr_engine.ocr(image_np)
            lines = []
            if result and result[0]:
                rec_texts = result[0].get("rec_texts", [])
                lines = [str(text) for text in rec_texts if text is not None]
            page_texts.append("\n".join(lines))
        return "\n\n--- PAGE BREAK ---\n\n".join(page_texts), time.perf_counter() - ocr_start
