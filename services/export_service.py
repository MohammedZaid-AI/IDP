from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from services.settings import get_settings


LOGGER = logging.getLogger(__name__)


class ExportService:
    def __init__(self) -> None:
        self.settings = get_settings()

    def export_records(self, records: list[dict[str, Any]], export_format: str = "xlsx", filename: str = "documents") -> Path:
        export_dir = self.settings.exports_dir
        export_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        target = export_dir / f"{filename}_{timestamp}.{export_format}"
        dataframe = pd.DataFrame(records)

        if export_format == "csv":
            dataframe.to_csv(target, index=False)
        elif export_format == "json":
            target.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
        else:
            dataframe.to_excel(target, index=False)
        return target

    def export_uploaded_records(self, records: list[dict[str, Any]], filename: str) -> Path:
        export_dir = self.settings.exports_dir
        export_dir.mkdir(parents=True, exist_ok=True)
        target = export_dir / f"{filename}.xlsx"
        print(f"Documents processed: {len(records)}")
        print(records)
        
        # Map raw keys to the exact 14 columns requested
        mapped_records = []
        for record in records:
            mapped_records.append({
                "Filename": record.get("filename", ""),
                "Document Number": record.get("document_number") or "",
                "VAT Number": record.get("vat_number") or "",
                "Document Date": record.get("document_date") or "",
                "Currency": record.get("currency") or "",
                "Vendor Name Arabic": record.get("vendor_name_ar") or "",
                "Vendor Name English": record.get("vendor_name_en") or "",
                "Customer Name Arabic": record.get("customer_name_ar") or "",
                "Customer Name English": record.get("customer_name_en") or "",
                "Address Arabic": record.get("address_ar") or "",
                "Address English": record.get("address_en") or "",
                "Subtotal": record.get("subtotal"),
                "Tax Amount": record.get("tax_amount"),
                "Total Amount": record.get("total_amount"),
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
                worksheet.column_dimensions[col_letter].width = max(max_len + 3, 10)
        LOGGER.info("Excel generated path: %s (exists=%s)", target.resolve(), target.exists())
        return target



class InvoiceExcelMapper:
    COLUMNS = [
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

    @classmethod
    def to_row(cls, payload: dict[str, Any]) -> dict[str, Any]:
        legacy_vendor = payload.get("vendor_name")
        legacy_customer = payload.get("customer_name")
        return {
            "document_number": payload.get("document_number"),
            "vat_number": payload.get("vat_number"),
            "document_date": payload.get("document_date"),
            "currency": payload.get("currency"),
            "vendor_name_ar": payload.get("vendor_name_ar", ""),
            "vendor_name_en": payload.get("vendor_name_en", legacy_vendor),
            "customer_name_ar": payload.get("customer_name_ar", ""),
            "customer_name_en": payload.get("customer_name_en", legacy_customer),
            "address_ar": payload.get("address_ar", ""),
            "address_en": payload.get("address_en", ""),
            "subtotal": payload.get("subtotal"),
            "tax_amount": payload.get("tax_amount"),
            "total_amount": payload.get("total_amount"),
        }
