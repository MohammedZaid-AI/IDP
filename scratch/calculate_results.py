import json
from pathlib import Path

def main():
    json_path = Path("C:/Users/MOHAMMED ZAID/.gemini/antigravity-ide/brain/3403273f-eefb-4002-9ec3-5d7f73f59799/evaluation_15_raw_results.json")
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    output_lines = []
    output_lines.append(f"Total processed: {len(data)}")
    
    total_ocr_time = 0.0
    total_llm_time = 0.0
    total_total_time = 0.0
    
    for r in data:
        t = r["timings"]
        total_ocr_time += t["ocr_time"]
        total_llm_time += t["llm_time"]
        total_total_time += t["total_time"]
        
    avg_ocr = total_ocr_time / len(data) if data else 0
    avg_llm = total_llm_time / len(data) if data else 0
    avg_total = total_total_time / len(data) if data else 0
    
    output_lines.append(f"Average OCR Time: {avg_ocr:.2f} s")
    output_lines.append(f"Average LLM Time: {avg_llm:.2f} s")
    output_lines.append(f"Average Total Time: {avg_total:.2f} s")
    output_lines.append("\n" + "="*50 + "\n")
    
    for idx, r in enumerate(data, 1):
        output_lines.append(f"Invoice {idx}: {r['filename']}")
        output_lines.append(f"OCR Time: {r['timings']['ocr_time']:.2f}s | LLM Time: {r['timings']['llm_time']:.2f}s | Total: {r['timings']['total_time']:.2f}s")
        output_lines.append(f"Confidence: {r['confidence']:.2f}")
        output_lines.append("Final JSON:")
        clean_json = {k: v for k, v in r['final_json'].items() if not k.startswith("_")}
        output_lines.append(json.dumps(clean_json, ensure_ascii=False, indent=2))
        output_lines.append("Issues:")
        output_lines.append(json.dumps(r['final_json'].get("_validation", {}).get("issues", []), ensure_ascii=False, indent=2))
        
        # Add a snippet of OCR text (first 10 lines)
        ocr_lines = r['ocr_text'].splitlines()
        output_lines.append("OCR Preview:")
        output_lines.append("\n".join(ocr_lines[:15]))
        output_lines.append("\n" + "-"*30 + "\n")

    out_file = Path("scratch/formatted_results.txt")
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text("\n".join(output_lines), encoding="utf-8")
    print(f"Results written to {out_file.absolute()}")

if __name__ == "__main__":
    main()
