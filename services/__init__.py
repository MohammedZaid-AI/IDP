from __future__ import annotations

from typing import Any


__all__ = [
    "ExportService",
    "PaddleOCRService",
    "NumericExtractor",
    "MergeExtractor",
    "HybridInvoiceExtractionService",
    "MultiModelDocumentWorkflow",
]

_EXPORTS = {
    "ExportService": ("services.export_service", "ExportService"),
    "PaddleOCRService": ("services.paddle_ocr_service", "PaddleOCRService"),
    "NumericExtractor": ("services.numeric_extractor", "NumericExtractor"),
    "MergeExtractor": ("services.merge_extractor", "MergeExtractor"),
    "HybridInvoiceExtractionService": ("services.merge_extractor", "HybridInvoiceExtractionService"),
    "MultiModelDocumentWorkflow": ("services.workflow", "MultiModelDocumentWorkflow"),
}


def __getattr__(name: str) -> Any:
    if name not in _EXPORTS:
        raise AttributeError(f"module 'services' has no attribute {name!r}")
    module_name, attribute_name = _EXPORTS[name]
    module = __import__(module_name, fromlist=[attribute_name])
    return getattr(module, attribute_name)


