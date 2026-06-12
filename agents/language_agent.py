from __future__ import annotations

import re


def detect_language(text: str) -> str:
    arabic = len(re.findall(r"[\u0600-\u06FF]", text))
    latin = len(re.findall(r"[A-Za-z]", text))
    if arabic > 50 and latin > 10:
        return "mixed"
    if arabic > 50:
        return "arabic"
    return "english"
