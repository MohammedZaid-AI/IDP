import os
import sys
import json
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.workflow import workflow
from services.settings import get_settings

try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except Exception:
    pass

def main():
    print("="*60)
    print("STARTING REDESIGNED OCR PIPELINE EVALUATION")
    print("="*60)

    uploads_dir = Path("uploads")
    all_files = sorted(list(uploads_dir.glob("*")))
    supported_exts = {".pdf", ".png", ".jpg", ".jpeg", ".tiff", ".bmp", ".webp"}
    valid_files = [f for f in all_files if f.suffix.lower() in supported_exts]

    print(f"Found {len(valid_files)} invoices in uploads/ to process.")
    results = []

    # Initialize stats file to clean slate
    stats_path = Path("scratch/ocr_stats.json")
    if stats_path.exists():
        try:
            stats_path.unlink()
        except Exception:
            pass

    for i, file_path in enumerate(valid_files, 1):
        print(f"\n[{i}/{len(valid_files)}] Processing {file_path.name}...")
        try:
            # Execute workflow
            res = workflow.process_file(file_path)
            json_output = res.json_output or {}

            # Read stats written during OCR stage
            raw_len = 0
            comp_len = 0
            done_reason = "unknown"
            tokens_used = 0

            if stats_path.exists():
                with open(stats_path, "r", encoding="utf-8") as sf:
                    ocr_stats = json.load(sf)
                    stats = ocr_stats.get(file_path.name, {})
                    raw_len = stats.get("raw_len", 0)
                    comp_len = stats.get("comp_len", 0)
                    done_reason = stats.get("done_reason", "unknown")
                    tokens_used = stats.get("tokens_used", 0)

            # Metadata recovery status
            inv_number = json_output.get("document_number")
            vendor_en = json_output.get("vendor_name_en")
            vendor_ar = json_output.get("vendor_name_ar")
            cust_en = json_output.get("customer_name_en")
            cust_ar = json_output.get("customer_name_ar")
            total = json_output.get("total_amount")

            inv_recovered = "Yes" if inv_number else "No"
            vendor_recovered = "Yes" if (vendor_en or vendor_ar) else "No"
            cust_recovered = "Yes" if (cust_en or cust_ar) else "No"
            totals_recovered = "Yes" if (total is not None) else "No"

            reduction = 0.0
            if raw_len > 0:
                reduction = (raw_len - comp_len) / raw_len * 100.0

            results.append({
                "filename": file_path.name,
                "raw_len": raw_len,
                "comp_len": comp_len,
                "reduction_pct": reduction,
                "inv_recovered": inv_recovered,
                "vendor_recovered": vendor_recovered,
                "cust_recovered": cust_recovered,
                "totals_recovered": totals_recovered,
                "done_reason": done_reason,
                "tokens_used": tokens_used
            })

            print(f"Processed: {file_path.name}")
            print(f"  Raw OCR length: {raw_len}")
            print(f"  Compressed OCR length: {comp_len} (Reduction: {reduction:.2f}%)")
            print(f"  Invoice #: {inv_recovered}, Vendor: {vendor_recovered}, Customer: {cust_recovered}, Totals: {totals_recovered}")
            print(f"  Done Reason: {done_reason}, Tokens Used: {tokens_used}")

        except Exception as e:
            print(f"Error processing {file_path.name}: {e}")
            results.append({
                "filename": file_path.name,
                "raw_len": 0,
                "comp_len": 0,
                "reduction_pct": 0.0,
                "inv_recovered": "Error",
                "vendor_recovered": "Error",
                "cust_recovered": "Error",
                "totals_recovered": "Error",
                "done_reason": "error",
                "tokens_used": 0
            })

    # Generate Markdown Report
    report_content = []
    report_content.append("# Redesigned OCR Pipeline Evaluation Report\n")
    report_content.append("This report evaluates the performance of the redesigned region-based OCR preprocessing pipeline on the invoice dataset in `uploads/`.\n")
    
    report_content.append("## OCR Redesign Results Table\n")
    report_content.append("| Invoice Filename | Original OCR Chars | Compressed OCR Chars | Reduction % | Invoice # | Vendor | Customer | Totals | Ends in done_reason=\"length\"? |")
    report_content.append("| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |")
    
    total_raw = 0
    total_comp = 0
    total_reduction = 0.0
    count = len(results)
    
    for r in results:
        ends_in_length = "Yes" if r["done_reason"] == "length" else "No"
        report_content.append(f"| {r['filename']} | {r['raw_len']} | {r['comp_len']} | {r['reduction_pct']:.2f}% | {r['inv_recovered']} | {r['vendor_recovered']} | {r['cust_recovered']} | {r['totals_recovered']} | {ends_in_length} |")
        total_raw += r["raw_len"]
        total_comp += r["comp_len"]
        total_reduction += r["reduction_pct"]

    avg_reduction = total_reduction / count if count > 0 else 0.0
    report_content.append(f"\n**Averages / Totals:**")
    report_content.append(f"- **Total Original Characters:** {total_raw}")
    report_content.append(f"- **Total Compressed Characters:** {total_comp}")
    report_content.append(f"- **Average Size Reduction:** {avg_reduction:.2f}%")
    
    report_path = Path("scratch/ocr_redesign_report.md")
    report_path.write_text("\n".join(report_content), encoding="utf-8")
    print(f"\nEvaluation completed. Report generated at {report_path}")

if __name__ == "__main__":
    main()
