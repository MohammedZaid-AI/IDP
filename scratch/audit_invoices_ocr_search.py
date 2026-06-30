import json
import re
from pathlib import Path

def audit():
    with open("scratch/evaluation_gemma_raw_results.json", "r", encoding="utf-8") as f:
        results = json.load(f)
        
    with open("scratch/extracted_manual_evals.json", "r", encoding="utf-8") as f:
        manual_evals = json.load(f)
        
    output = []
    for r in results:
        filename = r["filename"]
        ocr = r["ocr_text"]
        fj = r["final_json"]
        
        output.append("="*80)
        output.append(f"AUDITING: {filename}")
        output.append("="*80)
        
        # 1. Check for VAT numbers
        vat_matches = re.findall(r'\b\d{15}\b', ocr)
        extracted_vat = fj.get("vat_number")
        output.append(f"OCR 15-digit VAT candidates: {vat_matches}")
        output.append(f"Extracted VAT: '{extracted_vat}'")
        
        # 2. Check for dates
        date_candidates = re.findall(r'\b\d{1,4}[-/\.]\d{1,2}[-/\.]\d{1,4}\b', ocr)
        extracted_date = fj.get("document_date")
        output.append(f"OCR date candidates: {date_candidates}")
        output.append(f"Extracted Date: '{extracted_date}'")
        
        # 3. Check for amounts
        amounts = re.findall(r'\b\d+\.\d{2}\b', ocr)
        output.append(f"OCR decimal amount candidates: {list(set(amounts))[:10]}")
        output.append(f"Extracted subtotal/tax/total: sub={fj.get('subtotal')}, tax={fj.get('tax_amount')}, total={fj.get('total_amount')}")
        
        # 4. Check manual table for this file
        output.append("\nManual Evaluation Table:")
        table = manual_evals.get(filename, "None")
        for line in table.splitlines():
            if any(f in line for f in ["VAT", "Date", "Subtotal", "Tax", "Total"]):
                output.append("   " + line)
        output.append("\n")
        
    with open("scratch/ocr_search_output.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(output))
    print("OCR audit search written to scratch/ocr_search_output.txt")

if __name__ == "__main__":
    audit()
