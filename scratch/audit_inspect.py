import json
from pathlib import Path

def main():
    qwen_path = Path("C:/Users/MOHAMMED ZAID/.gemini/antigravity-ide/brain/3403273f-eefb-4002-9ec3-5d7f73f59799/evaluation_15_raw_results.json")
    gemma_path = Path("scratch/evaluation_gemma_raw_results.json")
    
    print(f"Qwen JSON exists: {qwen_path.exists()}")
    print(f"Gemma JSON exists: {gemma_path.exists()}")
    
    if qwen_path.exists():
        with open(qwen_path, "r", encoding="utf-8") as f:
            qwen_data = json.load(f)
        print(f"Qwen processed {len(qwen_data)} invoices:")
        for idx, r in enumerate(qwen_data, 1):
            print(f"  {idx}. {r['filename']}")
    else:
        qwen_data = []
            
    if gemma_path.exists():
        with open(gemma_path, "r", encoding="utf-8") as f:
            gemma_data = json.load(f)
        print(f"Gemma processed {len(gemma_data)} invoices:")
        for idx, r in enumerate(gemma_data, 1):
            print(f"  {idx}. {r['filename']}")
    else:
        gemma_data = []

if __name__ == "__main__":
    main()
