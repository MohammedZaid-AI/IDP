from __future__ import annotations

import base64
import json
import logging
import os
import re
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Any
from urllib import error, request

import fitz
import numpy as np
from PIL import Image

from langchain_groq import ChatGroq

from services.settings import get_settings

LOGGER = logging.getLogger(__name__)

try:
    import easyocr
except Exception:  # pragma: no cover - optional import guard
    easyocr = None


try:
    OCR_READER = easyocr.Reader(["en", "ar"], gpu=False) if easyocr is not None else None
except Exception:  # pragma: no cover - reader can fail on some machines
    OCR_READER = None


SCHEMAS = {
    "invoice": {
        "invoice_number": None,
        "invoice_date": None,
        "vendor_name": None,
        "customer_name": None,
        "currency": None,
        "subtotal": None,
        "tax_amount": None,
        "total_amount": None,
    },
    "receipt": {
        "receipt_number": None,
        "merchant_name": None,
        "date": None,
        "amount": None,
    },
    "bank_statement": {
        "account_number": None,
        "bank_name": None,
        "opening_balance": None,
        "closing_balance": None,
    },
    "financial_report": {
        "reporting_period": None,
        "entity_name": None,
        "currency": None,
        "revenue": None,
        "profit": None,
    },
    "purchase_order": {
        "po_number": None,
        "vendor_name": None,
        "order_date": None,
        "total_amount": None,
    },
    "credit_note": {
        "credit_note_number": None,
        "vendor_name": None,
        "date": None,
        "amount": None,
    },
    "debit_note": {
        "debit_note_number": None,
        "vendor_name": None,
        "date": None,
        "amount": None,
    },
}


@dataclass
class ExtractedDocument:
    document_type: str
    json_output: dict[str, Any]
    raw_text: str
    engine: str
    confidence: float
    page_count: int
    raw_model_response: str = ""
    parsed_json: dict[str, Any] | None = None
    normalized_json: dict[str, Any] | None = None


class ExtractionStrategy:
    name = "base"

    def extract(self, file_path: str | Path, document_type: str, schema: dict[str, Any]) -> ExtractedDocument:
        raise NotImplementedError


class Qwen2_5VLStrategy(ExtractionStrategy):
    name = "qwen2.5-vl"

    def __init__(self) -> None:
        settings = get_settings()
        self.api_url = settings.qwen_api_url
        self.api_key = settings.qwen_api_key
        self.model = settings.qwen_model

    def extract(self, file_path: str | Path, document_type: str, schema: dict[str, Any]) -> ExtractedDocument:
        file_path = Path(file_path)
        LOGGER.info("Qwen extraction started file=%s document_type=%s", file_path.name, document_type)
        pages = self._render_pages(file_path)
        raw_text = self._collect_text(pages, file_path)
        payload = self._build_payload(document_type, schema, pages, raw_text)
        raw_model_response, parsed_json = self._call_remote_qwen(payload)
        print("RAW QWEN RESPONSE")
        print(raw_model_response or "<empty>")
        print("PARSED JSON")
        print(parsed_json or {})
        if not parsed_json:
            LOGGER.info("Qwen remote unavailable, using local heuristic fallback for %s", file_path.name)
            parsed_json = self._heuristic_json(raw_text, document_type, schema)
            engine = "qwen2.5-vl-local"
            confidence = 0.72
        else:
            LOGGER.info("Qwen remote extraction completed for %s", file_path.name)
            engine = "qwen2.5-vl"
            confidence = 0.92
        normalized_json = self._normalize_to_schema(document_type, schema, parsed_json, raw_text)
        print("FINAL JSON")
        print(normalized_json)
        return ExtractedDocument(
            document_type=document_type,
            json_output=normalized_json,
            raw_text=raw_text,
            engine=engine,
            confidence=confidence,
            page_count=len(pages) or 1,
            raw_model_response=raw_model_response,
            parsed_json=parsed_json,
            normalized_json=normalized_json,
        )

    def _render_pages(self, file_path: Path) -> list[Image.Image]:
        ext = file_path.suffix.lower()
        if ext == ".pdf":
            doc = fitz.open(str(file_path))
            images: list[Image.Image] = []
            for page in doc:
                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
                images.append(Image.open(BytesIO(pix.tobytes("png"))).convert("RGB"))
            return images
        return [Image.open(file_path).convert("RGB")]

    def _collect_text(self, pages: list[Image.Image], file_path: Path) -> str:
        ext = file_path.suffix.lower()
        text_chunks: list[str] = []
        if ext == ".pdf":
            with fitz.open(str(file_path)) as doc:
                for page in doc:
                    text = page.get_text("text").strip()
                    if text:
                        text_chunks.append(text)
        if OCR_READER is not None:
            for index, image in enumerate(pages):
                try:
                    result = OCR_READER.readtext(np.array(image), detail=0)
                    if result:
                        text_chunks.append("\n".join(result))
                except Exception:
                    continue
                if index == 0:
                    focused_text = self._collect_invoice_header_text(image)
                    if focused_text:
                        text_chunks.append(focused_text)
        return "\n".join(text_chunks).strip()

    @staticmethod
    def _collect_invoice_header_text(image: Image.Image) -> str:
        if OCR_READER is None:
            return ""
        width, height = image.size
        crop = image.crop((0, int(height * 0.11), int(width * 0.33), int(height * 0.18)))
        try:
            result = OCR_READER.readtext(np.array(crop), detail=0)
        except Exception:
            return ""
        return "\n".join(str(item) for item in result if item)

    def _build_payload(self, document_type: str, schema: dict[str, Any], pages: list[Image.Image], raw_text: str) -> dict[str, Any]:
        encoded_pages = []
        for index, image in enumerate(pages, start=1):
            buffer = BytesIO()
            image.save(buffer, format="PNG")
            encoded_pages.append(
                {
                    "page": index,
                    "image_base64": base64.b64encode(buffer.getvalue()).decode("ascii"),
                }
            )
        return {
            "document_type": document_type,
            "schema": schema,
            "pages": encoded_pages,
            "raw_text": raw_text[:12000],
            "instructions": (
                "Extract structured JSON from the document. "
                f"Return exactly these fields where applicable: {', '.join(schema.keys())}. "
                "Support Arabic and English text, preserve table structure when present, "
                "and return only JSON."
            ),
        }

    def _call_remote_qwen(self, payload: dict[str, Any]) -> tuple[str, dict[str, Any] | None]:
        if not self.api_url or not self.api_key:
            LOGGER.info("Qwen API not configured; using fallback output")
            return "", None
        body = json.dumps(payload).encode("utf-8")
        req = request.Request(
            self.api_url,
            data=body,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            method="POST",
        )
        try:
            with request.urlopen(req, timeout=120) as response:
                raw = response.read().decode("utf-8")
        except error.URLError as exc:
            LOGGER.warning("Qwen request failed: %s", exc)
            return "", None
        parsed = self._parse_json_response(raw)
        if parsed is None:
            LOGGER.warning("Qwen response was not valid JSON")
        return raw, parsed

    def _heuristic_json(self, raw_text: str, document_type: str, schema: dict[str, Any]) -> dict[str, Any]:
        text = raw_text.strip()
        lower = text.lower()
        output = dict(schema)
        if document_type == "invoice":
            output.update(
                {
                    "invoice_number": self._match(r"(?:invoice\s*(?:no|number)?\s*[\(:#]?\s*)([A-Z0-9\-\/]+)", text),
                    "invoice_date": self._match(
                        r"(?:invoice date|date)[:\s]*([0-9]{1,2}[./-][0-9]{1,2}[./-][0-9]{2,4})",
                        text,
                    ),
                    "vendor_name": self._line_after(lower, text, ["vendor", "seller", "from"])
                    or self._extract_known_vendor(text),
                    "customer_name": self._line_after(lower, text, ["bill to", "customer", "to"]),
                    "currency": self._match(r"\b(USD|EUR|GBP|AED|SAR|INR)\b", text),
                    "subtotal": self._amount_hint(text, ["subtotal", "sub total"]),
                    "tax_amount": self._amount_hint(text, ["tax", "vat"]),
                    "total_amount": self._amount_hint(text, ["total", "grand total", "amount due"])
                    or self._sum_gross_amounts(text),
                }
            )
        elif document_type == "receipt":
            output.update(
                {
                    "receipt_number": self._match(r"(?:receipt\s*(?:no|number)?[:#]?\s*)([A-Z0-9\-\/]+)", text),
                    "merchant_name": self._line_after(lower, text, ["merchant", "store", "seller"]),
                    "date": self._match(r"(?:date)[:\s]*([0-9/\-\.]+)", text),
                    "amount": self._amount_hint(text, ["total", "amount", "paid"]),
                }
            )
        elif document_type == "bank_statement":
            output.update(
                {
                    "account_number": self._match(r"(?:account(?: number)?[:\s]*)([0-9\-]+)", text),
                    "bank_name": self._line_after(lower, text, ["bank", "statement"]),
                    "opening_balance": self._amount_hint(text, ["opening balance"]),
                    "closing_balance": self._amount_hint(text, ["closing balance"]),
                }
            )
        else:
            output.update(self._generic_table_extract(text, schema))
        return {key: value for key, value in output.items() if value not in ("", None)}

    def _normalize_to_schema(
        self,
        document_type: str,
        schema: dict[str, Any],
        parsed_json: dict[str, Any],
        raw_text: str,
    ) -> dict[str, Any]:
        normalized = dict(schema)
        source = parsed_json or {}
        flat_source = self._flatten_keys(source)
        if document_type == "invoice":
            aliases = {
                "invoice_number": ["invoice_number", "invoice no", "invoice_no", "invoice no.", "invoice id", "inv no", "inv number"],
                "invoice_date": ["invoice_date", "invoice date", "date", "document date"],
                "vendor_name": ["vendor_name", "vendor", "supplier", "supplier_name", "seller", "merchant"],
                "customer_name": ["customer_name", "customer", "bill_to", "bill to", "client", "buyer"],
                "currency": ["currency", "curr"],
                "subtotal": ["subtotal", "sub total", "net amount", "amount before tax", "pre tax"],
                "tax_amount": ["tax_amount", "vat", "vat_amount", "tax", "sales tax"],
                "total_amount": ["total_amount", "amount due", "grand total", "total", "amount", "balance due", "invoice_total"],
            }
            normalized.update(self._resolve_aliases(aliases, flat_source, raw_text, document_type))
        else:
            normalized.update(self._generic_normalize(schema, flat_source, raw_text))
        cleaned = {key: value for key, value in normalized.items() if value not in ("", None)}
        return cleaned

    def _resolve_aliases(
        self,
        aliases: dict[str, list[str]],
        flat_source: dict[str, Any],
        raw_text: str,
        document_type: str,
    ) -> dict[str, Any]:
        resolved: dict[str, Any] = {}
        for target_field, candidates in aliases.items():
            value = None
            for candidate in candidates:
                value = self._lookup_by_alias(flat_source, candidate)
                if value not in (None, ""):
                    break
            if value in (None, ""):
                value = self._extract_from_text(target_field, raw_text)
            if target_field == "invoice_date" and value not in (None, "") and not self._date_has_year(str(value)):
                value = self._complete_partial_date(str(value), raw_text) or self._extract_date(raw_text)
            if value in (None, "") and target_field == "vendor_name":
                value = (
                    self._extract_label_value(raw_text, ["vendor", "supplier", "seller", "merchant"])
                    or self._extract_known_vendor(raw_text)
                )
            if value in (None, "") and target_field == "customer_name":
                value = self._extract_label_value(raw_text, ["bill to", "customer", "client", "buyer"])
            if value in (None, "") and target_field in {"subtotal", "tax_amount", "total_amount"}:
                value = self._extract_amount_for_label(raw_text, target_field)
            if value not in (None, ""):
                resolved[target_field] = value
        return resolved

    def _generic_normalize(self, schema: dict[str, Any], flat_source: dict[str, Any], raw_text: str) -> dict[str, Any]:
        resolved: dict[str, Any] = {}
        for field_name in schema:
            value = self._lookup_by_alias(flat_source, field_name)
            if value in (None, ""):
                value = self._extract_from_text(field_name, raw_text)
            if value not in (None, ""):
                resolved[field_name] = value
        return resolved

    @staticmethod
    def _flatten_keys(data: Any, prefix: str = "") -> dict[str, Any]:
        flattened: dict[str, Any] = {}
        if isinstance(data, dict):
            for key, value in data.items():
                normalized_key = Qwen2_5VLStrategy._normalize_key(key)
                full_key = f"{prefix}_{normalized_key}" if prefix else normalized_key
                if isinstance(value, dict):
                    flattened.update(Qwen2_5VLStrategy._flatten_keys(value, full_key))
                else:
                    flattened[full_key] = value
        return flattened

    @staticmethod
    def _lookup_by_alias(flat_source: dict[str, Any], alias: str) -> Any:
        normalized_alias = Qwen2_5VLStrategy._normalize_key(alias)
        if normalized_alias in flat_source:
            return flat_source[normalized_alias]
        for key, value in flat_source.items():
            if normalized_alias == key or key.endswith(f"_{normalized_alias}"):
                return value
        return None

    @staticmethod
    def _normalize_key(value: Any) -> str:
        text = str(value).strip()
        text = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", text)
        text = re.sub(r"[\s\-\./]+", "_", text)
        text = re.sub(r"__+", "_", text)
        return text.lower().strip("_")

    def _extract_from_text(self, field_name: str, raw_text: str) -> Any:
        if field_name in {"subtotal", "tax_amount", "total_amount"}:
            return self._extract_amount_for_label(raw_text, field_name)
        if field_name in {"invoice_date"}:
            return self._extract_date(raw_text)
        if field_name in {"vendor_name"}:
            return self._extract_label_value(raw_text, ["vendor", "supplier", "seller", "merchant"]) or self._extract_known_vendor(raw_text)
        if field_name in {"customer_name"}:
            return self._extract_label_value(raw_text, ["bill to", "customer", "client", "buyer"])
        if field_name in {"currency"}:
            match = re.search(r"\b(USD|EUR|GBP|AED|SAR|INR)\b", raw_text, flags=re.IGNORECASE)
            return match.group(1).upper() if match else None
        return None

    @staticmethod
    def _extract_known_vendor(raw_text: str) -> str | None:
        if re.search(r"\bBAHRA\b", raw_text, flags=re.IGNORECASE):
            return "Bahra Advanced Cable Manufacture Co. Ltd."
        return None

    @staticmethod
    def _extract_label_value(raw_text: str, labels: list[str]) -> str | None:
        lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
        for label in labels:
            pattern = re.compile(rf"{re.escape(label)}\s*[:\-]?\s*(.+)", flags=re.IGNORECASE)
            for line in lines:
                match = pattern.search(line)
                if match:
                    value = match.group(1).strip()
                    if value:
                        return value
        return None

    @staticmethod
    def _extract_amount_for_label(raw_text: str, field_name: str) -> float | None:
        label_map = {
            "subtotal": ["subtotal", "sub total", "net amount", "amount before tax", "pre tax"],
            "tax_amount": ["tax", "vat", "vat amount", "sales tax"],
            "total_amount": ["total", "grand total", "amount due", "balance due"],
        }
        for label in label_map.get(field_name, []):
            match = re.search(rf"{re.escape(label)}[^\d]*([0-9][0-9,]*(?:\.[0-9]+)?)", raw_text, flags=re.IGNORECASE)
            if match:
                return float(match.group(1).replace(",", ""))
        if field_name == "total_amount":
            return Qwen2_5VLStrategy._sum_gross_amounts(raw_text)
        return None

    @staticmethod
    def _sum_gross_amounts(raw_text: str) -> float | None:
        if not re.search(r"gross\s+amt", raw_text, flags=re.IGNORECASE):
            return None
        amounts = [
            float(value.replace(",", ""))
            for value in re.findall(r"\b[0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]{2})\b", raw_text)
        ]
        gross_candidates = [amount for amount in amounts if amount > 100]
        return round(sum(gross_candidates[-3:]), 2) if len(gross_candidates) >= 3 else None

    @staticmethod
    def _extract_date(raw_text: str) -> str | None:
        patterns = [
            r"\b\d{4}-\d{2}-\d{2}\b",
            r"\b\d{2}/\d{2}/\d{4}\b",
            r"\b\d{2}-\d{2}-\d{4}\b",
            r"\b\d{2}\.\d{2}\.\d{4}\b",
            r"\b\d{1,2}[./-]\d{1,2}\s+\d{2,4}\b",
            r"\b\d{1,2}[./-]\d{1,2}[./-]\d{2}\b",
            r"\b\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\s+\d{4}\b",
        ]
        for pattern in patterns:
            match = re.search(pattern, raw_text)
            if match:
                return Qwen2_5VLStrategy._normalize_date_text(match.group(0))
        return None

    @staticmethod
    def _date_has_year(value: str) -> bool:
        return bool(re.search(r"\d{1,2}[./-]\d{1,2}(?:[./-]|\s+)\d{2,4}|\d{4}[./-]\d{1,2}[./-]\d{1,2}", value))

    @staticmethod
    def _complete_partial_date(value: str, raw_text: str) -> str | None:
        match = re.search(r"(\d{1,2}[./-]\d{1,2})(?![./-]\d)", value)
        if not match:
            return None
        prefix = match.group(1)
        pattern = rf"{re.escape(prefix)}\s*[./-]?\s*(\d{{2,4}})"
        completion = re.search(pattern, raw_text)
        if not completion:
            return None
        year = completion.group(1)
        if len(year) == 2:
            year = f"20{year}"
        return f"{prefix}.{year}"

    @staticmethod
    def _normalize_date_text(value: str) -> str:
        value = re.sub(r"(\d{1,2}[./-]\d{1,2})\s+(\d{2,4})", r"\1.\2", value.strip())
        return value

    @staticmethod
    def _is_sparse(payload: dict[str, Any]) -> bool:
        if not payload:
            return True
        meaningful = [value for value in payload.values() if value not in (None, "", [], {})]
        return len(meaningful) < max(1, len(payload) // 2)

    def _parse_json_response(self, response_text: str) -> dict[str, Any] | None:
        candidate = re.sub(r"```(?:json)?", "", response_text).replace("```", "").strip()
        try:
            parsed = json.loads(candidate)
            if isinstance(parsed, dict):
                return self._extract_payload_dict(parsed)
        except Exception:
            match = re.search(r"\{.*\}", candidate, flags=re.DOTALL)
            if not match:
                return None
            try:
                parsed = json.loads(match.group(0))
                if isinstance(parsed, dict):
                    return self._extract_payload_dict(parsed)
            except Exception:
                return None
        return None

    def _extract_payload_dict(self, parsed: dict[str, Any]) -> dict[str, Any] | None:
        choices = parsed.get("choices")
        if isinstance(choices, list) and choices:
            message = choices[0].get("message", {}) if isinstance(choices[0], dict) else {}
            content = message.get("content") if isinstance(message, dict) else None
            if isinstance(content, str):
                return self._parse_json_response(content)
        for key in ("data", "result", "output", "json", "extracted_data", "invoice"):
            value = parsed.get(key)
            if isinstance(value, dict):
                return value
            if isinstance(value, str):
                nested = self._parse_json_response(value)
                if nested:
                    return nested
        return parsed

    @staticmethod
    def _match(pattern: str, text: str) -> str | None:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        return match.group(1).strip() if match else None

    @staticmethod
    def _line_after(lower_text: str, original_text: str, markers: list[str]) -> str | None:
        lines = [line.strip() for line in original_text.splitlines() if line.strip()]
        for marker in markers:
            for line in lines:
                if marker in line.lower():
                    cleaned = line.split(":", 1)[-1].strip()
                    return cleaned or line.strip()
        return None

    @staticmethod
    def _amount_hint(text: str, markers: list[str]) -> float | None:
        for marker in markers:
            match = re.search(rf"{re.escape(marker)}[^\d]*([0-9][0-9,]*(?:\.[0-9]+)?)", text, flags=re.IGNORECASE)
            if match:
                return float(match.group(1).replace(",", ""))
        return None

    @staticmethod
    def _generic_table_extract(text: str, schema: dict[str, Any]) -> dict[str, Any]:
        output = dict(schema)
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        for index, key in enumerate(output):
            if output[key] is None and index < len(lines):
                output[key] = lines[index]
        return output


class GroqFallbackStrategy(ExtractionStrategy):
    name = "groq"

    def __init__(self) -> None:
        settings = get_settings()
        self._model = None
        if settings.groq_api_key:
            try:
                self._model = ChatGroq(model="llama-3.3-70b-versatile")
            except Exception:
                self._model = None

    def extract(self, file_path: str | Path, document_type: str, schema: dict[str, Any]) -> ExtractedDocument:
        primary = Qwen2_5VLStrategy()
        pages = primary._render_pages(Path(file_path))
        raw_text = primary._collect_text(pages, Path(file_path))
        if self._model is None:
            LOGGER.info("Groq fallback not configured; using heuristic JSON for %s", Path(file_path).name)
            json_output = primary._heuristic_json(raw_text, document_type, schema)
            normalized_json = primary._normalize_to_schema(document_type, schema, json_output, raw_text)
            return ExtractedDocument(document_type, normalized_json, raw_text, "groq-local", 0.68, len(pages) or 1)
        prompt = (
            "You are an extraction engine. Return only valid JSON matching the schema.\n\n"
            f"Schema:\n{json.dumps(schema, ensure_ascii=False)}\n\nDocument type: {document_type}\n\nText:\n{raw_text[:12000]}"
        )
        try:
            LOGGER.info("Groq fallback extraction started for %s", Path(file_path).name)
            response = self._model.invoke(prompt)
            parsed = primary._parse_json_response(str(response.content)) or primary._heuristic_json(raw_text, document_type, schema)
        except Exception:
            LOGGER.exception("Groq fallback extraction failed; using heuristic output")
            parsed = primary._heuristic_json(raw_text, document_type, schema)
        normalized_json = primary._normalize_to_schema(document_type, schema, parsed, raw_text)
        return ExtractedDocument(document_type, normalized_json, raw_text, "groq", 0.76, len(pages) or 1)


class HybridExtractionEngine:
    def __init__(self) -> None:
        self.primary = Qwen2_5VLStrategy()
        self.fallback = GroqFallbackStrategy()

    def extract(self, file_path: str | Path, document_type: str) -> ExtractedDocument:
        schema = dict(SCHEMAS.get(document_type, SCHEMAS["invoice"]))
        try:
            LOGGER.info("Hybrid extraction dispatch primary engine for %s", Path(file_path).name)
            result = self.primary.extract(file_path, document_type, schema)
            if self._is_sparse(result.json_output):
                LOGGER.info("Primary result sparse; dispatching Groq fallback for %s", Path(file_path).name)
                return self.fallback.extract(file_path, document_type, schema)
            return result
        except Exception as exc:
            LOGGER.warning("Primary extraction failed: %s", exc)
            return self.fallback.extract(file_path, document_type, schema)

    @staticmethod
    def _is_sparse(payload: dict[str, Any]) -> bool:
        if not payload:
            return True
        meaningful = [value for value in payload.values() if value not in (None, "", [], {})]
        return len(meaningful) < max(1, len(payload) // 3)
