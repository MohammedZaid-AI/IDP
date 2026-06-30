import os
import sys
import json
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.workflow import workflow

# Define prompt template exactly as in qwen_llm_extractor.py to reconstruct the exact prompt sent
PROMPT_TEMPLATE = """You are a highly accurate invoice extraction engine.

Your job is to extract structured information from OCR text.

You MUST return ONLY valid JSON.
Never explain.
Never use markdown.
Never include comments.
Never include code blocks.
Never return anything except the JSON object.

GENERAL RULES:
The OCR text may contain:
- Arabic
- English
- Mixed Arabic and English
- Tables
- Product descriptions
- Headers
- Footers
- Phone numbers
- VAT numbers
- CR numbers
- PO numbers

Your job is to identify ONLY the requested invoice entities.
Never guess.
If uncertain, return an empty string or null.

VERY IMPORTANT:
For every field, return ONLY the value.
Never include labels.
Never include neighbouring lines.
Never include surrounding paragraphs.

Example:
OCR:
Vendor Name
ABC Trading Company
PO Box 123

Correct:
"vendor_name_en": "ABC Trading Company"

Wrong:
"vendor_name_en": "Vendor Name\nABC Trading Company\nPO Box 123"

DOCUMENT NUMBER:
Choose ONLY the actual invoice number.
Ignore:
- Revenue Number
- Customer Number
- CR Number
- PO Number
- Delivery Number
- Reference Number
- Serial Number
- Item Code
- Product Code
If the invoice number is empty on the document, return "".
Never guess.

VENDOR:
Return ONLY the company name.
Do NOT include:
- Address
- Phone
- Fax
- VAT
- Email
- Website
- PO Box

Correct: ABC Trading Company
Wrong:
ABC Trading Company
PO Box 123
Riyadh
Saudi Arabia

CUSTOMER:
Return ONLY the customer name.
Never include:
- Address
- PO Box
- VAT
- Reference
- Invoice Number

ADDRESS:
Return ONLY the address.
Do not include:
- Vendor name
- Customer name
- Phone
- Email
- VAT
- Invoice Number

VAT NUMBER:
Return ONLY the VAT registration number.
Never return:
- CR
- PO
- Invoice Number

DATE:
Return ONLY the invoice date.
Prefer:
- Invoice Date
- Issue Date
- Tax Invoice Date
Do NOT use:
- Delivery Date
- Supply Date
- Due Date
unless the invoice date is missing.

AMOUNTS:
Extract ONLY:
- subtotal
- tax_amount
- total_amount
Ignore:
- Unit Price
- Quantity
- Line Total
- Product Total
- Discount %

LANGUAGE:
If the text is Arabic, store it in the Arabic field.
If the text is English, store it in the English field.
Never translate.
Never duplicate Arabic into English.
Never duplicate English into Arabic.

NEGATIVE EXAMPLES:

Wrong vendor_name:
ABC Trading
PO Box 123
Riyadh
Correct vendor_name:
ABC Trading

Wrong document_number:
Invoice Number
PO Box 123
Correct document_number:
736

Wrong address:
ABC Trading
PO Box
VAT Number
Phone
Correct address:
PO Box 123
Riyadh
Saudi Arabia

OUTPUT FORMAT:
Return EXACTLY a JSON object with this structure:
{
    "document_number": "",
    "vat_number": "",
    "document_date": "",
    "currency": "",
    "vendor_name_ar": "",
    "vendor_name_en": "",
    "customer_name_ar": "",
    "customer_name_en": "",
    "address_ar": "",
    "address_en": "",
    "subtotal": null,
    "tax_amount": null,
    "total_amount": null
}

OCR TEXT:
"""

def main():
    uploads_dir = Path("uploads")
    all_files = sorted(list(uploads_dir.glob("*")))
    supported_exts = {".pdf", ".png", ".jpg", ".jpeg", ".tiff", ".bmp", ".webp"}
    valid_files = [f for f in all_files if f.suffix.lower() in supported_exts]
    
    print(f"Found {len(valid_files)} valid files in uploads/")
    results = []
    
    for i, file_path in enumerate(valid_files, 1):
        print(f"\n[{i}/{len(valid_files)}] Processing {file_path.name}...")
        try:
            res = workflow.process_file(file_path)
            
            # Reconstruct exact prompt
            exact_prompt = PROMPT_TEMPLATE + res.raw_text
            
            # Try to parse parsed JSON (before validation)
            parsed_json = workflow._qwen_llm_extractor._parse_json(res.raw_llm_response) or {}
            
            results.append({
                "filename": file_path.name,
                "ocr_text": res.raw_text,
                "prompt": exact_prompt,
                "raw_qwen_response": res.raw_llm_response,
                "parsed_json": parsed_json,
                "final_json": res.json_output,
                "timings": {
                    "ocr_time": res.processing_timings.get("ocr_time", 0.0),
                    "llm_time": res.processing_timings.get("extraction_time", 0.0),
                    "validation_time": res.processing_timings.get("validation_time", 0.0),
                    "total_time": res.processing_time
                },
                "confidence": res.confidence
            })
        except Exception as e:
            print(f"Failed to process {file_path.name}: {e}")
            results.append({
                "filename": file_path.name,
                "ocr_text": f"ERROR: {e}",
                "prompt": "",
                "raw_qwen_response": "",
                "parsed_json": {},
                "final_json": {},
                "timings": {
                    "ocr_time": 0.0,
                    "llm_time": 0.0,
                    "validation_time": 0.0,
                    "total_time": 0.0
                },
                "confidence": 0.0
            })
            
    # Save raw results
    out_dir = Path("C:/Users/MOHAMMED ZAID/.gemini/antigravity-ide/brain/3403273f-eefb-4002-9ec3-5d7f73f59799")
    out_dir.mkdir(parents=True, exist_ok=True)
    with open(out_dir / "evaluation_15_raw_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
        
    print(f"\nRaw results saved to {out_dir / 'evaluation_15_raw_results.json'}")

if __name__ == "__main__":
    main()
