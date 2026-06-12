from services.classifier import DocumentClassifier


_classifier = DocumentClassifier()


def classify_document(text: str) -> str:
    return _classifier.classify(text).document_type
