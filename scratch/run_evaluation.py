import os
import sys
import json
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.workflow import workflow

def run_evaluation():
    uploads_dir = Path("uploads")
    # Find all uploads
    all_files = sorted(list(uploads_dir.glob("*")))
    supported_exts = {".pdf", ".png", ".jpg", ".jpeg", ".tiff", ".bmp", ".webp"}
    valid_files = [f for f in all_files if f.suffix.lower() in supported_exts]
    
    # Deduplicate files that are identical copies (same prefix) and exclude Bahra Cables
    seen_prefixes = set()
    selected_files = []
    for f in valid_files:
        if "BAHRA" in f.name.upper():
            continue
        # e.g., 1_BAHRI-BOLLORE-JED301286.png -> 1_BAHRI-BOLLORE-JED301286
        base_prefix = f.name.split("_")[0] + "_" + f.name.split("_")[1].split("-")[0] if len(f.name.split("_")) > 1 else f.name
        if base_prefix not in seen_prefixes:
            seen_prefixes.add(base_prefix)
            selected_files.append(f)
        if len(selected_files) >= 10:
            break
            
    # If we still have fewer than 10 unique prefixes, fill in with any remaining non-Bahra files
    if len(selected_files) < 10:
        for f in valid_files:
            if "BAHRA" in f.name.upper():
                continue
            if f not in selected_files:
                selected_files.append(f)
            if len(selected_files) >= 10:
                break

    print(f"Selected {len(selected_files)} files for evaluation:")
    for f in selected_files:
        print(f" - {f.name}")
        
    report_data = []
    failed_invoices = []
    
    for i, file_path in enumerate(selected_files, 1):
        print(f"\nProcessing [{i}/{len(selected_files)}]: {file_path.name}")
        start_time = time.perf_counter()
        try:
            result = workflow.process_file(file_path)
            duration = time.perf_counter() - start_time
            
            # Check validation status
            is_valid = result.validation.valid
            if not is_valid:
                failed_invoices.append(file_path.name)
                
            report_data.append({
                "filename": file_path.name,
                "ocr_text": result.raw_text,
                "raw_qwen_response": result.raw_llm_response,
                "final_json": result.json_output,
                "validation": result.validation.model_dump(),
                "duration": duration,
                "confidence": result.confidence,
                "status": "Success" if is_valid else "Validation Failed"
            })
        except Exception as e:
            duration = time.perf_counter() - start_time
            print(f"Error processing {file_path.name}: {e}")
            failed_invoices.append(file_path.name)
            report_data.append({
                "filename": file_path.name,
                "ocr_text": "ERROR",
                "raw_qwen_response": f"ERROR: {str(e)}",
                "final_json": {},
                "validation": {"valid": False, "issues": [{"field": "system", "message": str(e), "severity": "error"}]},
                "duration": duration,
                "confidence": 0.0,
                "status": "System Error"
            })

    # Generate Markdown Report
    report_md = []
    report_md.append("# Invoice Extraction Evaluation Report\n")
    report_md.append(f"Processed **{len(selected_files)}** files using the new simplified pipeline.\n")
    
    report_md.append("## Summary Statistics\n")
    success_count = sum(1 for r in report_data if r["status"] == "Success")
    avg_time = sum(r["duration"] for r in report_data) / len(report_data) if report_data else 0
    report_md.append(f"- **Total Processed**: {len(report_data)}")
    report_md.append(f"- **Valid Invoices (Passed Validation)**: {success_count}")
    report_md.append(f"- **Failed Invoices**: {len(failed_invoices)}")
    report_md.append(f"- **Average Processing Time**: {avg_time:.2f} seconds\n")
    
    if failed_invoices:
        report_md.append("### Failed Invoices List\n")
        for f in failed_invoices:
            report_md.append(f"- {f}")
        report_md.append("\n")
        
    report_md.append("## Detailed Results\n")
    for r in report_data:
        report_md.append(f"### File: {r['filename']}\n")
        report_md.append(f"- **Status**: {r['status']}")
        report_md.append(f"- **Processing Time**: {r['duration']:.2f}s")
        report_md.append(f"- **Confidence Score**: {r['confidence']}")
        
        # OCR Text (snippet)
        ocr_snippet = r['ocr_text']
        if len(ocr_snippet) > 500:
            ocr_snippet = ocr_snippet[:250] + "\n... [TRUNCATED] ...\n" + ocr_snippet[-250:]
        report_md.append("#### OCR Output snippet\n```\n" + ocr_snippet + "\n```\n")
        
        # Raw response
        report_md.append("#### Raw Qwen Response\n```json\n" + r['raw_qwen_response'] + "\n```\n")
        
        # Final JSON
        final_json_str = json.dumps(r['final_json'], ensure_ascii=False, indent=2)
        report_md.append("#### Final JSON\n```json\n" + final_json_str + "\n```\n")
        
        # Validation Results
        validation_str = json.dumps(r['validation'], ensure_ascii=False, indent=2)
        report_md.append("#### Validation Results\n```json\n" + validation_str + "\n```\n")
        
        report_md.append("---\n")
        
    # Write to a report file
    output_path = Path("C:/Users/MOHAMMED ZAID/.gemini/antigravity-ide/brain/3403273f-eefb-4002-9ec3-5d7f73f59799/evaluation_report.md")
    output_path.write_text("\n".join(report_md), encoding="utf-8")
    print(f"\nEvaluation finished. Report generated at {output_path}")

if __name__ == "__main__":
    run_evaluation()
