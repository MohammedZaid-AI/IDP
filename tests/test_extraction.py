import os
from pathlib import Path
from services.workflow import workflow

def test_bahra_invoice_extraction():
    file_path = Path(os.path.join(os.getcwd(), "uploads", "1_BAHRA-CABLES-60129398.png"))
    
    result = workflow.process_file(file_path)
    extracted = result.json_output
    
    print("BAHRA RAW OCR:", result.raw_text)
    print("BAHRA JSON:", extracted)
    assert extracted.get("total_amount") is not None
    if extracted.get("tax_amount") is not None:
        assert extracted.get("tax_amount") > 0

def test_bahri_invoice_extraction():
    file_path = Path(os.path.join(os.getcwd(), "uploads", "1_BAHRI-BOLLORE-JED301286.png"))
    
    result = workflow.process_file(file_path)
    extracted = result.json_output
    
    print("BAHRI JSON:", extracted)
    assert extracted.get("total_amount") is not None

def test_cps_invoice_extraction():
    file_path = Path(os.path.join(os.getcwd(), "uploads", "1_CPS-CONSTRUCTION-PLANT-490.png"))
    
    result = workflow.process_file(file_path)
    extracted = result.json_output
    
    print("CPS RAW OCR:", result.raw_text)
    print("CPS JSON:", extracted)
    assert extracted.get("total_amount") is not None

def main():
    print("Testing BAHRA...")
    test_bahra_invoice_extraction()
    print("Testing BAHRI...")
    test_bahri_invoice_extraction()
    print("Testing CPS...")
    test_cps_invoice_extraction()
    print("All tests passed!")

if __name__ == "__main__":
    # Force engine to qwen_llm
    os.environ["EXTRACTION_ENGINE"] = "qwen_llm"
    from dotenv import load_dotenv
    load_dotenv()
    from services.settings import get_settings
    get_settings.cache_clear()
    
    main()
