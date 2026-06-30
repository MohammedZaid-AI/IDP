import json

def view():
    with open("scratch/evaluation_gemma_raw_results.json", "r", encoding="utf-8") as f:
        results = json.load(f)
        
    for r in results:
        if r["filename"] == "4_JY2020-07-JV000738.png":
            with open("scratch/ocr_temp.txt", "w", encoding="utf-8") as f:
                f.write(r["ocr_text"])

if __name__ == "__main__":
    view()
