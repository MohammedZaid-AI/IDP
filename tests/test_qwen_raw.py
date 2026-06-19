import asyncio
import os
from pathlib import Path

# Force engine to qwen_llm
os.environ["EXTRACTION_ENGINE"] = "qwen_llm"
from services.settings import get_settings
get_settings.cache_clear()

from services.qwen_vision_ocr import QwenVisionOCRService

def main():
    service = QwenVisionOCRService()
    
    file_path_cps = Path(os.path.join(os.getcwd(), "uploads", "1_CPS-CONSTRUCTION-PLANT-490_117a62149c7d.png"))
    
    res_cps = service.extract_text(file_path_cps)
    print("CPS Qwen Output:")
    print("----------------")
    print(res_cps)
    print("----------------")
    
    file_path_bahra = Path(os.path.join(os.getcwd(), "uploads", "1_BAHRA-CABLES-60129398_127fa610fe34.png"))
        
    res_bahra = service.extract_text(file_path_bahra)
    print("BAHRA Qwen Output:")
    print("----------------")
    print(res_bahra)
    print("----------------")

if __name__ == "__main__":
    main()
