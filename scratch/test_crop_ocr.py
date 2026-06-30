import base64
import httpx
from io import BytesIO
from PIL import Image
from pathlib import Path
import os
import json
import sys

try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except Exception:
    pass

def run_qari(img, prompt, num_predict=1000):
    w, h = img.size
    max_size = 1024
    if max(w, h) > max_size:
        scale = max_size / max(w, h)
        img = img.resize((int(w * scale), int(h * scale)), Image.Resampling.LANCZOS)
    
    buffered = BytesIO()
    img.save(buffered, format="PNG")
    b64_str = base64.b64encode(buffered.getvalue()).decode("ascii")

    url = "http://localhost:11434/api/chat"
    model = "hf.co/mradermacher/Qari-OCR-0.2.2.1-VL-2B-Instruct-merged-GGUF:Q4_K_M"

    payload = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": prompt,
                "images": [b64_str],
            }
        ],
        "stream": False,
        "options": {
            "temperature": 0.0,
            "num_predict": num_predict,
        }
    }

    try:
        res = httpx.post(url, json=payload, timeout=180.0)
        if res.status_code == 200:
            return res.json().get("message", {}).get("content", "").strip(), res.json().get("done_reason", "stop")
        else:
            return f"Error: {res.status_code} - {res.text}", "error"
    except Exception as e:
        return f"Exception: {e}", "error"

def main():
    img_path = Path("uploads/1_BAHRA-CABLES-60129398.png")
    if not img_path.exists():
        print(f"Image not found at {img_path}")
        return

    # Open image
    img = Image.open(img_path).convert("RGB")
    width, height = img.size
    print(f"Original image size: {width}x{height}")

    # Crop regions
    header_crop = img.crop((0, 0, width, int(height * 0.35)))
    body_crop = img.crop((0, int(height * 0.30), width, int(height * 0.75)))
    footer_crop = img.crop((0, int(height * 0.70), width, height))

    # Save crops to scratch/ for verification
    scratch_dir = Path("scratch")
    scratch_dir.mkdir(exist_ok=True)
    header_crop.save(scratch_dir / "test_header.png")
    body_crop.save(scratch_dir / "test_body.png")
    footer_crop.save(scratch_dir / "test_footer.png")
    print("Crops saved successfully.")

    # Run OCR on Header
    print("\nRunning OCR on HEADER crop...")
    header_prompt = "You are an OCR engine. Read the document. Return ONLY the visible text exactly as it appears. Do NOT interpret. Do NOT generate Markdown or JSON. Return only plain UTF-8 text."
    header_text, header_reason = run_qari(header_crop, header_prompt, num_predict=500)
    print(f"Header OCR done. Reason: {header_reason}")
    print("--- HEADER TEXT ---")
    print(header_text)
    print("-------------------")

    # Run OCR on Footer
    print("\nRunning OCR on FOOTER crop...")
    footer_prompt = "You are an OCR engine. Read the document. Return ONLY the visible text exactly as it appears. Do NOT interpret. Do NOT generate Markdown or JSON. Return only plain UTF-8 text."
    footer_text, footer_reason = run_qari(footer_crop, footer_prompt, num_predict=500)
    print(f"Footer OCR done. Reason: {footer_reason}")
    print("--- FOOTER TEXT ---")
    print(footer_text)
    print("-------------------")

    # Run OCR on Body with table compression prompt
    print("\nRunning OCR on BODY crop with compression instructions...")
    body_prompt = "You are an OCR engine. Transcribe only the table headers and the first 2 rows of the table. Then output '[PRODUCT TABLE REMOVED - 10 ROWS]' and then stop. Do not transcribe the other rows."
    body_text, body_reason = run_qari(body_crop, body_prompt, num_predict=300)
    print(f"Body OCR done. Reason: {body_reason}")
    print("--- BODY TEXT ---")
    print(body_text)
    print("-----------------")

if __name__ == "__main__":
    main()
