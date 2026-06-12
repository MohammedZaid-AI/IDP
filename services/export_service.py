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
        dataframe = self._dataframe_with_metadata_first(records)

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

    @staticmethod
    def _dataframe_with_metadata_first(records: list[dict[str, Any]]) -> pd.DataFrame:
        dataframe = pd.DataFrame(records)
        leading_columns = [column for column in ("filename", "document_type") if column in dataframe.columns]
        remaining_columns = [column for column in dataframe.columns if column not in leading_columns]
        return dataframe.reindex(columns=leading_columns + remaining_columns)
