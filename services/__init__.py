from __future__ import annotations

from typing import Any


__all__ = [
    "DocumentValidator",
    "ExportService",
    "PaddleDeepSeekExtractor",
    "PaddleQwenExtractor",
    "DocumentWorkflow",
]

_EXPORTS = {
    "DocumentValidator": ("services.validation", "DocumentValidator"),
    "ExportService": ("services.export_service", "ExportService"),
    "PaddleDeepSeekExtractor": ("services.paddle_deepseek", "PaddleDeepSeekExtractor"),
    "PaddleQwenExtractor": ("services.paddle_qwen", "PaddleQwenExtractor"),
    "DocumentWorkflow": ("services.workflow", "DocumentWorkflow"),
}


def __getattr__(name: str) -> Any:
    if name not in _EXPORTS:
        raise AttributeError(f"module 'services' has no attribute {name!r}")
    module_name, attribute_name = _EXPORTS[name]
    module = __import__(module_name, fromlist=[attribute_name])
    return getattr(module, attribute_name)
