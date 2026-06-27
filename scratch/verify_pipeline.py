import sys
import os
import re
import json
from pathlib import Path

# Configure stdout/stderr to handle UTF-8
try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except Exception:
    pass

# Ensure project root is in path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from services.merge_extractor import HybridInvoiceExtractionService

def main():
    if len(sys.argv) < 2:
        print("Usage: python scratch/verify_pipeline.py <path_to_invoice_image>")
        sys.exit(1)
        
    path = Path(sys.argv[1])
    if not path.exists():
        print(f"Error: File not found at {path}")
        sys.exit(1)
        
    print(f"Initializing production extraction service...")
    service = HybridInvoiceExtractionService()
    service.ensure_initialized()

    print(f"Running end-to-end pipeline on: {path.name}")
    
    # Execute the exact production pipeline end-to-end
    result = service.extract(path)
    
    # Retrieve the exact prompt, raw response, and parsed JSON stored on the extractor
    prompt = getattr(service.ollama_extractor, "last_prompt", "")
    raw_ollama_response = getattr(service.ollama_extractor, "last_raw_response", "")
    parsed_before_merge = getattr(service.ollama_extractor, "last_parsed_json", {})

    print("\n========================")
    print("1. Raw Paddle OCR output")
    print("========================\n")
    print(result.ocr_text)
    
    print("\n========================")
    print("2. Raw Qari OCR output")
    print("========================\n")
    print(result.qari_ocr_text)
    
    print("\n========================")
    print("3. repr(qari_text)")
    print("========================\n")
    print(repr(result.qari_ocr_text))
    
    print("\n========================")
    print("4. The exact prompt sent to Ollama")
    print("========================\n")
    print(prompt)
    
    print("\n========================")
    print("5. The raw Ollama response")
    print("========================\n")
    print(raw_ollama_response)
    
    print("\n========================")
    print("6. The parsed JSON before merge")
    print("========================\n")
    print(json.dumps(parsed_before_merge, ensure_ascii=False, indent=2))
    
    print("\n========================")
    print("7. The final merged JSON after validation")
    print("========================\n")
    print(json.dumps(result.extracted_json, ensure_ascii=False, indent=2))
    print("\n" + "#" * 60 + "\n")

if __name__ == "__main__":
    main()
