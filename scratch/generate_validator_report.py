import json
import time
import os
import sys
from pathlib import Path

# Add project root to sys.path so we can import services
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from services.qwen_llm_extractor import QwenLlmExtractionService

def main():
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

    cache_path = Path("scratch/evaluation_gemma_raw_results.json")
    if not cache_path.exists():
        print(f"Error: Cache file {cache_path} not found.")
        sys.exit(1)

    with open(cache_path, "r", encoding="utf-8") as f:
        cache_data = json.load(f)

    # Initialize extraction service to access our new validation logic
    service = QwenLlmExtractionService()

    report_lines = []
    report_lines.append("# Redesigned Validation Layer Evaluation Report\n")
    report_lines.append("This report compares the performance and confidence scores of the new OCR-aware validation layer against the previous validation layer on the invoice dataset in `uploads/`.\n")
    report_lines.append("## Validation Changes Results Table\n")
    report_lines.append("| Invoice Filename | Prev Conf | New Conf | Confidence Change | Prev Validation | New Validation | Validation Change | Highlight (Confidence Increased)? |")
    report_lines.append("| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |")

    increased_count = 0
    total_count = len(cache_data)

    print(f"Loaded {total_count} invoices from cache. Starting validation runs...")

    for idx, entry in enumerate(cache_data):
        filename = entry["filename"]
        ocr_text = entry["ocr_text"]
        parsed_json = entry["parsed_json"]
        
        # Safe fallback for confidence
        prev_conf = entry.get("confidence", 0.0)
        
        # Get previous validation status
        final_json = entry.get("final_json", {})
        prev_validation = final_json.get("_validation", {})
        prev_valid_status = "PASS" if prev_validation.get("valid", False) else "FAIL"
        
        # Run the new validation method
        started = time.perf_counter()
        res = service._validate_and_score(
            extracted=parsed_json,
            ocr_text=ocr_text,
            llm_response=entry.get("raw_gemma_response", ""),
            prompt=entry.get("prompt", ""),
            started_time=started
        )
        
        new_conf = res.get("_confidence", 0.0)
        new_validation = res.get("_validation", {})
        new_valid_status = "PASS" if new_validation.get("valid", False) else "FAIL"
        
        conf_diff = round(new_conf - prev_conf, 2)
        conf_diff_str = f"+{conf_diff}" if conf_diff > 0 else str(conf_diff)
        
        highlight = "❌"
        if conf_diff > 0:
            highlight = "**YES (+{:.2f})** 🚀".format(conf_diff)
            increased_count += 1
        elif conf_diff == 0:
            highlight = "No Change"
        else:
            highlight = "Decreased ({:.2f})".format(conf_diff)

        validation_diff = "No Change"
        if prev_valid_status != new_valid_status:
            validation_diff = f"{prev_valid_status} ➔ {new_valid_status}"

        report_lines.append(
            f"| {filename} | {prev_conf:.2f} | {new_conf:.2f} | {conf_diff_str} | {prev_valid_status} | {new_valid_status} | {validation_diff} | {highlight} |"
        )
        print(f"[{idx+1}/{total_count}] Processed {filename}: Conf {prev_conf} -> {new_conf} ({new_valid_status})")

    report_lines.append("\n## Summary Metrics")
    report_lines.append(f"- **Total Invoices Evaluated:** {total_count}")
    report_lines.append(f"- **Invoices with Increased Confidence:** {increased_count} / {total_count} ({increased_count/total_count*100:.1f}%)")
    report_lines.append(f"- **False Negatives Cleared:** Highlighted above in Validation Change where status transitioned from FAIL to PASS.")

    report_content = "\n".join(report_lines)

    output_path = Path("scratch/validator_redesign_report.md")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(report_content)

    print(f"\nEvaluation completed. Report generated at {output_path}")

if __name__ == "__main__":
    main()
