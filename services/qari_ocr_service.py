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


from rapidfuzz import fuzz

HEADER_KEYWORDS = [
    r'\bdescription\b', r'\bqty\b', r'\bquantity\b', r'\bunit\s*price\b', 
    r'\bamount\b', r'\bprice\b', r'\bdesc\b', r'\bamt\b', r'\bitem\b',
    r'\bالوصف\b', r'\bالكمية\b', r'\bسعر\s*الوحدة\b', r'\bالاجمالي\b', 
    r'\bالسعر\b', r'\bالبيان\b', r'\bتفاصيل\b', r'\bالمادة\b'
]

FOOTER_KEYWORDS = [
    r'\bsubtotal\b', r'\bvat\b', r'\btax\b', r'\btotal\b', r'\bdiscount\b', 
    r'\bnet\s*amount\b', r'\bgrand\s*total\b', r'\bamount\s*due\b', r'\bpay\b',
    r'\bالاجمالي\b', r'\bالصافي\b', r'\bالضريبة\b', r'\bالمجموع\b', 
    r'\bقيمة\s*الضريبة\b', r'\bالمبلغ\s*الخاضع\b'
]

def compress_repeating_line_content(line: str) -> str:
    # Collapse repeating phrases inside a single line
    words = line.split()
    if len(words) > 10:
        unique_words = set(words)
        if len(unique_words) / len(words) < 0.3:
            seen = set()
            unique_ordered = []
            for w in words:
                if w not in seen:
                    unique_ordered.append(w)
                    seen.add(w)
            return " ".join(unique_ordered) + " [REPETITIVE WORDS REMOVED]"
            
    if len(re.findall(r'\b\d+\b', line)) > 15:
        return re.sub(r'(\d+[, ]\s*){10,}', r'\1... [REPETITIVE NUMBERS REMOVED] ... ', line)
        
    return line

def compress_table_rows(lines: list[str]) -> tuple[list[str], int]:
    if not lines:
        return [], 0
        
    compressed = []
    i = 0
    removed_count = 0
    
    while i < len(lines):
        line = lines[i].strip()
        if not line:
            compressed.append(line)
            i += 1
            continue
            
        match_count = 0
        for j in range(i + 1, len(lines)):
            next_line = lines[j].strip()
            if not next_line:
                continue
                
            sim = fuzz.ratio(line, next_line)
            threshold = 75.0 if len(line) > 5 else 90.0
            
            is_match = False
            if sim >= threshold:
                is_match = True
            elif (len(line) > 10 and next_line in line) or (len(next_line) > 10 and line in next_line):
                is_match = True
            else:
                line_digits = len(re.findall(r'\d+', line))
                next_digits = len(re.findall(r'\d+', next_line))
                if line_digits > 0 and next_digits > 0 and abs(line_digits - next_digits) <= 1:
                    if abs(len(line) - len(next_line)) < 10:
                        is_match = True
            
            if is_match:
                match_count += 1
            else:
                break
                
        if match_count >= 2:
            compressed.append(f"[PRODUCT TABLE REMOVED - {match_count + 1} ROWS]")
            removed_count += (match_count + 1)
            i += match_count + 1
        else:
            compressed.append(lines[i])
            i += 1
            
    return compressed, removed_count

def split_ocr_regions_inline(text: str) -> tuple[str, str, str]:
    table_start_idx = -1
    for kw in HEADER_KEYWORDS:
        match = re.search(kw, text, re.IGNORECASE)
        if match:
            idx = match.start()
            if table_start_idx == -1 or idx < table_start_idx:
                table_start_idx = idx
                
    if table_start_idx == -1:
        table_start_idx = int(len(text) * 0.3)
        
    footer_start_idx = -1
    for kw in FOOTER_KEYWORDS:
        match = re.search(kw, text[table_start_idx:], re.IGNORECASE)
        if match:
            idx = table_start_idx + match.start()
            if footer_start_idx == -1 or idx < footer_start_idx:
                footer_start_idx = idx
                
    if footer_start_idx == -1:
        for kw in FOOTER_KEYWORDS:
            matches = list(re.finditer(kw, text, re.IGNORECASE))
            if matches:
                idx = matches[-1].start()
                if footer_start_idx == -1 or idx > footer_start_idx:
                    footer_start_idx = idx
                    
    if footer_start_idx == -1 or footer_start_idx <= table_start_idx:
        footer_start_idx = int(len(text) * 0.75)
        
    if table_start_idx >= footer_start_idx:
        table_start_idx = int(len(text) * 0.3)
        footer_start_idx = int(len(text) * 0.75)
        
    header_text = text[:table_start_idx].strip()
    body_text = text[table_start_idx:footer_start_idx].strip()
    footer_text = text[footer_start_idx:].strip()
    
    return header_text, body_text, footer_text

def split_ocr_regions(lines: list[str]) -> tuple[list[str], list[str], list[str]]:
    n = len(lines)
    if n == 0:
        return [], [], []
        
    if n <= 4:
        full_text = "\n".join(lines)
        h_txt, b_txt, f_txt = split_ocr_regions_inline(full_text)
        h_lines = h_txt.splitlines() if h_txt else []
        b_lines = b_txt.splitlines() if b_txt else []
        f_lines = f_txt.splitlines() if f_txt else []
        return h_lines, b_lines, f_lines
        
    table_start_idx = -1
    for idx, line in enumerate(lines):
        line_lower = line.lower()
        if any(re.search(pattern, line_lower) for pattern in HEADER_KEYWORDS):
            table_start_idx = idx
            break
            
    if table_start_idx == -1:
        table_start_idx = int(n * 0.3)
        
    footer_start_idx = -1
    for idx in range(table_start_idx + 1, n):
        line_lower = lines[idx].lower()
        if any(re.search(pattern, line_lower) for pattern in FOOTER_KEYWORDS):
            footer_start_idx = idx
            break
            
    if footer_start_idx == -1:
        for idx in range(n - 1, table_start_idx, -1):
            line_lower = lines[idx].lower()
            if any(re.search(pattern, line_lower) for pattern in FOOTER_KEYWORDS):
                footer_start_idx = idx
                break
                
    if footer_start_idx == -1:
        footer_start_idx = int(n * 0.75)
        
    if table_start_idx >= footer_start_idx:
        table_start_idx = int(n * 0.3)
        footer_start_idx = int(n * 0.75)
        
    table_start_idx = max(0, min(table_start_idx, n - 1))
    footer_start_idx = max(table_start_idx + 1, min(footer_start_idx, n))
    
    header_lines = lines[:table_start_idx]
    body_lines = lines[table_start_idx:footer_start_idx]
    footer_lines = lines[footer_start_idx:]
    
    return header_lines, body_lines, footer_lines

def preprocess_ocr_text(text: str) -> tuple[str, dict[str, int]]:
    if not text:
        return "", {"raw_len": 0, "comp_len": 0, "header_len": 0, "body_len": 0, "footer_len": 0}
        
    lines = text.splitlines()
    cleaned_lines = []
    for line in lines:
        cleaned_line = compress_repeating_line_content(line)
        cleaned_lines.append(cleaned_line)
        
    header_lines, body_lines, footer_lines = split_ocr_regions(cleaned_lines)
    
    compressed_body_lines, removed_count = compress_table_rows(body_lines)
    
    header_text = "\n".join(header_lines).strip()
    body_text = "\n".join(compressed_body_lines).strip()
    footer_text = "\n".join(footer_lines).strip()
    
    formatted_text = f"""========== HEADER ==========
{header_text}
========== BODY ==========
{body_text}
========== FOOTER ==========
{footer_text}"""

    stats = {
        "raw_len": len(text),
        "comp_len": len(formatted_text),
        "header_len": len(header_text),
        "body_len": len(body_text),
        "footer_len": len(footer_text)
    }
    
    return formatted_text, stats


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
    # Convert PIL Image to grayscale
    img_gray = img.convert('L')
    
    # Invert image so text is white (255) and background is black (0)
    img_inv = ImageOps.invert(img_gray)
    
    # Convert to numpy array
    arr = np.array(img_inv)
    
    # Sum pixels horizontally
    horizontal_sum = np.sum(arr, axis=1)
    
    # Binarize the horizontal sum to detect text vs blank space
    # Threshold can be a fraction of the maximum horizontal sum
    max_val = np.max(horizontal_sum)
    if max_val == 0:
        return 0
    threshold = max_val * 0.05
    text_lines = horizontal_sum > threshold
    
    # Count transitions from False (blank) to True (text)
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
            # Check if there are table keywords
            table_keywords = [
                "description", "qty", "quantity", "unit price", "amount", "price", "item", "desc", "amt",
                "الوصف", "الكمية", "سعر", "الاجمالي", "السعر", "البيان"
            ]
            has_table = any(any(kw in line.lower() for kw in table_keywords) for line in body_lines)
            
            if has_table and len(body_lines) > 0:
                # Keep first 2-3 lines of body_text
                lines_kept = min(len(body_lines), 3)
                header_and_first_rows = body_lines[:lines_kept]
                removed_rows = max(1, total_lines - lines_kept)
                compressed_body = "\n".join(header_and_first_rows) + f"\n[PRODUCT TABLE REMOVED - {removed_rows} ROWS]"
            else:
                # If no table keywords or body is empty, use body_text as is
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

        # Save stats to shared ocr_stats.json
        try:
            stats_path = Path("scratch/ocr_stats.json")
            stats_path.parent.mkdir(parents=True, exist_ok=True)
            if stats_path.exists():
                with open(stats_path, "r", encoding="utf-8") as sf:
                    ocr_stats = json.load(sf)
            else:
                ocr_stats = {}
                
            ocr_stats[file_path.name] = {
                "raw_len": total_raw_len,
                "comp_len": total_comp_len,
                "header_len": total_header_len,
                "body_len": total_body_len,
                "footer_len": total_footer_len,
                "tokens_used": total_tokens,
                "done_reason": final_done_reason
            }
            with open(stats_path, "w", encoding="utf-8") as sf:
                json.dump(ocr_stats, sf, ensure_ascii=False, indent=2)
        except Exception as e:
            LOGGER.error("Failed to save ocr_stats.json: %s", e)
            
        # Save raw_ocr.txt and cleaned_ocr.txt
        try:
            cwd = Path(os.getcwd())
            raw_full = f"{combined_header}\n{combined_body}\n{combined_footer}"
            (cwd / "raw_ocr.txt").write_text(raw_full, encoding="utf-8")
            (cwd / "cleaned_ocr.txt").write_text(formatted_text, encoding="utf-8")
        except Exception as e:
            LOGGER.error("Failed to save debug files raw_ocr.txt / cleaned_ocr.txt: %s", e)

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
