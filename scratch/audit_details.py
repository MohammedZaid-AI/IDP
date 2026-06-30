import json
from pathlib import Path

def main():
    with open("scratch/evaluation_gemma_raw_results.json", "r", encoding="utf-8") as f:
        gemma_results = json.load(f)
        
    with open("scratch/extracted_manual_evals.json", "r", encoding="utf-8") as f:
        manual_evals = json.load(f)
        
    output = []
    for r in gemma_results:
        filename = r["filename"]
        output.append("="*80)
        output.append(f"INVOICE: {filename}")
        output.append("="*80)
        
        # Extracted JSON
        clean_json = {k: v for k, v in r['final_json'].items() if not k.startswith("_")}
        output.append("Extracted JSON:")
        output.append(json.dumps(clean_json, ensure_ascii=False, indent=2))
        
        output.append("\nManual Evaluation Table:")
        table = manual_evals.get(filename, "No manual evaluation found.")
        output.append(table)
        output.append("\n" + "-"*80 + "\n")
        
    with open("scratch/audit_output.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(output))
    print("Audit details written to scratch/audit_output.txt")

if __name__ == "__main__":
    main()
