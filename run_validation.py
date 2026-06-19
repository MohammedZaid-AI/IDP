import os
import sys
from pathlib import Path
import json
import pandas as pd
import time

# Ensure project root is in path
sys.path.insert(0, str(Path(__file__).resolve().parent))

# Force paddle_qwen extraction engine
os.environ["EXTRACTION_ENGINE"] = "paddle_qwen"

from services.workflow import workflow

def run_validation():
    print("Starting automated validation run for paddle_qwen pipeline...")
    
    uploads_dir = Path("uploads")
    # Gather image files
    extensions = [".png", ".jpg", ".jpeg", ".pdf"]
    invoice_files = []
    for ext in extensions:
        invoice_files.extend(list(uploads_dir.glob(f"*{ext}")))
    
    # Sort files alphabetically
    invoice_files.sort(key=lambda x: x.name)
    
    # Take the first 20 invoices
    target_files = invoice_files[:20]
    
    print(f"Total files in uploads: {len(invoice_files)}")
    print(f"Selecting first 20 files to process:")
    for f in target_files:
        print(f"  - {f.name}")
        
    results = []
    failed_invoices = []
    
    for file_path in target_files:
        print(f"\nProcessing {file_path.name}...")
        try:
            start_time = time.perf_counter()
            result = workflow.process_file(file_path)
            total_time = time.perf_counter() - start_time
            
            ext_json = result.json_output or {}
            timings = result.processing_timings or {}
            
            ocr_time = timings.get("ocr_time", 0.0)
            llm_time = timings.get("extraction_time", 0.0)
            
            row = {
                "Filename": file_path.name,
                "Document Number": ext_json.get("document_number"),
                "Vendor": ext_json.get("vendor_name"),
                "Customer": ext_json.get("customer_name"),
                "Subtotal": ext_json.get("subtotal"),
                "Tax Amount": ext_json.get("tax_amount"),
                "Total Amount": ext_json.get("total_amount"),
                "Confidence": result.confidence,
                "OCR Time": ocr_time,
                "LLM Time": llm_time,
                "Total Time": total_time
            }
            results.append(row)
            print(f"SUCCESS: {file_path.name} | Total Time: {total_time:.2f}s")
        except Exception as exc:
            print(f"FAILED: {file_path.name} | Exception: {exc}")
            failed_invoices.append({
                "filename": file_path.name,
                "error": str(exc)
            })
            
    # Create pandas DataFrame
    df = pd.DataFrame(results)
    
    # Save to Excel
    report_path = "validation_report.xlsx"
    df.to_excel(report_path, index=False)
    print(f"\nValidation report saved to {report_path}")
    
    # Generate Summary Metrics
    total_processed = len(results)
    
    if total_processed > 0:
        avg_ocr_latency = df["OCR Time"].mean()
        avg_total_latency = df["Total Time"].mean()
        
        def pct_populated(col):
            populated = df[col].apply(lambda x: x not in (None, "", [], {}))
            return float((populated.sum() / total_processed) * 100.0)
            
        pct_subtotal = pct_populated("Subtotal")
        pct_tax = pct_populated("Tax Amount")
        pct_total = pct_populated("Total Amount")
        pct_doc_num = pct_populated("Document Number")
        pct_vendor = pct_populated("Vendor")
    else:
        avg_ocr_latency = 0.0
        avg_total_latency = 0.0
        pct_subtotal = 0.0
        pct_tax = 0.0
        pct_total = 0.0
        pct_doc_num = 0.0
        pct_vendor = 0.0
        
    summary = {
        "total_invoices_processed": total_processed,
        "average_ocr_latency": round(avg_ocr_latency, 4),
        "average_total_latency": round(avg_total_latency, 4),
        "percentage_with_subtotal_populated": round(pct_subtotal, 2),
        "percentage_with_tax_populated": round(pct_tax, 2),
        "percentage_with_total_populated": round(pct_total, 2),
        "percentage_with_invoice_number_populated": round(pct_doc_num, 2),
        "percentage_with_vendor_populated": round(pct_vendor, 2)
    }
    
    summary_path = "validation_summary.json"
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"Validation summary saved to {summary_path}")
    
    print("\nSummary metrics:")
    print(json.dumps(summary, indent=2))
    
    if failed_invoices:
        print("\nFailed Invoices:")
        for fail in failed_invoices:
            print(f"  - {fail['filename']}: {fail['error']}")
            
    # Also write failed invoices list to a json file for return
    with open("failed_invoices.json", "w") as f:
        json.dump(failed_invoices, f, indent=2)

if __name__ == "__main__":
    run_validation()
