import re
import json
import pathlib

def extract_manual_evals():
    report_path = pathlib.Path("gemma4_evaluation_report.md")
    if not report_path.exists():
        print("gemma4_evaluation_report.md does not exist.")
        return {}

    content = report_path.read_text(encoding='utf-8')
    # Split content by invoice sections
    invoice_sections = content.split("# Invoice: ")
    
    manual_evals = {}
    
    for section in invoice_sections[1:]:
        lines = section.splitlines()
        filename = lines[0].strip()
        
        # Find the table
        table_lines = []
        in_table = False
        for line in lines:
            if "| Field | Status | Notes |" in line or "| Field            | Status | Notes |" in line:
                in_table = True
                table_lines.append(line)
                continue
            if in_table:
                if line.strip().startswith("|"):
                    table_lines.append(line)
                else:
                    in_table = False
        
        manual_evals[filename] = "\n".join(table_lines)
        
    print(f"Extracted manual evaluations for {len(manual_evals)} invoices.")
    return manual_evals

if __name__ == "__main__":
    evals = extract_manual_evals()
    # Save to json for reference
    with open("scratch/extracted_manual_evals.json", "w", encoding="utf-8") as f:
        json.dump(evals, f, ensure_ascii=False, indent=2)
