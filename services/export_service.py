from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from services.settings import get_settings


LOGGER = logging.getLogger(__name__)


def map_to_canonical(extracted: dict) -> dict:
    if not isinstance(extracted, dict):
        return {}

    def get_path(d, path_str):
        parts = path_str.split('.')
        curr = d
        for p in parts:
            if isinstance(curr, dict) and p in curr:
                curr = curr[p]
            else:
                return None
        return curr

    # Resolve flat or nested options
    doc_num = get_path(extracted, "document.number") or extracted.get("document_number") or extracted.get("invoice_number") or extracted.get("number")
    
    vendor_name_en = get_path(extracted, "vendor.name_en") or extracted.get("vendor_name_en")
    vendor_name_ar = get_path(extracted, "vendor.name_ar") or extracted.get("vendor_name_ar")
    
    customer_name_en = get_path(extracted, "customer.name_en") or extracted.get("customer_name_en")
    customer_name_ar = get_path(extracted, "customer.name_ar") or extracted.get("customer_name_ar")
    
    address_ar = get_path(extracted, "vendor.address_ar") or get_path(extracted, "address_ar") or extracted.get("address_ar")
    address_en = get_path(extracted, "vendor.address_en") or get_path(extracted, "address_en") or extracted.get("address_en")

    doc_date = get_path(extracted, "document.date") or extracted.get("document_date") or extracted.get("date") or extracted.get("invoice_date")
    currency = get_path(extracted, "document.currency") or extracted.get("currency")
    
    from services.qwen_llm_extractor import normalize_number
    subtotal = normalize_number(get_path(extracted, "financials.subtotal") or extracted.get("subtotal"))
    tax_amount = normalize_number(get_path(extracted, "financials.tax_amount") or extracted.get("tax_amount") or extracted.get("vat") or extracted.get("vat_amount"))
    total_amount = normalize_number(get_path(extracted, "financials.total_amount") or extracted.get("total_amount") or extracted.get("grand_total"))

    purchase_order = get_path(extracted, "metadata.purchase_order") or extracted.get("purchase_order") or extracted.get("po_number")
    reference_number = get_path(extracted, "metadata.reference_number") or extracted.get("reference_number")
    doc_type = extracted.get("document_type") or extracted.get("type") or "invoice"
    
    return {
        "document_number": str(doc_num or "").strip(),
        "vendor_name_ar": str(vendor_name_ar or "").strip(),
        "vendor_name_en": str(vendor_name_en or "").strip(),
        "customer_name_ar": str(customer_name_ar or "").strip(),
        "customer_name_en": str(customer_name_en or "").strip(),
        "address_ar": str(address_ar or "").strip(),
        "address_en": str(address_en or "").strip(),
        "document_date": str(doc_date or "").strip(),
        "currency": str(currency or "").strip(),
        "subtotal": subtotal,
        "tax_amount": tax_amount,
        "total_amount": total_amount,
        "purchase_order": str(purchase_order or "").strip(),
        "reference_number": str(reference_number or "").strip(),
        "document_type": str(doc_type or "").strip(),
    }


class ExportService:
    def __init__(self) -> None:
        self.settings = get_settings()

    def export_records(self, records: list[dict[str, Any]], export_format: str = "xlsx", filename: str = "documents") -> Path:
        export_dir = self.settings.exports_dir
        export_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        target = export_dir / f"{filename}_{timestamp}.{export_format}"
        
        mapped_records = []
        for record in records:
            ext_json = record.get("json_output", {})
            if isinstance(ext_json, str):
                try:
                    ext_json = json.loads(ext_json)
                except Exception:
                    ext_json = {}
            
            canonical = map_to_canonical(ext_json)
            # Add other business keys if mapped flat
            if not canonical.get("document_number") and record.get("document_number"):
                canonical["document_number"] = record["document_number"]
            if not canonical.get("document_type") and record.get("document_type"):
                canonical["document_type"] = record["document_type"]
                
            mapped_records.append({
                "Vendor Name (Arabic)": canonical.get("vendor_name_ar", ""),
                "Vendor Name (English)": canonical.get("vendor_name_en", ""),
                "Customer Name (Arabic)": canonical.get("customer_name_ar", ""),
                "Customer Name (English)": canonical.get("customer_name_en", ""),
                "Address (Arabic)": canonical.get("address_ar", ""),
                "Address (English)": canonical.get("address_en", ""),
                "Invoice Number": canonical.get("document_number", ""),
                "Invoice Date": canonical.get("document_date", ""),
                "Currency": canonical.get("currency", ""),
                "Subtotal": canonical.get("subtotal"),
                "VAT": canonical.get("tax_amount"),
                "Total": canonical.get("total_amount"),
                "Purchase Order": canonical.get("purchase_order", ""),
                "Reference Number": canonical.get("reference_number", ""),
                "Document Type": canonical.get("document_type", "invoice"),
            })
        
        dataframe = pd.DataFrame(mapped_records)

        if export_format == "csv":
            dataframe.to_csv(target, index=False)
        elif export_format == "json":
            target.write_text(json.dumps(mapped_records, ensure_ascii=False, indent=2), encoding="utf-8")
        else:
            dataframe.to_excel(target, index=False)
        return target

    def export_uploaded_records(self, records: list[dict[str, Any]], filename: str) -> Path:
        export_dir = self.settings.exports_dir
        export_dir.mkdir(parents=True, exist_ok=True)
        target = export_dir / f"{filename}.xlsx"
        
        mapped_records = []
        for record in records:
            mapped_records.append({
                "Vendor Name (Arabic)": record.get("vendor_name_ar") or "",
                "Vendor Name (English)": record.get("vendor_name_en") or "",
                "Customer Name (Arabic)": record.get("customer_name_ar") or "",
                "Customer Name (English)": record.get("customer_name_en") or "",
                "Address (Arabic)": record.get("address_ar") or "",
                "Address (English)": record.get("address_en") or "",
                "Invoice Number": record.get("document_number") or "",
                "Invoice Date": record.get("document_date") or "",
                "Currency": record.get("currency") or "",
                "Subtotal": record.get("subtotal"),
                "VAT": record.get("tax_amount"),
                "Total": record.get("total_amount"),
                "Purchase Order": record.get("purchase_order") or "",
                "Reference Number": record.get("reference_number") or "",
                "Document Type": record.get("document_type") or "invoice",
            })
        dataframe = pd.DataFrame(mapped_records)

        with pd.ExcelWriter(target, engine="openpyxl") as writer:
            dataframe.to_excel(writer, index=False, sheet_name="Sheet1")
            
            workbook = writer.book
            worksheet = writer.sheets["Sheet1"]
            
            # Header row bold
            from openpyxl.styles import Font
            bold_font = Font(bold=True)
            for col in range(1, len(dataframe.columns) + 1):
                cell = worksheet.cell(row=1, column=col)
                cell.font = bold_font
            
            # Auto-size columns
            for col in worksheet.columns:
                max_len = 0
                for cell in col:
                    val_str = str(cell.value or "")
                    if len(val_str) > max_len:
                        max_len = len(val_str)
                col_letter = col[0].column_letter
                worksheet.column_dimensions[col_letter].width = max(max_len + 3, 12)
        LOGGER.info("Excel generated path: %s (exists=%s)", target.resolve(), target.exists())
        return target


class InvoiceExcelMapper:
    COLUMNS = [
        "document_number",
        "vendor_name_ar",
        "vendor_name_en",
        "customer_name_ar",
        "customer_name_en",
        "address_ar",
        "address_en",
        "document_date",
        "currency",
        "subtotal",
        "tax_amount",
        "total_amount",
        "purchase_order",
        "reference_number",
        "document_type",
    ]

    @classmethod
    def to_row(cls, payload: dict[str, Any]) -> dict[str, Any]:
        canonical = map_to_canonical(payload)
        return canonical
