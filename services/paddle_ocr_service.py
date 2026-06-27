from __future__ import annotations

import logging
import time
import numpy as np

from services.settings import get_settings

LOGGER = logging.getLogger(__name__)


class PaddleOCRService:
    """Service wrapper for local PaddleOCR engine."""

    def __init__(self) -> None:
        self._ocr_engine = None
        self._model_verified = False

    def _init_ocr(self) -> None:
        """Lazily initialize PaddleOCR engine to speed up startup checks."""
        if self._ocr_engine is None:
            # pyrefly: ignore [missing-import]
            from paddleocr import PaddleOCR

            LOGGER.info("Initializing PaddleOCR engine...")
            self._ocr_engine = PaddleOCR(
                ocr_version="PP-OCRv4",
                lang="en",
                use_doc_orientation_classify=False,
                use_doc_unwarping=False,
                use_textline_orientation=False,
                enable_mkldnn=False,
            )
            LOGGER.info("PaddleOCR engine initialized successfully.")

    def verify_model(self) -> bool:
        """Lazily verify model and initialize PaddleOCR."""
        self._model_verified = True
        try:
            self._init_ocr()
            return True
        except Exception as exc:
            LOGGER.error("Failed to initialize PaddleOCR during verification: %s", exc)
            return False

    def ensure_initialized(self) -> None:
        """Ensure OCR is initialized and warmed up."""
        if not self._model_verified:
            self.verify_model()
        self._init_ocr()
        try:
            LOGGER.info("Warming up PaddleOCR engine...")
            dummy_img = np.zeros((100, 100, 3), dtype=np.uint8)
            self._ocr_engine.ocr(dummy_img)
            LOGGER.info("PaddleOCR engine warmed up successfully.")
            print("✓ PaddleOCR initialized", flush=True)
        except Exception as exc:
            LOGGER.error("Failed to warm up PaddleOCR engine: %s", exc)
            print(f"✗ PaddleOCR initialization failed: {exc}", flush=True)
