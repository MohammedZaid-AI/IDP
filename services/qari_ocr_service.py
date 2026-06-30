from __future__ import annotations

import sys
try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except Exception:
    pass

import base64
import json
import logging
import time
import os
import re
import html
from html.parser import HTMLParser
from io import BytesIO
from pathlib import Path
from typing import Any

import fitz  # PyMuPDF
from PIL import Image, ImageOps
import httpx
import numpy as np

from services.settings import get_settings

LOGGER = logging.getLogger(__name__)

QARI_PROMPT = """You are an OCR engine.

Your only job is to read the document.

Return ONLY the visible text exactly as it appears.

Requirements:

- Preserve Arabic exactly.
- Preserve English exactly.
- Preserve numbers exactly.
- Preserve reading order.
- Preserve line breaks.
- Preserve labels and values.

Do NOT interpret the document.

Do NOT summarize.

Do NOT classify.

Do NOT translate.

Do NOT generate HTML.

Do NOT generate XML.

Do NOT generate Markdown.

Do NOT generate JSON.

Do NOT generate tables.

Do NOT generate bounding boxes.

Do NOT generate layout tags.

Return only plain UTF-8 text."""


class HTMLTextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.result = []
        self.block_tags = {
            'p', 'div', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 
            'li', 'tr', 'table', 'br', 'section', 'body', 'html'
        }

    def handle_starttag(self, tag, attrs):
        if tag in self.block_tags:
            if self.result and not self.result[-1].endswith('\n'):
                self.result.append('\n')

    def handle_endtag(self, tag):
        if tag in self.block_tags:
            if self.result and not self.result[-1].endswith('\n'):
                self.result.append('\n')

    def handle_data(self, data):
        self.result.append(data)


def strip_html_if_present(text: str) -> tuple[str, bool]:
    has_html = False
    if "<" in text and ">" in text:
        if re.search(r'</?[a-zA-Z][^>]*>', text):
            has_html = True
            
    if not has_html:
        return text, False

    try:
        parser = HTMLTextExtractor()
        parser.feed(text)
        parsed_text = "".join(parser.result)
        parsed_text = re.sub(r'\n{3,}', '\n\n', parsed_text)
        return parsed_text.strip(), True
    except Exception:
        cleaned = re.sub(r'<[^>]+>', '\n', text)
        cleaned = html.unescape(cleaned)
        cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
        return cleaned.strip(), True


def clean_ocr(text: str) -> str:
    if not text:
        return ""
    lines = text.splitlines()
    cleaned_lines = []
    prev_line = None
    for line in lines:
        cleaned_line = re.sub(r'[ \t\xa0\u2000-\u200a\u202f\u205f\u3000]+', ' ', line).strip()
        if prev_line is not None and cleaned_line == prev_line:
            continue
        cleaned_lines.append(cleaned_line)
        prev_line = cleaned_line
    return "\n".join(cleaned_lines).strip()


def count_lines_projection(img: Image.Image) -> int:
    img_gray = img.convert('L')
    img_inv = ImageOps.invert(img_gray)
    arr = np.array(img_inv)
    horizontal_sum = np.sum(arr, axis=1)
    
    max_val = np.max(horizontal_sum)
    if max_val == 0:
        return 0
    threshold = max_val * 0.05
    text_lines = horizontal_sum > threshold
    
    transitions = 0
    in_text = False
    for val in text_lines:
        if val and not in_text:
            transitions += 1
            in_text = True
        elif not val and in_text:
            in_text = False
            
    return transitions


class QariOCRService:
    """Extracts text from document images using local Qari-OCR model via Ollama."""

    def __init__(self) -> None:
        settings = get_settings()
        self.url = settings.ollama_url.rstrip("/")
        self.model = "hf.co/mradermacher/Qari-OCR-0.2.2.1-VL-2B-Instruct-merged-GGUF:Q4_K_M"

    def ensure_initialized(self) -> None:
        try:
            res = httpx.get(f"{self.url}/api/tags", timeout=5.0)
            if res.status_code == 200:
                models = res.json().get("models", [])
                any(m.get("name") == self.model or m.get("name", "").startswith(f"{self.model}:") for m in models)
        except Exception:
            pass

    def _run_qari_on_image(self, img: Image.Image, prompt: str, num_predict: int) -> tuple[str, str, int]:
        w, h = img.size
        max_size = 1024
        if max(w, h) > max_size:
            scale = max_size / max(w, h)
            img = img.resize((int(w * scale), int(h * scale)), Image.Resampling.LANCZOS if hasattr(Image, "Resampling") else Image.LANCZOS)
        
        buffered = BytesIO()
        img.save(buffered, format="PNG")
        b64_bytes = buffered.getvalue()
        b64_str = base64.b64encode(b64_bytes).decode("ascii")

        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": prompt,
                    "images": [b64_str],
                }
            ],
            "stream": True,
            "options": {
                "temperature": 0.0,
                "num_predict": num_predict,
            }
        }

        full_content = []
        eval_count = 0
        done_reason = "stop"

        try:
            with httpx.Client(timeout=300.0) as client:
                with client.stream("POST", f"{self.url}/api/chat", json=payload) as response:
                    if response.status_code == 200:
                        for line in response.iter_lines():
                            if not line:
                                continue
                            try:
                                parsed = json.loads(line)
                                token = parsed.get("message", {}).get("content", "")
                                if token:
                                    full_content.append(token)
                                if parsed.get("done", False):
                                    eval_count = parsed.get("eval_count", 0)
                                    done_reason = parsed.get("done_reason", "stop")
                            except Exception:
                                pass
                    else:
                        LOGGER.error("Qari OCR API failed: status=%d", response.status_code)
        except Exception as exc:
            LOGGER.error("Qari OCR request failed: %s", exc)

        content = "".join(full_content).strip()
        stripped_content, _ = strip_html_if_present(content)
        cleaned_content = clean_ocr(stripped_content)
        
        return cleaned_content, done_reason, (eval_count or len(full_content))

    def extract_text(self, file_path: str | Path) -> str:
        file_path = Path(file_path)
        LOGGER.info("Qari OCR started file=%s", file_path.name)

        pages = self._render_pages(file_path)
        
        header_texts = []
        body_texts = []
        footer_texts = []
        
        total_tokens = 0
        final_done_reason = "stop"
        
        total_raw_len = 0
        total_comp_len = 0
        total_header_len = 0
        total_body_len = 0
        total_footer_len = 0
        
        for idx, img in enumerate(pages):
            w, h = img.size
            
            # Crop regions
            header_crop = img.crop((0, 0, w, int(h * 0.35)))
            body_crop = img.crop((0, int(h * 0.30), w, int(h * 0.75)))
            footer_crop = img.crop((0, int(h * 0.70), w, h))
            
            # Run Header OCR (only on first page for multi-page)
            header_text = ""
            if idx == 0:
                header_text, h_reason, h_tokens = self._run_qari_on_image(header_crop, QARI_PROMPT, 500)
                total_tokens += h_tokens
                if h_reason == "length":
                    final_done_reason = "length"
            
            # Run Footer OCR (only on last page)
            footer_text = ""
            if idx == len(pages) - 1:
                footer_text, f_reason, f_tokens = self._run_qari_on_image(footer_crop, QARI_PROMPT, 500)
                total_tokens += f_tokens
                if f_reason == "length":
                    final_done_reason = "length"
            
            # Run Body OCR (on all pages) to extract table headers
            body_text, b_reason, b_tokens = self._run_qari_on_image(
                body_crop, 
                "You are an OCR engine. Transcribe ONLY the table headers (e.g. Description, Qty, Unit Price, Amount) and the first 2 rows of the product table, then stop. Do not transcribe other product rows.",
                200
            )
            total_tokens += b_tokens
                
            # Count lines in Body crop using projection profile
            total_lines = count_lines_projection(body_crop)
            
            # Compress body
            body_lines = body_text.splitlines()
            table_keywords = [
                "description", "qty", "quantity", "unit price", "amount", "price", "item", "desc", "amt",
                "الوصف", "الكمية", "سعر", "الاجمالي", "السعر", "البيان"
            ]
            has_table = any(any(kw in line.lower() for kw in table_keywords) for line in body_lines)
            
            if has_table and len(body_lines) > 0:
                lines_kept = min(len(body_lines), 3)
                header_and_first_rows = body_lines[:lines_kept]
                removed_rows = max(1, total_lines - lines_kept)
                compressed_body = "\n".join(header_and_first_rows) + f"\n[PRODUCT TABLE REMOVED - {removed_rows} ROWS]"
            else:
                compressed_body = body_text
                
            if header_text:
                header_texts.append(header_text)
            body_texts.append(compressed_body)
            if footer_text:
                footer_texts.append(footer_text)
                
            total_raw_len += len(header_text) + len(body_text) + len(footer_text)
            total_header_len += len(header_text)
            total_body_len += len(compressed_body)
            total_footer_len += len(footer_text)

        # Format final text
        combined_header = "\n".join(header_texts).strip()
        combined_body = "\n".join(body_texts).strip()
        combined_footer = "\n".join(footer_texts).strip()
        
        formatted_text = f"""========== HEADER ==========
{combined_header}
========== BODY ==========
{combined_body}
========== FOOTER ==========
{combined_footer}"""

        total_comp_len = len(formatted_text)

        # Debug logging as required by the user
        print(f"Raw OCR length: {total_raw_len}", flush=True)
        print(f"Compressed OCR length: {total_comp_len}", flush=True)
        print(f"Header length: {total_header_len}", flush=True)
        print(f"Body length: {total_body_len}", flush=True)
        print(f"Footer length: {total_footer_len}", flush=True)
        print(f"Generation tokens used: {total_tokens}", flush=True)
        print(f"done_reason: {final_done_reason}", flush=True)
        print("", flush=True)

        return formatted_text

    def _render_pages(self, file_path: Path) -> list[Image.Image]:
        ext = file_path.suffix.lower()
        if ext == ".pdf":
            doc = fitz.open(str(file_path))
            images = []
            for page in doc:
                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
                images.append(Image.open(BytesIO(pix.tobytes("png"))).convert("RGB"))
            return images
        return [Image.open(file_path).convert("RGB")]
