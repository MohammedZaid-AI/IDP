from __future__ import annotations

import json
import logging
import re
import time
import subprocess
from typing import Any

import httpx

from services.settings import get_settings

LOGGER = logging.getLogger(__name__)

# Global cache for availability
_OLLAMA_AVAILABLE = None


def has_letters(block: list[str]) -> bool:
    for token in block:
        if any(c.isalpha() for c in token):
            return True
    return False


def deduplicate_tokens(text: str) -> str:
    if not text:
        return ""
    # Deduplicate repeating sequences of characters (2-15 chars repeating 5+ times)
    text = re.sub(r'(.{2,15}?)\1{4,}', r'\1', text)
    # Deduplicate repeating single characters (excluding digits and spaces repeating 5+ times)
    text = re.sub(r'([^0-9\s])\1{4,}', r'\1', text)
    # Find all words/tokens, including newlines
    tokens = re.findall(r"\S+|\n", text)    
    if not tokens:
        return ""
    
    result = []
    norm_result = []  # lowercase and digits replaced with '#'
    
    for token in tokens:
        result.append(token)
        # Create normalized token   
        norm_t = token.lower()
        norm_t = re.sub(r"\d+", "#", norm_t)
        norm_result.append(norm_t)
        
        # Check for repeating patterns of size k up to 20
        for k in range(1, 21):
            if len(result) >= 3 * k:
                # Only deduplicate if the pattern has at least one letter
                if has_letters(result[-k:]):
                    if norm_result[-k:] == norm_result[-2*k:-k] == norm_result[-3*k:-2*k]:
                        # Pop the last block from both original and normalized lists
                        del result[-k:]
                        del norm_result[-k:]
                        break
    
    # Reconstruct text. We join with space, but avoid extra spaces around newlines.
    reconstructed = []
    for t in result:
        if t == "\n":
            reconstructed.append("\n")
        else:
            if reconstructed and reconstructed[-1] != "\n":
                reconstructed.append(" ")
            reconstructed.append(t)
    return "".join(reconstructed)


def find_english_vendor_fallback(paddle_text: str) -> str:
    if not paddle_text:
        return ""
    lines = [line.strip() for line in paddle_text.splitlines() if line.strip()]
    for line in lines[:4]:
        words = line.upper().split()
        if any(w in ("EST", "EST.", "LTD", "LTD.", "CO", "CO.", "LLC", "GMBH", "CORP", "INC", "COMPANY", "SERVICE", "SERVICES", "CABLES", "TRADING", "PLANT", "MANUFACTURE") for w in words):
            if not any(lbl in line.lower() for lbl in ("invoice", "bill", "date", "address", "tel", "phone", "fax", "tax", "vat")):
                cleaned = re.sub(r"^[\W_]+", "", line).strip()
                if len(cleaned) > 5 and re.search(r"[A-Z]{3,}", cleaned):
                    return cleaned
    return ""


def clean_metadata_value(val: str) -> str:
    if not val:
        return ""
    
    # Replace underscores with hyphens
    val = val.replace("_", "-")
    # Standardize spacing around hyphens
    val = re.sub(r"\s*-\s*", " - ", val)
    # Collapse multiple hyphens/dashes
    val = re.sub(r"\s*-\s*(?:-\s*)+", " - ", val)
    
    # Collapse multiple spaces
    val = re.sub(r"\s+", " ", val).strip()
    
    # List of labels to remove from the beginning (case-insensitive)
    labels = [
        "اسم الشركة",
        "company name",
        "vendor name",
        "vendor",
        "supplier name",
        "supplier",
        "customer name",
        "customer",
        "client name",
        "client",
        "address",
        "عنوان",
        "العميل",
        "المورد",
        "اسم البائع",
        "اسم العميل",
        "فاتورة",
        "invoice",
        "vat",
        "رقم الضريبة",
    ]
    
    changed = True
    while changed:
        changed = False
        val_lower = val.lower()
        for label in labels:
            if val_lower.startswith(label):
                val = val[len(label):].strip()
                val_lower = val.lower()
                changed = True
                break
        
        stripped_val = val.lstrip(":،-_,. \t\r\n")
        if stripped_val != val:
            val = stripped_val
            changed = True
            
    return val


class OllamaExtractor:
    """Extracts Arabic/English company metadata using local Ollama model qwen2.5:3b."""

    def __init__(self) -> None:
        settings = get_settings()
        self.url = settings.ollama_url.rstrip("/")
        self.model = "qwen2.5:3b"

    @property
    def is_available(self) -> bool:
        global _OLLAMA_AVAILABLE
        if _OLLAMA_AVAILABLE is None:
            try:
                res = httpx.get(f"{self.url}/api/tags", timeout=3.0)
                if res.status_code == 200:
                    models = res.json().get("models", [])
                    if any(m.get("name") == self.model or m.get("name", "").startswith(f"{self.model}:") for m in models):
                        _OLLAMA_AVAILABLE = True
                    else:
                        _OLLAMA_AVAILABLE = False
                else:
                    _OLLAMA_AVAILABLE = False
            except Exception:
                _OLLAMA_AVAILABLE = False
        return _OLLAMA_AVAILABLE

    def ensure_initialized(self) -> None:
        global _OLLAMA_AVAILABLE
        
        # Verify Ollama connection
        ollama_ok = False
        try:
            res = httpx.get(f"{self.url}/api/tags", timeout=5.0)
            if res.status_code == 200:
                ollama_ok = True
        except Exception:
            pass

        if not ollama_ok:
            print("✗ Ollama connection failed", flush=True)
            _OLLAMA_AVAILABLE = False
            return

        print("✓ Ollama connected", flush=True)

        # Verify qwen2.5:3b is available using subprocess "ollama list" first
        model_available = False
        try:
            res = subprocess.run(["ollama", "list"], capture_output=True, text=True, check=True)
            if self.model in res.stdout:
                model_available = True
        except Exception:
            # Fallback to API tags endpoint check
            try:
                res = httpx.get(f"{self.url}/api/tags", timeout=5.0)
                models = res.json().get("models", [])
                if any(m.get("name") == self.model or m.get("name", "").startswith(f"{self.model}:") for m in models):
                    model_available = True
            except Exception:
                pass

        if model_available:
            print(f"✓ {self.model} available", flush=True)
            _OLLAMA_AVAILABLE = True
        else:
            print(f"✗ {self.model} unavailable", flush=True)
            _OLLAMA_AVAILABLE = False

    def extract_entities(self, ocr_text: str, paddle_text: str | None = None) -> dict[str, Any]:
        start_time = time.perf_counter()
        
        # Deduplicate repetitions from visual OCR transcription
        ocr_text = deduplicate_tokens(ocr_text)

        extracted_json = {
            "vendor_name_ar": "",
            "vendor_name_en": "",
            "customer_name_ar": "",
            "customer_name_en": "",
            "address_ar": "",
            "address_en": "",
        }

        if not self.is_available:
            return {
                "extracted_json": extracted_json,
                "confidences": {k: 0.0 for k in extracted_json},
                "raw_response": "Ollama extractor is unavailable.",
                "llm_time": 0.0
            }

        source_text = f"Primary OCR (PaddleOCR):\n---\n{paddle_text}\n---\n\nBilingual VLM Transcription (Qari OCR):\n---\n{ocr_text}\n---" if paddle_text else ocr_text

        prompt = (
            "You are a bilingual invoice metadata extractor. Analyze the input OCR texts and extract the values into the required JSON schema.\n\n"
            "### RULES:\n"
            "- Extract values exactly as they appear. Never include labels (like 'اسم الشركة', 'Company Name', 'Address', 'عنوان').\n"
            "- Extract vendor_name_ar and vendor_name_en independently. Look at both texts. Populate both if both exist. Do not combine them.\n"
            "- For vendor_name_en and customer_name_en, you MUST extract the official English names as they appear in the source texts (especially the top headers of the PaddleOCR text, e.g., 'ABC TRADING EST', 'XYZ LLC'). Do NOT translate the Arabic names into English (for example, do NOT translate 'مؤسسة الأمل' to 'HOPE FOUNDATION' or 'Hope'). If the official English name is not present in the texts, return \"\".\n"
            "- vendor_name must be the company issuing the invoice. customer_name must be the buyer/client. Do NOT swap them.\n"
            "- If customer_name is not clearly present, return \"\". Do NOT generate placeholders (e.g. 'Unnamed customer', 'the name').\n"
            "- Copy addresses verbatim. Do NOT translate addresses. If only Arabic address exists, return \"\" for address_en (do not translate it).\n"
            "- Never change names of cities (e.g., do not change 'الرياض' to 'مكة المكرمة', do not change 'الفيصليه' to 'الفيصلي').\n"
            "- Do NOT output Chinese characters. Use only Arabic or English matching the input texts.\n"
            "- Output MUST be a valid JSON object matching the SCHEMA below. No markdown fences or explanations.\n\n"
            "### SCHEMA:\n"
            "{\n"
            "  \"vendor_name_ar\": \"\",\n"
            "  \"vendor_name_en\": \"\",\n"
            "  \"customer_name_ar\": \"\",\n"
            "  \"customer_name_en\": \"\",\n"
            "  \"address_ar\": \"\",\n"
            "  \"address_en\": \"\"\n"
            "}\n\n"
            f"### OCR TEXTS:\n{source_text}"
        )
        self.last_prompt = prompt
        self.last_raw_response = ""

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
                            "top_p": 0.9,
                            "seed": 42
                        }
                    }
                )
                if res.status_code == 200:
                    res_json = res.json()
                    raw_response = res_json.get("response", "").strip()
                    self.last_raw_response = raw_response
                    parsed = self._parse_json(raw_response)
                    if parsed:
                        for key in extracted_json:
                            val = parsed.get(key, "")
                            clean_val = "" if val is None else str(val).strip()
                            extracted_json[key] = clean_metadata_value(clean_val)
                        if paddle_text:
                            fallback_en = find_english_vendor_fallback(paddle_text)
                            if fallback_en:
                                val_en = extracted_json.get("vendor_name_en", "")
                                conf = self._calculate_confidence(val_en, ocr_text, paddle_text)
                                is_substring = val_en.lower() in fallback_en.lower() if val_en else False
                                is_fuzzy_match = False
                                if val_en:
                                    try:
                                        from rapidfuzz import fuzz
                                        is_fuzzy_match = fuzz.ratio(val_en.lower(), fallback_en.lower()) >= 80.0
                                    except Exception:
                                        pass
                                if not val_en or conf < 0.6 or is_substring or is_fuzzy_match:
                                    extracted_json["vendor_name_en"] = clean_metadata_value(fallback_en)
                else:
                    LOGGER.error("Ollama API failed status=%d response=%s", res.status_code, res.text)
        except Exception as exc:
            LOGGER.error("Ollama extraction failed: %s", exc)

        llm_time = time.perf_counter() - start_time
        
        confidences = {}
        for field, value in extracted_json.items():
            confidences[field] = self._calculate_confidence(value, ocr_text, paddle_text)

        self.last_parsed_json = extracted_json
        return {
            "extracted_json": extracted_json,
            "confidences": confidences,
            "raw_response": raw_response,
            "llm_time": llm_time
        }

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

    def _calculate_confidence(self, value: str, ocr_text: str, paddle_text: str | None = None) -> float:
        if not value:
            return 0.0
        combined = (ocr_text + "\n" + paddle_text) if paddle_text else ocr_text
        if value in combined:
            return 1.0
        words = value.split()
        if not words:
            return 0.0
        matches = sum(1 for word in words if word in combined)
        return round(matches / len(words), 2)
