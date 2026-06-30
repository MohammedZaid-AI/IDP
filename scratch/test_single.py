import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.workflow import workflow
from services.settings import get_settings

def test_single():
    # Clear settings cache and force model/engine if needed
    get_settings.cache_clear()
    
    uploads_dir = Path("uploads")
    all_files = sorted(list(uploads_dir.glob("*")))
    supported_exts = {".pdf", ".png", ".jpg", ".jpeg", ".tiff", ".bmp", ".webp"}
    valid_files = [f for f in all_files if f.suffix.lower() in supported_exts]
    
    if not valid_files:
        print("No valid files found in uploads/")
        return
        
    test_file = valid_files[0]
    print(f"Testing pipeline with file: {test_file.name}")
    
    try:
        result = workflow.process_file(test_file)
        print("Pipeline execution succeeded!")
        print(f"Filename: {result.filename}")
        print(f"Confidence: {result.confidence}")
        print(f"Total Time: {result.processing_time:.2f}s")
        print(f"Final JSON Keys: {list(result.json_output.keys())}")
    except Exception as e:
        print(f"Pipeline execution failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_single()
