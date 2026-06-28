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


def clean_ocr(text: str) -> str:
    if not text:
        return ""
    lines = text.splitlines()
    cleaned_lines = []
    prev_line = None
    for line in lines:
        # Collapse multiple horizontal whitespaces
        cleaned_line = re.sub(r'[ \t\xa0\u2000-\u200a\u202f\u205f\u3000]+', ' ', line).strip()
        # Remove exact duplicate consecutive lines
        if prev_line is not None and cleaned_line == prev_line:
            continue
        cleaned_lines.append(cleaned_line)
        prev_line = cleaned_line
    return "\n".join(cleaned_lines).strip()


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
                    cleaned_content = clean_ocr(content)
                    
                    # Print debug logging as required
                    raw_len = len(content)
                    cleaned_len = len(cleaned_content)
                    print(f"Raw OCR length: {raw_len} characters")
                    print(f"Cleaned OCR length: {cleaned_len} characters")
                    print(f"Characters removed: {raw_len - cleaned_len}")
                    
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
