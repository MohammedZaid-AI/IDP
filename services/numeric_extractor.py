from __future__ import annotations

import json
import logging
import re
import time
from dataclasses import dataclass
from typing import Any
from urllib import error, request as urllib_request

from services.settings import get_settings


LOGGER = logging.getLogger(__name__)

NUMERIC_FIELDS = [
    "document_number",
    "vat_number",
    "document_date",
    "currency",
    "subtotal",
    "tax_amount",
    "total_amount",
]

NUMERIC_EXTRACTION_PROMPT = (
    "You extract numeric and financial invoice fields from PaddleOCR text.\n"
    "Use only the OCR text provided.\n"
    "Never extract company names.\n"
    "Never extract addresses.\n"
    "Never infer values.\n"
    "Never hallucinate values.\n"
    "Return null if a value is not explicitly present.\n\n"
    "Extract ONLY this JSON schema:\n"
    "{{\n"
    "  \"document_number\": \"\",\n"
    "  \"vat_number\": \"\",\n"
    "  \"document_date\": \"\",\n"
    "  \"currency\": \"\",\n"
    "  \"subtotal\": null,\n"
    "  \"tax_amount\": null,\n"
    "  \"total_amount\": null\n"
    "}}\n\n"
    "Field rules:\n"
    "- document_number: invoice/document number only. Never use VAT, TIN, tax ID, phone, page, or date values.\n"
    "- vat_number: VAT/TIN/tax registration number only.\n"
    "- document_date: invoice/document issue date exactly as shown.\n"
    "- currency: explicit currency code or symbol/text only. Do not infer from country.\n"
    "- subtotal, tax_amount, total_amount: numeric amounts only.\n\n"
    "PaddleOCR text:\n"
    "--- START OCR ---\n"
    "{ocr_text}\n"
    "--- END OCR ---"
)


@dataclass
class NumericExtractionResult:
    extracted_json: dict[str, Any]
    raw_response: str
    llm_time: float


def _empty_numeric_payload() -> dict[str, Any]:
    return {
        "document_number": "",
        "vat_number": "",
        "document_date": "",
        "currency": "",
        "subtotal": None,
        "tax_amount": None,
        "total_amount": None,
    }


def _parse_json_response(text: str) -> dict[str, Any] | None:
    cleaned = text.strip()
    cleaned = re.sub(r"```(?:json)?", "", cleaned).replace("```", "").strip()
    try:
        payload = json.loads(cleaned)
        if isinstance(payload, dict):
            return payload
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
    if not match:
        return None
    try:
        payload = json.loads(match.group(0))
        if isinstance(payload, dict):
            return payload
    except json.JSONDecodeError:
        return None
    return None


class NumericExtractor:
    """Deterministic rule-based extractor for PaddleOCR financial fields."""

    def __init__(self, model: str | None = None) -> None:
        pass  # Signature kept for backwards compatibility

    def extract(self, paddle_ocr_text: str) -> NumericExtractionResult:
        start_time = time.perf_counter()
        
        # 1. Document Number
        doc_num = self._extract_document_number(paddle_ocr_text)
        
        # 2. VAT Number
        vat_num = self._extract_vat_number(paddle_ocr_text)
        
        # 3. Document Date
        doc_date = self._extract_document_date(paddle_ocr_text)
        
        # 4. Currency
        currency = self._extract_currency(paddle_ocr_text)
        
        # 5. Amounts (Subtotal, Tax, Total)
        amounts = self._extract_amounts_via_regex(paddle_ocr_text)
        
        payload = {
            "document_number": doc_num,
            "vat_number": vat_num,
            "document_date": doc_date,
            "currency": currency,
            "subtotal": amounts.get("subtotal"),
            "tax_amount": amounts.get("tax_amount"),
            "total_amount": amounts.get("total_amount"),
        }
        
        elapsed_time = time.perf_counter() - start_time
        
        # Diagnostics Output as requested
        diagnostics = (
            f"\n==================================================\n"
            f"DETERMINISTIC NUMERIC EXTRACTOR DIAGNOSTICS\n"
            f"==================================================\n"
            f"RAW PADDLE OCR TEXT:\n"
            f"{paddle_ocr_text}\n"
            f"--------------------------------------------------\n"
            f"REGEX MATCH DETAILS:\n"
            f"  - Document Number Candidate Matches: label patterns and digit scanning\n"
            f"  - VAT Number Candidate Matches: 15-digit sequences starting with 3\n"
            f"  - Date Candidate Matches: DD/MM/YYYY, DD-MM-YYYY, YYYY-MM-DD\n"
            f"  - Currency matches found: {currency or 'None'}\n"
            f"  - Mathematical relationship triplets evaluated for amounts\n"
            f"--------------------------------------------------\n"
            f"FINAL EXTRACTED VALUES:\n"
            f"  document_number: {doc_num!r}\n"
            f"  vat_number:      {vat_num!r}\n"
            f"  document_date:   {doc_date!r}\n"
            f"  currency:        {currency!r}\n"
            f"  subtotal:        {amounts.get('subtotal')}\n"
            f"  tax_amount:      {amounts.get('tax_amount')}\n"
            f"  total_amount:    {amounts.get('total_amount')}\n"
            f"==================================================\n"
        )
        print(diagnostics, flush=True)
        LOGGER.info(diagnostics)
        
        raw_response = json.dumps(payload, ensure_ascii=False, indent=2)
        
        return NumericExtractionResult(
            extracted_json=payload,
            raw_response=raw_response,
            llm_time=0.0,
        )

    def _clean_and_parse_float(self, s: str) -> float | None:
        raw_digits = re.sub(r'[^0-9]', '', s)
        if len(raw_digits) >= 14:
            LOGGER.warning("[DIAGNOSTIC] Ignored candidate value %r because it has 14+ digits (likely a VAT/TIN number)", s)
            print(f"[DIAGNOSTIC] Ignored candidate value {s!r} because it has 14+ digits (likely a VAT/TIN number)", flush=True)
            return None

        s_clean = s.strip().replace(" ", "").replace("-", "")
        if re.search(r'[\.,][0-9]{2}$', s_clean):
            integer_part = s_clean[:-3].replace(",", "").replace(".", "")
            decimal_part = s_clean[-2:]
            try:
                val = float(f"{integer_part}.{decimal_part}")
                if len(str(int(val))) >= 14:
                    return None
                return val
            except ValueError:
                return None
        else:
            cleaned = re.sub(r'[^0-9]', '', s_clean)
            try:
                val = float(cleaned)
                if len(str(int(val))) >= 14:
                    return None
                return val
            except ValueError:
                return None

    def _extract_document_number(self, ocr_text: str) -> str:
        patterns = [
            r'(?i)(?:invoice\s*no|invoice\s*number|invoice\s*#|inv\s*no|inv\s*#|ref\s*no|document\s*no)\s*[:\-\.#]?\s*([A-Za-z0-9\-]+)',
            r'(?i)(?:invoice|no\b)\.?\s*[:\-\.#]?\s*([A-Za-z0-9\-]+)'
        ]
        lines = [line.strip() for line in ocr_text.split('\n')]
        
        def is_valid_doc_num(val):
            val_clean = val.strip()
            if not val_clean:
                return False
            if val_clean.isdigit() and len(val_clean) == 15:
                return False
            if re.search(r'\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4}', val_clean):
                return False
            if re.search(r'\d{4}[\/\-\.]\d{1,2}[\/\-\.]\d{1,2}', val_clean):
                return False
            if val_clean.lower() in ('date', 'tax', 'tel', 'fax', 'phone', 'total', 'vat', 'invoice'):
                return False
            if not re.search(r'[A-Za-z0-9]', val_clean):
                return False
            return True

        for pattern in patterns:
            for line in lines:
                matches = re.findall(pattern, line)
                for m in matches:
                    cleaned = re.sub(r'(?i)^(invoice\s*no\.?|invoice\s*|no\.?|inv\s*no\.?|inv\b|ref\s*no\.?|ref\b)\s*[:\-\.#]?\s*', '', m).strip()
                    if is_valid_doc_num(cleaned):
                        return cleaned
                        
        numeric_matches = re.findall(r'\b\d{5,12}\b', ocr_text)
        if numeric_matches:
            filtered = [m for m in numeric_matches if m not in ("2020", "2021", "2022", "2023", "2024", "2025", "2026")]
            if filtered:
                return max(filtered, key=len)
        return ""

    def _extract_vat_number(self, ocr_text: str) -> str:
        cleaned_digits = re.sub(r'[^0-9]', '', ocr_text)
        lines = [line.strip() for line in ocr_text.split('\n')]
        vat_label_patterns = [
            r'(?i)(?:vat\s*no|vat\s*number|tax\s*no|tax\s*id|tax\s*registration|tin)\.?\s*[:\-\.#]?\s*([0-9\s\-]+)'
        ]
        for pattern in vat_label_patterns:
            for line in lines:
                matches = re.findall(pattern, line)
                for m in matches:
                    digits = re.sub(r'[^0-9]', '', m)
                    if len(digits) == 15:
                        return digits

        for line in lines:
            cleaned_line_digits = re.sub(r'[^0-9]', '', line)
            matches = re.findall(r'\b\d{15}\b', line)
            if matches:
                return matches[0]
            if len(cleaned_line_digits) == 15:
                if cleaned_line_digits.startswith('3'):
                    return cleaned_line_digits

        all_digits = re.findall(r'\d{15}', cleaned_digits)
        if all_digits:
            return all_digits[0]
        return ""

    def _extract_document_date(self, ocr_text: str) -> str:
        lines = [line.strip() for line in ocr_text.split('\n')]
        date_patterns = [
            r'\b(\d{1,2})[\/\-\.](\d{1,2})[\/\-\.](\d{2,4})\b',
            r'\b(\d{4})[\/\-\.](\d{1,2})[\/\-\.](\d{1,2})\b'
        ]
        candidates = []
        
        def is_valid_date(d, m, y):
            try:
                d, m, y = int(d), int(m), int(y)
                if y < 100:
                    y += 2000
                if m < 1 or m > 12:
                    return False
                if d < 1 or d > 31:
                    return False
                return f"{y}-{m:02d}-{d:02d}"
            except ValueError:
                return False

        for line_idx, line in enumerate(lines):
            for pattern in date_patterns:
                matches = re.findall(pattern, line)
                for m in matches:
                    if len(m) == 3:
                        p1, p2, p3 = m
                        if len(p1) == 4:
                            standardized = is_valid_date(p3, p2, p1)
                        else:
                            standardized = is_valid_date(p1, p2, p3)
                        if standardized:
                            candidates.append({
                                "value": standardized,
                                "original": "-".join(m),
                                "line_idx": line_idx,
                                "line": line
                            })
                            
        if not candidates:
            return ""
            
        for c in candidates:
            score = 0
            l_lower = c["line"].lower()
            if any(kw in l_lower for kw in ["issue", "invoice", "date", "supply", "billing"]):
                score += 10
            if any(kw in l_lower for kw in ["due", "delivery"]):
                score -= 5
            c["score"] = score
            
        candidates.sort(key=lambda x: x["score"], reverse=True)
        return candidates[0]["value"]

    def _extract_currency(self, ocr_text: str) -> str:
        text_lower = ocr_text.lower()
        currencies = {
            "sar": ["sar", "sr", "saudi riyal", "saudi riyals", "riyal", "riyals"],
            "usd": ["usd", "dollar", "dollars", "$"],
            "eur": ["eur", "euro", "euros", "€"],
            "aed": ["aed", "dirham", "dirhams"]
        }
        found = []
        for code, keywords in currencies.items():
            for kw in keywords:
                if kw == "$":
                    pattern = r'\$'
                elif kw == "€":
                    pattern = r'€'
                else:
                    pattern = r'\b' + re.escape(kw) + r'\b'
                if re.search(pattern, text_lower):
                    found.append(code.upper())
                    break
        if not found:
            return ""
        if "SAR" in found:
            return "SAR"
        return found[0]

    def _extract_amounts_via_regex(self, ocr_text: str) -> dict[str, float | None]:
        result = {
            "subtotal": None,
            "tax_amount": None,
            "total_amount": None
        }
        lines = [line.strip() for line in ocr_text.split('\n')]
        
        all_nums = []
        for line_idx, line in enumerate(lines):
            candidates = re.findall(r'\b[0-9][0-9,\.\s\-]*[0-9]\b|\b[0-9]\b', line)
            for cand in candidates:
                val = self._clean_and_parse_float(cand)
                if val is not None:
                    all_nums.append((val, line_idx, line))

        triplets = []
        for i in range(len(all_nums)):
            for j in range(i + 1, len(all_nums)):
                for k in range(j + 1, len(all_nums)):
                    val_i, idx_i, line_i = all_nums[i]
                    val_j, idx_j, line_j = all_nums[j]
                    val_k, idx_k, line_k = all_nums[k]
                    
                    if idx_k - idx_i <= 10:
                        if abs(val_i + val_j - val_k) < 0.05:
                            if val_i > 1.0 and val_j >= 0.0:
                                if val_j > 0.0:
                                    ratio = val_j / val_i
                                    if not (0.01 <= ratio <= 0.30):
                                        continue
                                triplets.append({
                                    "subtotal": val_i,
                                    "tax_amount": val_j,
                                    "total_amount": val_k,
                                    "start_line": idx_i,
                                    "end_line": idx_k,
                                    "score": 0
                                })

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
                        
                idx_sub = t["start_line"] + offset
                if 0 <= idx_sub < len(lines):
                    sub_lower = lines[idx_sub].lower()
                    if any(sk in sub_lower for sk in ["subtotal", "sub total", "before vat", "net amount"]):
                        score += 8
                        
                idx_tax = (t["start_line"] + t["end_line"]) // 2 + offset
                if 0 <= idx_tax < len(lines):
                    tax_lower = lines[idx_tax].lower()
                    if any(tk in tax_lower for tk in ["vat", "tax", "tax amount"]):
                        score += 5
            t["score"] = score

        if triplets:
            triplets.sort(key=lambda x: (x["score"], x["total_amount"]), reverse=True)
            best = triplets[0]
            result["subtotal"] = best["subtotal"]
            result["tax_amount"] = best["tax_amount"]
            result["total_amount"] = best["total_amount"]
            return result

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
            elif "total" in lower_line and not any(neg in lower_line for neg in ["total pages", "page total"]):
                if total_idx == -1:
                    total_idx = idx
            
            if any(k in lower_line for k in ["vat amt", "vat amount", "tax amount", "tax amt", "vat value"]):
                tax_idx = idx
            elif "vat" in lower_line or "tax" in lower_line:
                if tax_idx == -1:
                    tax_idx = idx
                    
            if any(k in lower_line for k in ["subtotal", "sub total", "amt before vat", "amount before vat", "net amt", "net amount"]):
                subtotal_idx = idx

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
        if tax_idx != -1:
            result["tax_amount"] = find_number_near_line(tax_idx)
        if total_idx != -1:
            result["total_amount"] = find_number_near_line(total_idx)
        return result

