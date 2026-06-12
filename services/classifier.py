from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from langchain_groq import ChatGroq

from services.settings import get_settings


DOCUMENT_TYPES = [
    "invoice",
    "receipt",
    "bank_statement",
    "financial_report",
    "purchase_order",
    "credit_note",
    "debit_note",
]


@dataclass
class ClassificationResult:
    document_type: str
    confidence: float
    reasoning: str = ""


class DocumentClassifier:
    def __init__(self) -> None:
        settings = get_settings()
        self._model = None
        if settings.groq_api_key:
            try:
                self._model = ChatGroq(model="llama-3.3-70b-versatile")
            except Exception:
                self._model = None

    def classify(self, text: str) -> ClassificationResult:
        heuristic = self._heuristic_classify(text)
        if self._model is None:
            return heuristic

        prompt = (
            "Classify the following financial document into exactly one of: "
            f"{', '.join(DOCUMENT_TYPES)}. Return only the category name.\n\n{text[:6000]}"
        )
        try:
            response = self._model.invoke(prompt)
            candidate = str(response.content).strip().lower()
            if candidate in DOCUMENT_TYPES:
                return ClassificationResult(document_type=candidate, confidence=0.9, reasoning="groq")
        except Exception:
            pass
        return heuristic

    def _heuristic_classify(self, text: str) -> ClassificationResult:
        sample = text.lower()
        scores = {
            "invoice": len(re.findall(r"\binvoice\b|\binv[.-]?\d+|\bbill to\b|\bsubtotal\b", sample)),
            "receipt": len(re.findall(r"\breceipt\b|\bmerchant\b|\bpaid\b|\btransaction\b", sample)),
            "bank_statement": len(re.findall(r"\bbank statement\b|\baccount number\b|\bopening balance\b|\bclosing balance\b", sample)),
            "financial_report": len(re.findall(r"\bbalance sheet\b|\bincome statement\b|\bprofit and loss\b|\bannual report\b", sample)),
            "purchase_order": len(re.findall(r"\bpurchase order\b|\bpo number\b|\border date\b", sample)),
            "credit_note": len(re.findall(r"\bcredit note\b|\bcredit memo\b", sample)),
            "debit_note": len(re.findall(r"\bdebit note\b|\bdebit memo\b", sample)),
        }
        document_type = max(scores, key=scores.get)
        confidence = 0.55 + min(scores[document_type] * 0.07, 0.35)
        if scores[document_type] == 0:
            document_type = "invoice"
            confidence = 0.5
        return ClassificationResult(document_type=document_type, confidence=round(confidence, 2), reasoning="heuristic")
