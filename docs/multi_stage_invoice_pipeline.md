# Multi-Stage Invoice Pipeline

## 1. Project Architecture

Redesign the current single-prompt flow into a staged extraction engine while keeping the existing OCR layer unchanged:

```text
Image / PDF
  -> Existing OCR engine
  -> Raw OCR text
  -> Field extraction agents
  -> Merge layer
  -> Validation layer
  -> Confidence scoring
  -> Structured output modes
  -> Excel export
```

The goal is to stop asking one model call to solve the whole invoice. Instead, each field gets a small, strict, field-specific prompt. This improves consistency, reduces field confusion such as invoice number vs VAT number, and gives us field-level confidence/evidence for review.

Recommended runtime engine flag:

```env
EXTRACTION_ENGINE=multi_stage_qwen
OLLAMA_FIELD_EXTRACTION_MODEL=gemma4:e4b
```

The existing OCR remains the source of truth. The LLM is only allowed to select and normalize values already present in OCR text.

## 2. Folder Structure

Current pragmatic structure:

```text
services/
  invoice_multi_stage.py        # staged invoice extraction engine
  workflow.py                   # engine selection, timings, persistence
  export_service.py             # Excel generation and column ordering
routers/
  api.py                        # upload/export API integration
tests/
  test_invoice_multi_stage.py   # deterministic tests for validation/export/confidence
docs/
  multi_stage_invoice_pipeline.md
```

Recommended package split once behavior stabilizes:

```text
services/invoice_pipeline/
  prompts.py                    # field prompt registry
  clients.py                    # Ollama/Qwen JSON client
  agents.py                     # field extractor agent classes
  merge.py                      # canonical document merge logic
  validation.py                 # grounding, normalization, business rules
  confidence.py                 # field and overall confidence scoring
  formatters.py                 # JSON/chat summary/Excel row formatting
  orchestrator.py               # end-to-end staged pipeline
```

## 3. Service Design

Core services:

- `OllamaJsonClient`: Sends strict JSON prompts to local Qwen via Ollama and parses the model response.
- `FieldExtractorAgent`: Receives OCR text and one `FieldDefinition`; extracts only that field.
- `InvoiceMergeService`: Combines all independent field results into the canonical invoice schema.
- `InvoiceValidationService`: Rejects hallucinated or placeholder values, normalizes dates/currency/amounts, and checks arithmetic consistency.
- `InvoiceConfidenceService`: Produces weighted overall confidence from field-level confidence and validation issues.
- `InvoiceSummaryFormatter`: Produces human-readable ChatGPT-style output for UI/chat review.
- `InvoiceExcelMapper`: Maps canonical JSON to the exact Excel columns.
- `StagedInvoiceExtractionService`: Orchestrates OCR text through agents, merge, validation, confidence, and output formatting.

Each field agent should return this shape:

```json
{
  "value": "1738",
  "evidence": "Invoice No: 1738",
  "confidence": 0.98
}
```

## 4. Python Class Design

Recommended contracts:

```python
@dataclass
class FieldDefinition:
    name: str
    question: str
    instruction_block: str
    expected_type: str = "string"
    priority: int = 50

@dataclass
class FieldAgentResult:
    field_name: str
    raw_value: Any = None
    normalized_value: Any = None
    evidence: str = ""
    confidence: float = 0.0
    grounded: bool = False
    issues: list[str] = field(default_factory=list)
    raw_response: str = ""

@dataclass
class StagedExtractionResult:
    document_type: str
    extracted_json: dict[str, Any]
    raw_response: str
    ocr_text: str
    confidence: float
    page_count: int
    ocr_time: float
    llm_time: float
    validation_time: float
    processing_time: float
    field_results: dict[str, FieldAgentResult]
```

Canonical merged payload:

```json
{
  "document_number": "",
  "document_date": "",
  "vendor_name": "",
  "customer_name": "",
  "vat_number": "",
  "currency": "",
  "subtotal": null,
  "tax_amount": null,
  "total_amount": null,
  "_confidences": {},
  "_evidence": {},
  "_validation": {},
  "_summary": "",
  "_output_modes": {}
}
```

## 5. Workflow Orchestration

Workflow behavior:

1. `workflow.process_file()` receives the uploaded file path.
2. Existing OCR runs unchanged and returns raw OCR text.
3. `StagedInvoiceExtractionService.process_ocr_text()` receives only OCR text and OCR metadata.
4. The service runs nine independent field agents.
5. `InvoiceMergeService` builds the canonical invoice object.
6. `InvoiceValidationService` verifies grounding and normalizes values.
7. `InvoiceConfidenceService` calculates per-field and overall confidence.
8. The final payload is persisted through the existing workflow.
9. `ExportService` writes the Excel row using invoice-first columns.

Pseudo-code:

```python
def _process_multi_stage_qwen(state):
    ocr_result = ocr_service.extract_text(state["file_path"])
    result = staged_invoice_service.process_ocr_text(
        ocr_text=ocr_result.ocr_text,
        ocr_result=ocr_result,
    )

    state["document_type"] = "invoice"
    state["json_output"] = result.extracted_json
    state["raw_text"] = result.ocr_text
    state["raw_llm_response"] = result.raw_response
    state["confidence"] = result.confidence
    state["extraction_engine"] = "multi_stage_qwen"
    return state
```

## 6. Prompt Templates for All Extractors

Global rules included in every prompt:

```text
You are a field-specific invoice extraction agent for bilingual Arabic-English invoices.
Use only the OCR text provided.
Extract only the assigned field.
Do not translate.
Preserve Arabic exactly as it appears.
Preserve English exactly as it appears.
If Arabic and English versions of the same name appear, return both separated by " | ".
Never hallucinate.
Return JSON only with keys: value, evidence, confidence.
If the field is missing, return {"value": null, "evidence": "", "confidence": 0.0}.
```

Vendor Name extractor:

```text
Question: Identify the vendor or supplier name.
Prioritize labels: Seller, Supplier, Vendor, From, المؤسسة, المورد, اسم البائع.
The vendor is the company issuing the invoice.
Never return the customer or bill-to entity.
Preserve Arabic and English if both exist.
```

Customer Name extractor:

```text
Question: Identify the customer or billed-to entity name.
Prioritize labels: Customer, Bill To, Buyer, Client, العميل, اسم العميل.
Never return placeholder labels such as Customer:, Client:, M/s, Receiver, Signature.
Never return the vendor name.
Preserve Arabic and English if both exist.
```

Invoice Number extractor:

```text
Question: Identify the invoice number.
Prioritize labels: Invoice No, Invoice Number, Tax Invoice No, رقم الفاتورة.
Never return VAT Number, Tax ID, TIN, or registration number.
Prefer short alphanumeric invoice identifiers near invoice labels.
```

VAT Number extractor:

```text
Question: Identify the VAT or tax registration number.
Prioritize labels: VAT No, VAT Number, TRN, Tax Registration Number, الرقم الضريبي, رقم الضريبة.
Never return invoice number.
Prefer long numeric or alphanumeric tax identifiers.
```

Date extractor:

```text
Question: Identify the invoice issue date.
Prioritize labels: Invoice Date, Date, Tax Invoice Date, تاريخ الفاتورة.
Ignore due date unless it is the only clearly available document issue date.
Return the date exactly from OCR; normalization happens after extraction.
```

Currency extractor:

```text
Question: Identify the invoice currency.
Prioritize explicit currency codes: SAR, AED, USD, QAR, OMR, BHD, KWD.
If OCR explicitly says Saudi Riyal or ريال سعودي, return SAR.
Do not infer currency from country unless currency text exists in OCR.
```

Subtotal extractor:

```text
Question: Identify subtotal or amount before VAT.
Prioritize labels: Subtotal, Amount Before VAT, Net Amount, الإجمالي قبل الضريبة.
Return only the numeric amount.
Never return tax amount or final total.
```

Tax Amount extractor:

```text
Question: Identify VAT or tax amount.
Prioritize labels: VAT Amount, Tax Amount, VAT Amt, قيمة الضريبة.
Return only the numeric amount.
Never return subtotal or grand total.
```

Total Amount extractor:

```text
Question: Identify the final payable total amount.
Prioritize labels: Total, Grand Total, Total Amount, Amount Due, الإجمالي.
If multiple totals exist, prefer the final payable amount.
Return only the numeric amount.
```

## 7. Validation Design

Validation must treat OCR text as the source of truth.

Grounding checks:

- For identifiers and names, verify the extracted value or its evidence appears in OCR text.
- For normalized values, verify either the raw value or evidence appears in OCR text.
- Reject values that cannot be grounded.

Placeholder rejection:

```text
Customer
Client
M/s
Receiver
Signature
Customer:
Client:
Supplier:
Vendor:
```

Field validation rules:

- `vat_number`: Allow alphanumeric tax identifiers, commonly 10-20 characters; for KSA, prefer 15 digits when detected.
- `document_date`: Normalize to `YYYY-MM-DD`; reject impossible dates.
- `currency`: Normalize to uppercase 3-letter code such as `SAR`, `AED`, `USD`.
- `subtotal`, `tax_amount`, `total_amount`: Parse Arabic and English digits, commas, decimals, and currency symbols into numbers.
- Arithmetic check: if subtotal, tax, and total are present, verify `subtotal + tax_amount ~= total_amount` with a small tolerance.

Validation output:

```json
{
  "_validation": {
    "valid": true,
    "issues": [
      {
        "field": "total_amount",
        "message": "Subtotal + tax does not match total.",
        "severity": "warning"
      }
    ]
  }
}
```

## 8. Confidence Scoring Design

Each field agent returns its own confidence. Validation can reduce or zero confidence when a value is ungrounded or invalid.

Recommended business-weighted scoring:

```python
FIELD_WEIGHTS = {
    "document_number": 0.22,
    "vat_number": 0.20,
    "total_amount": 0.18,
    "vendor_name": 0.12,
    "customer_name": 0.08,
    "document_date": 0.07,
    "currency": 0.05,
    "subtotal": 0.04,
    "tax_amount": 0.04,
}
```

Overall score:

```text
overall_confidence = sum(field_confidence * field_weight)
overall_confidence -= validation_error_penalty
overall_confidence -= validation_warning_penalty
```

Example field confidence block:

```json
{
  "_confidences": {
    "vendor_name": 0.95,
    "customer_name": 0.90,
    "document_number": 1.0,
    "vat_number": 0.98,
    "document_date": 0.92,
    "currency": 0.95,
    "subtotal": 0.88,
    "tax_amount": 0.90,
    "total_amount": 0.98
  }
}
```

## 9. Excel Export Implementation

Excel must be generated from the validated canonical payload, not raw model output.

Target columns:

```text
Invoice Number | Date | Vendor | Customer | VAT | Currency | Subtotal | Tax | Total
```

Mapper:

```python
class InvoiceExcelMapper:
    COLUMNS = [
        "Invoice Number",
        "Date",
        "Vendor",
        "Customer",
        "VAT",
        "Currency",
        "Subtotal",
        "Tax",
        "Total",
    ]

    @classmethod
    def to_row(cls, payload):
        return {
            "Invoice Number": payload.get("document_number"),
            "Date": payload.get("document_date"),
            "Vendor": payload.get("vendor_name"),
            "Customer": payload.get("customer_name"),
            "VAT": payload.get("vat_number"),
            "Currency": payload.get("currency"),
            "Subtotal": payload.get("subtotal"),
            "Tax": payload.get("tax_amount"),
            "Total": payload.get("total_amount"),
        }
```

Export service behavior:

- Build one row per processed invoice.
- Put `filename` and `document_type` first if present.
- Put invoice columns next in the exact target order.
- Append any flattened metadata after the invoice columns for debugging/review.

## 10. End-to-End Implementation Plan

Phase 1: Staged engine foundation

1. Add `services/invoice_multi_stage.py`.
2. Define canonical fields and data contracts.
3. Add `OllamaJsonClient` with strict JSON response parsing.
4. Add `FieldDefinition` registry for the nine extractors.
5. Add `FieldExtractorAgent` to run one prompt per field.

Phase 2: Merge, validation, confidence

1. Add `InvoiceMergeService` to combine field results.
2. Add grounding checks against OCR text.
3. Add placeholder rejection.
4. Add VAT/date/currency/amount normalization.
5. Add arithmetic sanity checks.
6. Add field-level confidence and weighted overall confidence.

Phase 3: Output modes

1. Return canonical JSON as the primary machine output.
2. Add `InvoiceSummaryFormatter` for ChatGPT-style human-readable output.
3. Add `InvoiceExcelMapper` for Excel-ready rows.
4. Store `_evidence`, `_confidences`, and `_validation` in the payload for review tooling.

Phase 4: Workflow integration

1. Add `EXTRACTION_ENGINE=multi_stage_qwen` routing in `services/workflow.py`.
2. Keep OCR unchanged.
3. Persist raw OCR, raw field-agent responses, final JSON, validation result, confidence, and timings.
4. Ensure upload API uses invoice Excel mapping for combined exports.

Phase 5: Production hardening

1. Add deterministic tests for validation, confidence, Excel mapping, date parsing, amount parsing, and placeholder rejection.
2. Add benchmark fixtures from real bilingual invoices.
3. Compare old single-prompt engine vs staged engine on field accuracy.
4. Add optional parallel field-agent execution once local model capacity supports it.
5. Store per-field evidence in the database for reviewer UI.
6. Add country-specific VAT validators for KSA, UAE, and other target markets.
