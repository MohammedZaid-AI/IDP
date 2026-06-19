"""Vision-based OCR pipeline using Qwen2.5-VL via local Ollama.

Extracts plain text/markdown from documents while preserving structure.
"""

from __future__ import annotations

import base64
import json
import logging
import time
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Any

import fitz  # PyMuPDF
from PIL import Image

from services.settings import get_settings

LOGGER = logging.getLogger(__name__)

# Maximum number of pages to send in a single request
MAX_PAGES = 10

OCR_PROMPT = (
    "You are an expert Document Data Extractor.\n"
    "Extract ONLY the following information from the document, and output it in STRICT JSON format:\n"
    "{\n"
    "  \"document_number\": \"...\",\n"
    "  \"document_date\": \"...\",\n"
    "  \"vendor_name\": \"...\",\n"
    "  \"customer_name\": \"...\",\n"
    "  \"currency\": \"...\",\n"
    "  \"amount_block\": \"raw text exactly as seen on invoice\"\n"
    "}\n\n"
    "CRITICAL RULES:\n"
    "- 'amount_block' should contain ALL text related to Gross Amount, Total Amount, Invoice Total, Net Amount, VAT, Tax Amount, Subtotal, and Summary Tables at the bottom of the invoice.\n"
    "- DO NOT calculate totals.\n"
    "- DO NOT calculate VAT.\n"
    "- DO NOT infer values.\n"
    "- DO NOT normalize dates.\n"
    "- DO NOT generate final financial fields.\n"
    "- Output ONLY raw JSON, with no markdown wrappers."
)

@dataclass
class QwenOCRResult:
    """Result of a Qwen2.5-VL OCR call."""

    ocr_text: str
    page_count: int
    ocr_time: float
    eval_count: int = 0
    prompt_eval_count: int = 0
    text_length: int = 0
    load_duration: float = 0.0
    prompt_eval_duration: float = 0.0
    eval_duration: float = 0.0
    orig_resolution: str = ""
    resized_resolution: str = ""


# ---------------------------------------------------------------------------
# Image helpers
# ---------------------------------------------------------------------------

def _render_pages(file_path: Path) -> list[Image.Image]:
    """Convert a file to a list of PIL images (one per page)."""
    ext = file_path.suffix.lower()
    if ext == ".pdf":
        doc = fitz.open(str(file_path))
        images: list[Image.Image] = []
        for page_index, page in enumerate(doc):
            if page_index >= MAX_PAGES:
                LOGGER.info("Capped at %d pages for %s", MAX_PAGES, file_path.name)
                break
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
            images.append(Image.open(BytesIO(pix.tobytes("png"))).convert("RGB"))
        return images
    # Single image file
    return [Image.open(file_path).convert("RGB")]


def _image_to_base64(image: Image.Image, max_size: int = None) -> str:
    """Encode a PIL image to a base64 string, resizing if needed."""
    if max_size is None:
        import os
        max_size = int(os.environ.get("QWEN_MAX_SIZE", 800))
    width, height = image.size
    if max(width, height) > max_size:
        scale = max_size / max(width, height)
        image = image.resize((int(width * scale), int(height * scale)), Image.LANCZOS)
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode("ascii")


# ---------------------------------------------------------------------------
# Main OCR Extractor
# ---------------------------------------------------------------------------

def _crop_and_stitch(image: Image.Image) -> Image.Image:
    """Crop top 25% and bottom 25% of the image and stitch them vertically."""
    width, height = image.size
    top_region = image.crop((0, 0, width, int(height * 0.25)))
    bottom_region = image.crop((0, int(height * 0.75), width, height))
    
    stitched = Image.new("RGB", (width, top_region.height + bottom_region.height))
    stitched.paste(top_region, (0, 0))
    stitched.paste(bottom_region, (0, top_region.height))
    return stitched

class QwenVisionOCRService:
    """Extracts structured text directly from document images using Qwen2.5-VL via local Ollama."""

    def __init__(self) -> None:
        settings = get_settings()
        self.ollama_url: str = settings.ollama_url
        self.model: str = "qwen2.5vl:3b"
        self._model_verified = False

    def verify_model(self) -> bool:
        """Run startup verification."""
        from urllib import error, request as urllib_request
        import sys

        tags_url = f"{self.ollama_url.rstrip('/')}/api/tags"
        try:
            req = urllib_request.Request(tags_url, method="GET")
            with urllib_request.urlopen(req, timeout=5) as response:
                data = json.loads(response.read().decode("utf-8"))
        except Exception as exc:
            msg = "Qwen2.5-VL local model not running."
            print(msg, file=sys.stderr)
            LOGGER.error("Ollama is not reachable at %s — %s. %s", tags_url, exc, msg)
            return False

        models = data.get("models", [])
        available_names = [m.get("name", "") for m in models]
        for name in available_names:
            if self.model in name or name.startswith(self.model.split(":")[0]):
                LOGGER.info("✓ Ollama model '%s' verified (matched '%s')", self.model, name)
                self._model_verified = True
                return True

        msg = "Qwen2.5-VL local model not running."
        print(msg, file=sys.stderr)
        LOGGER.error("%s Model '%s' not found in Ollama. Available models: %s", msg, self.model, available_names)
        return False

    def extract_text(self, file_path: str | Path, crop: bool = False) -> QwenOCRResult:
        """Run extraction on a single file and return the result."""
        file_path = Path(file_path)
        LOGGER.info("Qwen vision OCR started file=%s, crop=%s", file_path.name, crop)

        if not self._model_verified:
            # Re-check in case Ollama came up
            self.verify_model()

        pages = _render_pages(file_path)
        page_count = len(pages)
        
        if crop:
            pages = [_crop_and_stitch(page) for page in pages]

        start = time.perf_counter()
        
        # Track resolution for the first page
        orig_res = f"{pages[0].size[0]}x{pages[0].size[1]}" if pages else ""
        
        metrics = self._call_ollama(pages)
        ocr_time = time.perf_counter() - start
        
        import os
        max_size = int(os.environ.get("QWEN_MAX_SIZE", 800))
        # Estimate resized resolution assuming lanczos
        w, h = pages[0].size if pages else (0, 0)
        if max(w, h) > max_size:
            scale = max_size / max(w, h)
            res_res = f"{int(w * scale)}x{int(h * scale)}"
        else:
            res_res = orig_res

        LOGGER.info("Qwen vision OCR time: %.2fs for %s", ocr_time, file_path.name)

        return QwenOCRResult(
            ocr_text=metrics.get("text", ""),
            page_count=page_count,
            ocr_time=ocr_time,
            eval_count=metrics.get("eval_count", 0),
            prompt_eval_count=metrics.get("prompt_eval_count", 0),
            text_length=len(metrics.get("text", "")),
            load_duration=metrics.get("load_duration", 0.0),
            prompt_eval_duration=metrics.get("prompt_eval_duration", 0.0),
            eval_duration=metrics.get("eval_duration", 0.0),
            orig_resolution=orig_res,
            resized_resolution=res_res,
        )

    def _call_ollama(self, pages: list[Image.Image]) -> dict:
        """Send images to local Ollama's /api/chat endpoint."""
        from urllib import error, request as urllib_request
        import subprocess

        # Image logging
        for idx, img in enumerate(pages):
            orig_w, orig_h = img.size
            LOGGER.info("Page %d - Original resolution: %dx%d", idx + 1, orig_w, orig_h)

        image_b64_list = []
        for idx, img in enumerate(pages):
            b64_str = _image_to_base64(img)
            # Find the size of the resized image by loading it back
            from io import BytesIO
            import base64
            res_img = Image.open(BytesIO(base64.b64decode(b64_str)))
            res_w, res_h = res_img.size
            LOGGER.info("Page %d - Resized resolution: %dx%d", idx + 1, res_w, res_h)
            image_b64_list.append(b64_str)

        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": OCR_PROMPT,
                    "images": image_b64_list,
                }
            ],
            "stream": False,
            "keep_alive": "30m",
            "options": {
                "temperature": 0.0,
                "num_predict": 2048,
            },
        }

        body = json.dumps(payload).encode("utf-8")
        chat_url = f"{self.ollama_url.rstrip('/')}/api/chat"

        req = urllib_request.Request(
            chat_url,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        LOGGER.info("Starting inference with model: %s", self.model)
        try:
            ps_out = subprocess.check_output(["ollama", "ps"]).decode().strip()
            LOGGER.info("ollama ps during Qwen OCR inference start:\n%s", ps_out)
        except Exception as e:
            LOGGER.error("Failed to run ollama ps: %s", e)

        inference_start = time.perf_counter()
        try:
            with urllib_request.urlopen(req, timeout=900) as response:
                raw = response.read().decode("utf-8")
        except error.URLError as exc:
            LOGGER.error("Ollama request failed: %s", exc)
            return {"text": "", "eval_count": 0}
        inference_end = time.perf_counter()
        inference_duration = inference_end - inference_start
        LOGGER.info("Inference completed with model %s in %.2fs", self.model, inference_duration)

        try:
            api_response = json.loads(raw)
            message_content = api_response.get("message", {}).get("content", "")
            eval_count = api_response.get("eval_count", 0)
            prompt_eval_count = api_response.get("prompt_eval_count", 0)
            
            # Ollama returns durations in nanoseconds
            load_duration = api_response.get("load_duration", 0) / 1e9
            prompt_eval_duration = api_response.get("prompt_eval_duration", 0) / 1e9
            eval_duration = api_response.get("eval_duration", 0) / 1e9
            
            LOGGER.info("Tokens: Prompt Eval=%d, Eval=%d", prompt_eval_count, eval_count)
            return {
                "text": message_content, 
                "eval_count": eval_count,
                "prompt_eval_count": prompt_eval_count,
                "load_duration": load_duration,
                "prompt_eval_duration": prompt_eval_duration,
                "eval_duration": eval_duration
            }
        except (json.JSONDecodeError, KeyError) as exc:
            LOGGER.error("Failed to parse Ollama response: %s", exc)
            return {"text": raw, "eval_count": 0}

qwen_ocr_service = QwenVisionOCRService()
