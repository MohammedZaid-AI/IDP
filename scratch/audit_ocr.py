import json

def audit_ocr():
    with open("scratch/evaluation_gemma_raw_results.json", "r", encoding="utf-8") as f:
        results = json.load(f)
        
    targets = [
        "20220820_160841493.jpg",
        "20220820_160954815.jpg",
        "20220820_161037175.jpg",
        "1_BAIT-AL-BAKOURAH-50005.png"
    ]
    
    output = []
    for r in results:
        if r["filename"] in targets:
            output.append("="*80)
            output.append(f"FILE: {r['filename']}")
            output.append("="*80)
            output.append("OCR TEXT:")
            output.append(r["ocr_text"])
            output.append("\nEXTRACTED JSON:")
            clean_json = {k: v for k, v in r['final_json'].items() if not k.startswith("_")}
            output.append(json.dumps(clean_json, ensure_ascii=False, indent=2))
            output.append("\n")
            
    with open("scratch/audit_ocr_output.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(output))
    print("OCR audit written to scratch/audit_ocr_output.txt")

if __name__ == "__main__":
    audit_ocr()
