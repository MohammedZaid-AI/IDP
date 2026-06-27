import base64
import httpx
from io import BytesIO
from PIL import Image
from pathlib import Path

def test_file(img_name, output_name):
    img_path = Path("uploads") / img_name
    if not img_path.exists():
        print(f"Image {img_name} not found!")
        return

    # Render/resize image
    img = Image.open(img_path).convert("RGB")
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
                "role": "system",
                "content": "You are a professional OCR transcriber. Transcribe all text in the image accurately. Write each word only once. Do not repeat headers, tables, or sentences."
            },
            {
                "role": "user",
                "content": "Transcribe the text from the invoice image verbatim. Read row by row. Do not repeat headers or rows.",
                "images": [b64_str],
            }
        ],
        "stream": False,
        "options": {
            "temperature": 0.2,
            "repeat_penalty": 1.5,
            "repeat_last_n": 256,
            "num_predict": 2048,
        }
    }

    print(f"Sending {img_name} to Qari-OCR...")
    try:
        res = httpx.post(url, json=payload, timeout=180.0)
        if res.status_code == 200:
            content = res.json().get("message", {}).get("content", "").strip()
            print(f"Succeeded! Writing to scratch/{output_name}...")
            with open(f"scratch/{output_name}", "w", encoding="utf-8") as f:
                f.write(content)
        else:
            print(f"Error: {res.status_code} - {res.text}")
    except Exception as e:
        print(f"Exception: {e}")

def main():
    test_file("1_BAHRA-CABLES-60129398.png", "qari_output_bahra.txt")
    test_file("1_BAHRI-BOLLORE-JED301286.png", "qari_output_bahri.txt")
    test_file("1_CPS-CONSTRUCTION-PLANT-490.png", "qari_output_cps.txt")

if __name__ == "__main__":
    main()
