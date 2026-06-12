from __future__ import annotations

import os
from pathlib import Path

import easyocr
import fitz


reader = easyocr.Reader(["en", "ar"], gpu=False)

IMAGE_EXTENSIONS = [
    ".png",
    ".jpg",
    ".jpeg",
    ".bmp",
    ".tiff",
    ".webp",
]


def extract_text(file_path: str) -> str:
    ext = os.path.splitext(file_path)[1].lower()

    if ext in IMAGE_EXTENSIONS:
        result = reader.readtext(file_path, detail=0)
        return "\n".join(result)

    text = ""
    doc = fitz.open(file_path)

    for page_num in range(len(doc)):
        page = doc[page_num]
        pix = page.get_pixmap()
        image_file = Path(f"temp_{page_num}.png")
        pix.save(str(image_file))
        try:
            result = reader.readtext(str(image_file), detail=0)
            text += "\n".join(result)
        finally:
            if image_file.exists():
                image_file.unlink()

    return text
