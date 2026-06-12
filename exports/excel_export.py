from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from services.settings import get_settings


def export_excel(data: str | dict[str, Any] | list[dict[str, Any]], mode: str) -> str:
    parsed = json.loads(data) if isinstance(data, str) else data
    records = parsed if isinstance(parsed, list) else [parsed]
    print(f"Documents processed: {len(records)}")
    print(records)
    frame = pd.DataFrame(records)
    settings = get_settings()
    target = settings.exports_dir / ("master.xlsx" if mode == "Append To Master Excel" else "output.xlsx")
    frame.to_excel(target, index=False)
    return str(target)
