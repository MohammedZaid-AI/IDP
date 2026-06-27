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
from io import BytesIO
from pathlib import Path
from typing import Any

import fitz  # PyMuPDF
from PIL import Image
import httpx

from services.settings import get_settings

LOGGER = logging.getLogger(__name__)


def has_letters(block: list[str]) -> bool:
    for token in block:
        if any(c.isalpha() for c in token):
            return True
    return False


def deduplicate_tokens(text: str) -> str:
    if not text:
        return ""
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
                # Compare the last 3 chunks of size k
                chunk1 = norm_result[-k:]
                chunk2 = norm_result[-2*k:-k]
                chunk3 = norm_result[-3*k:-2*k]
                
                # Check if the chunk contains letters
                if has_letters(chunk1) and chunk1 == chunk2 == chunk3:
                    del result[-2*k:]
                    del norm_result[-2*k:]
                    break
                    
    # Reassemble text from tokens, keeping newlines formatting
    lines = []
    current_line = []
    for t in result:
        if t == "\n":
            lines.append(" ".join(current_line))
            current_line = []
        else:
            current_line.append(t)
    if current_line:
        lines.append(" ".join(current_line))
    return "\n".join(lines)


def truncate_on_loop(text: str) -> str:
    if not text:
        return ""
    lines = text.splitlines()
    n = len(lines)
    
    # 1. Check for block repetitions (size k >= 1) repeating 3 times consecutively
    for k in range(1, 25):
        if 3 * k > n:
            break
        for i in range(n - 3 * k + 1):
            block1 = lines[i : i + k]
            block2 = lines[i + k : i + 2 * k]
            block3 = lines[i + 2 * k : i + 3 * k]
            
            block_content = "".join(block1).strip()
            if len(block_content) > 3:
                norm1 = [re.sub(r'\s+', '', l.lower()) for l in block1]
                norm2 = [re.sub(r'\s+', '', l.lower()) for l in block2]
                norm3 = [re.sub(r'\s+', '', l.lower()) for l in block3]
                
                if norm1 == norm2 == norm3:
                    LOGGER.info(f"Loop detected (3x) at line {i} with block size {k}. Truncating.")
                    print(f"Loop detected (3x) at line {i} with block size {k}. Truncating.", flush=True)
                    return "\n".join(lines[:i + k])

    # 2. Check for larger block repetitions (size k >= 2) repeating 2 times consecutively
    for k in range(2, 25):
        if 2 * k > n:
            break
        for i in range(n - 2 * k + 1):
            block1 = lines[i : i + k]
            block2 = lines[i + k : i + 2 * k]
            
            block_content = "".join(block1).strip()
            if len(block_content) > 15:
                norm1 = [re.sub(r'\s+', '', l.lower()) for l in block1]
                norm2 = [re.sub(r'\s+', '', l.lower()) for l in block2]
                
                if norm1 == norm2:
                    LOGGER.info(f"Loop detected (2x) at line {i} with block size {k}. Truncating.")
                    print(f"Loop detected (2x) at line {i} with block size {k}. Truncating.", flush=True)
                    return "\n".join(lines[:i + k])
                    
    # 3. Check for single line repeating 2 times consecutively if it's long and identical
    for i in range(n - 1):
        l1 = re.sub(r'\s+', '', lines[i].lower())
        l2 = re.sub(r'\s+', '', lines[i+1].lower())
        if l1 == l2 and len(l1) > 25:
            LOGGER.info(f"Single line loop detected (2x) at line {i}. Truncating.")
            print(f"Single line loop detected (2x) at line {i}. Truncating.", flush=True)
            return "\n".join(lines[:i + 1])
            
    return text


def deduplicate_paragraphs(text: str) -> tuple[str, int]:
    raw_paragraphs = re.split(r'\n\s*\n', text)
    
    unique_paragraphs = []
    seen_normalized = set()
    removed_count = 0
    
    for p in raw_paragraphs:
        p_strip = p.strip()
        if not p_strip:
            continue
        norm_p = re.sub(r'\s+', '', p_strip.lower())
        if norm_p in seen_normalized:
            removed_count += 1
            continue
        seen_normalized.add(norm_p)
        unique_paragraphs.append(p_strip)
        
    return "\n\n".join(unique_paragraphs), removed_count


def clean_ocr(text: str) -> tuple[str, int, int]:
    raw_len = len(text)
    
    # 1. Truncate loop
    truncated = truncate_on_loop(text)
    
    # 2. Token-level deduplication
    deduplicated = deduplicate_tokens(truncated)
    
    # 3. Paragraph-level deduplication
    deduped_paras, dup_paras_removed = deduplicate_paragraphs(deduplicated)
    
    # 4. Line by line clean
    cleaned_lines = []
    prev_line = None
    
    for line in deduped_paras.splitlines():
        # Collapse multiple horizontal whitespaces
        cleaned_line = re.sub(r'[ \t\xa0\u2000-\u200a\u202f\u205f\u3000]+', ' ', line).strip()
        
        # Remove consecutive duplicate lines
        if prev_line is not None and cleaned_line == prev_line:
            continue
            
        # Collapse word-level repetitions within the line
        words = cleaned_line.split()
        if len(words) > 3:
            if len(set(words)) == 1:
                cleaned_line = words[0]
            else:
                new_words = []
                for w in words:
                    if not new_words or w != new_words[-1]:
                        new_words.append(w)
                cleaned_line = " ".join(new_words)
                
        if cleaned_line == "" and prev_line == "":
            continue
            
        cleaned_lines.append(cleaned_line)
        prev_line = cleaned_line
        
    cleaned_text = "\n".join(cleaned_lines).strip()
    chars_removed = raw_len - len(cleaned_text)
    return cleaned_text, dup_paras_removed, chars_removed


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

    def extract_text(self, file_path: str | Path) -> str:
        file_path = Path(file_path)
        LOGGER.info("Qari OCR started file=%s", file_path.name)

        # Collect and print image metadata for verification
        file_size = os.path.getsize(file_path) if os.path.exists(file_path) else 0
        mime_type = "image/png" if file_path.suffix.lower() == ".png" else "image/jpeg"
        
        print("\n================ MULTIMODAL REQUEST DETAILS ================")
        print(f"Endpoint URL: {self.url}/api/chat")
        print(f"HTTP Method: POST")
        print(f"File Size: {file_size} bytes")
        print(f"MIME Type: {mime_type}")
        
        pages = self._render_pages(file_path)
        image_b64_list = []
        for i, img in enumerate(pages):
            w, h = img.size
            max_size = 1024
            if max(w, h) > max_size:
                scale = max_size / max(w, h)
                img = img.resize((int(w * scale), int(h * scale)), Image.Resampling.LANCZOS if hasattr(Image, "Resampling") else Image.LANCZOS)
            
            w_final, h_final = img.size
            buffered = BytesIO()
            img.save(buffered, format="PNG")
            b64_bytes = buffered.getvalue()
            b64_str = base64.b64encode(b64_bytes).decode("ascii")
            image_b64_list.append(b64_str)
            
            print(f"Page {i+1} - Original Size: {w}x{h}, Resized Size: {w_final}x{h_final}")
            print(f"Page {i+1} - Image attached: YES")
            print(f"Page {i+1} - Image size in bytes: {len(b64_bytes)}")
            print(f"Page {i+1} - Base64 length: {len(b64_str)}")
            print(f"Page {i+1} - First 100 Base64 characters: {b64_str[:100]}")
            print(f"Page {i+1} - Last 100 Base64 characters: {b64_str[-100:]}")
        print("============================================================\n")

        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": "transcribe",
                    "images": image_b64_list,
                }
            ],
            "stream": False,
            "options": {
                "temperature": 0.0,
                "num_predict": 850,
            }
        }

        # Save request to debug_qari_request.json (excluding full base64 strings)
        debug_payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": "transcribe",
                    "images": [
                        {
                            "attached": "YES",
                            "base64_length": len(b64),
                            "first_100": b64[:100],
                            "last_100": b64[-100:]
                        } for b64 in image_b64_list
                    ],
                }
            ],
            "stream": False,
            "options": {
                "temperature": 0.0,
                "num_predict": 850,
            }
        }
        try:
            with open("debug_qari_request.json", "w", encoding="utf-8") as f:
                json.dump(debug_payload, f, ensure_ascii=False, indent=2)
        except Exception as e:
            LOGGER.error("Failed to save debug_qari_request.json: %s", e)

        try:
            with httpx.Client(timeout=300.0) as client:
                res = client.post(
                    f"{self.url}/api/chat",
                    json=payload
                )
                
                # Save raw response to debug_qari_response.json
                try:
                    with open("debug_qari_response.json", "w", encoding="utf-8") as f:
                        f.write(res.text)
                except Exception as e:
                    LOGGER.error("Failed to save debug_qari_response.json: %s", e)

                print("\n================ RAW QARI RESPONSE ================")
                print(res.text)
                print("===================================================\n")
                
                if res.status_code == 200:
                    parsed_json = res.json()
                    print("\n================ PARSED QARI JSON ================")
                    print(json.dumps(parsed_json, ensure_ascii=False, indent=2))
                    print("===================================================\n")
                    
                    content = parsed_json.get("message", {}).get("content", "").strip()
                    
                    # Clean the OCR output
                    cleaned_content, dup_paras_removed, chars_removed = clean_ocr(content)
                    
                    # Print debug logging as required
                    raw_len = len(content)
                    cleaned_len = len(cleaned_content)
                    print(f"Raw OCR length: {raw_len} characters")
                    print(f"Cleaned OCR length: {cleaned_len} characters")
                    print(f"Characters removed: {chars_removed}")
                    print(f"Number of duplicate paragraphs removed: {dup_paras_removed}")
                    
                    # Save raw_ocr.txt and cleaned_ocr.txt
                    try:
                        cwd = Path(os.getcwd())
                        (cwd / "raw_ocr.txt").write_text(content, encoding="utf-8")
                        (cwd / "cleaned_ocr.txt").write_text(cleaned_content, encoding="utf-8")
                    except Exception as e:
                        LOGGER.error("Failed to save debug files raw_ocr.txt / cleaned_ocr.txt: %s", e)

                    print("\n================ EXTRACTED CONTENT ================")
                    print(repr(cleaned_content))
                    print("===================================================\n")
                    return cleaned_content
                else:
                    LOGGER.error("Qari OCR API failed: status=%d response=%s", res.status_code, res.text)
        except Exception as exc:
            LOGGER.error("Qari OCR request failed: %s", exc)
            
        return ""

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
