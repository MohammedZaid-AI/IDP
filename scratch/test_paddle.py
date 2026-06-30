import sys
from pathlib import Path
from paddleocr import PaddleOCR

def main():
    print("Initializing PaddleOCR...")
    try:
        # Initialize PaddleOCR
        ocr = PaddleOCR(lang='en')
        print("PaddleOCR initialized successfully.")
        
        # Test on one invoice image
        img_path = Path("uploads/1_BAHRA-CABLES-60129398.png")
        if not img_path.exists():
            print(f"Image {img_path} not found.")
            return
            
        print(f"Running PaddleOCR on {img_path}...")
        result = ocr.predict(str(img_path))
        print(f"OCR result type: {type(result)}")
        print(result)
        
    except Exception as e:
        import traceback
        print(f"Error: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    main()
