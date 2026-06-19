"""Vision-based OCR pipeline using DeepSeek-VL2 via local Ollama.

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
    "Extract ONLY the following information from the document as plain text:\n"
    "1. Document Number\n"
    "2. Document Date\n"
    "3. Vendor Name\n"
    "4. Customer Name\n"
    "5. Currency\n"
    "6. Amount-related text blocks (extract the raw text surrounding financial totals, subtotals, and taxes at the bottom of the invoice)\n\n"
    "CRITICAL RULES:\n"
    "- DO NOT extract final totals or attempt to calculate them.\n"
    "- DO NOT generate markdown.\n"
    "- DO NOT generate explanations.\n"
    "- Output as a simple plain-text list.\n"
    "- If a value is missing, write 'null'."
)

@dataclass
class DeepSeekOCRResult:
    """Result of a DeepSeek-VL2 OCR call."""

    ocr_text: str
    page_count: int
    ocr_time: float
    eval_count: int = 0
    text_length: int = 0


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


def _image_to_base64(image: Image.Image, max_size: int = 800) -> str:
    """Encode a PIL image to a base64 string, resizing if needed."""
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

class DeepSeekVisionOCRService:
    """Extracts structured text directly from document images using DeepSeek-VL2 via local Ollama."""

    def __init__(self) -> None:
        settings = get_settings()
        self.ollama_url: str = settings.ollama_url
        self.model: str = "deepseek-vl2"
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
            msg = "DeepSeek-VL2 local model not running."
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

        msg = "DeepSeek-VL2 local model not running."
        print(msg, file=sys.stderr)
        LOGGER.error("%s Model '%s' not found in Ollama. Available models: %s", msg, self.model, available_names)
        # Even if not found in list, attempt to run since user might be pulling or mapping it differently
        # Let's not hard-fail the benchmark, just log it.
        return False

    def extract_text(self, file_path: str | Path) -> DeepSeekOCRResult:
        """Run extraction on a single file and return the result."""
        file_path = Path(file_path)
        LOGGER.info("DeepSeek vision OCR started file=%s", file_path.name)

        if not self._model_verified:
            self.verify_model()

        pages = _render_pages(file_path)
        page_count = len(pages)

        start = time.perf_counter()
        raw_response, eval_count = self._call_ollama(pages)
        ocr_time = time.perf_counter() - start

        LOGGER.info("DeepSeek vision OCR time: %.2fs for %s", ocr_time, file_path.name)

        return DeepSeekOCRResult(
            ocr_text=raw_response,
            page_count=page_count,
            ocr_time=ocr_time,
            eval_count=eval_count,
            text_length=len(raw_response)
        )

    def _call_ollama(self, pages: list[Image.Image]) -> tuple[str, int]:
        """Send images to local Ollama's /api/chat endpoint."""
        from urllib import error, request as urllib_request
        import time
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
            "keep_alive": 0,
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
            LOGGER.info("ollama ps during DeepSeek OCR inference start:\n%s", ps_out)
        except Exception as e:
            LOGGER.error("Failed to run ollama ps: %s", e)

        inference_start = time.perf_counter()
        try:
            with urllib_request.urlopen(req, timeout=900) as response:
                raw = response.read().decode("utf-8")
        except error.URLError as exc:
            LOGGER.error("Ollama request failed: %s", exc)
            return f"Ollama request failed: {exc}", 0
        inference_end = time.perf_counter()
        inference_duration = inference_end - inference_start
        LOGGER.info("Inference completed with model %s in %.2fs", self.model, inference_duration)

        try:
            api_response = json.loads(raw)
            message_content = api_response.get("message", {}).get("content", "")
            eval_count = api_response.get("eval_count", 0)
            prompt_eval_count = api_response.get("prompt_eval_count", 0)
            LOGGER.info("DeepSeek OCR - Prompt token count: %d, Completion token count: %d", prompt_eval_count, eval_count)
        except (json.JSONDecodeError, KeyError) as exc:
            LOGGER.error("Failed to parse Ollama response: %s", exc)
            return raw, 0

        return message_content, eval_count

deepseek_ocr_service = DeepSeekVisionOCRService()
