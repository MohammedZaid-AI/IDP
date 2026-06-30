import base64
import httpx
from io import BytesIO
from PIL import Image
from pathlib import Path
import os
import json
import re
import sys

try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except Exception:
    pass

QARI_PROMPT = """You are an OCR engine.

Your only job is to read the document.

Return ONLY the visible text exactly as it appears.

Requirements:

- Preserve Arabic exactly.
- Preserve English exactly.
- Preserve numbers exactly.
- Preserve reading order.
- Preserve line breaks.
- Preserve labels and values.

Do NOT interpret the document.

Do NOT summarize.

Do NOT classify.

Do NOT translate.

Do NOT generate HTML.

Do NOT generate XML.

Do NOT generate Markdown.

Do NOT generate JSON.

Do NOT generate tables.

Do NOT generate bounding boxes.

Do NOT generate layout tags.

Return only plain UTF-8 text."""

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
            return res.json().get("message", {}).get("content", "").strip(), res.json().get("done_reason", "stop"), res.json().get("eval_count", 0)
        else:
            return f"Error: {res.status_code}", "error", 0
    except Exception as e:
        return f"Exception: {e}", "error", 0

def detect_and_compress(text):
    lines = text.splitlines()
    table_keywords = [
        r'\bdescription\b', r'\bqty\b', r'\bquantity\b', r'\bunit\s*price\b', 
        r'\bamount\b', r'\bprice\b', r'\bdesc\b', r'\bamt\b', r'\bitem\b',
        r'\bالوصف\b', r'\bالكمية\b', r'\bسعر\s*الوحدة\b', r'\bالاجمالي\b', 
        r'\bالسعر\b', r'\bالبيان\b'
    ]
    
    header_idx = -1
    table_header_line = ""
    for idx, line in enumerate(lines):
        if any(re.search(kw, line.lower()) for kw in table_keywords):
            header_idx = idx
            table_header_line = line
            break
            
    if header_idx == -1:
        return text, False, 0, ""
        
    footer_keywords = [
        r'\bsubtotal\b', r'\bvat\b', r'\btax\b', r'\btotal\b', r'\bdiscount\b', 
        r'\bnet\s*amount\b', r'\bgrand\s*total\b', r'\bamount\s*due\b',
        r'\bالاجمالي\b', r'\bالصافي\b', r'\bالضريبة\b', r'\bالمجموع\b'
    ]
    
    footer_idx = -1
    for idx in range(header_idx + 1, len(lines)):
        if any(re.search(kw, lines[idx].lower()) for kw in footer_keywords):
            footer_idx = idx
            break
            
    if footer_idx == -1:
        table_rows = lines[header_idx + 1:]
    else:
        table_rows = lines[header_idx + 1:footer_idx]
        
    # We estimate total lines in body region from the image using projection profile later.
    # But from text, we can see if there are table rows.
    return text, True, len(table_rows), table_header_line

def main():
    img_path = Path("uploads/1_BAHRA-CABLES-60129398.png")
    img = Image.open(img_path).convert("RGB")
    
    print("Running Pass 1: Normal full page OCR...")
    raw_text, done_reason, tokens_used = run_qari(img, QARI_PROMPT, 1000)
    print(f"Normal OCR done. Chars: {len(raw_text)}, done_reason: {done_reason}, tokens: {tokens_used}")
    
    _, has_table, rows, header_line = detect_and_compress(raw_text)
    print(f"Table detected: {has_table}, Rows in text: {rows}, Header line: {header_line}")
    
    if has_table or done_reason == "length":
        print("\nRunning Pass 2: Region-based OCR...")
        width, height = img.size
        header_crop = img.crop((0, 0, width, int(height * 0.35)))
        footer_crop = img.crop((0, int(height * 0.70), width, height))
        
        header_text, _, h_tokens = run_qari(header_crop, QARI_PROMPT, 500)
        footer_text, _, f_tokens = run_qari(footer_crop, QARI_PROMPT, 500)
        
        # Estimate total lines in body crop using horizontal projection
        from scratch.test_line_count import count_lines_projection
        body_crop = img.crop((0, int(height * 0.30), width, int(height * 0.75)))
        total_body_lines = count_lines_projection(body_crop)
        removed_rows = max(1, total_body_lines - 3)  # assume ~3 lines are header/metadata
        
        compressed_body = f"{header_line}\n[PRODUCT TABLE REMOVED - {removed_rows} ROWS]"
        
        formatted_text = f"""========== HEADER ==========
{header_text}
========== BODY ==========
{compressed_body}
========== FOOTER ==========
{footer_text}"""
        
        print("\n--- COMPRESSED OCR RESULT ---")
        print(formatted_text)
        print("-----------------------------")
        print(f"Original Chars: {len(raw_text)}, Compressed Chars: {len(formatted_text)}")
        print(f"Total tokens generated in both passes: {tokens_used + h_tokens + f_tokens}")

if __name__ == "__main__":
    main()
