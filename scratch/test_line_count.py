import numpy as np
from PIL import Image, ImageOps
from pathlib import Path

def count_lines_projection(img_path):
    # Load image and convert to grayscale
    img = Image.open(img_path).convert('L')
    
    # Invert image so text is white (255) and background is black (0)
    img_inv = ImageOps.invert(img)
    
    # Convert to numpy array
    arr = np.array(img_inv)
    
    # Sum pixels horizontally
    horizontal_sum = np.sum(arr, axis=1)
    
    # Binarize the horizontal sum to detect text vs blank space
    # Threshold can be a fraction of the maximum horizontal sum
    threshold = np.max(horizontal_sum) * 0.05
    text_lines = horizontal_sum > threshold
    
    # Count transitions from False (blank) to True (text)
    transitions = 0
    in_text = False
    for val in text_lines:
        if val and not in_text:
            transitions += 1
            in_text = True
        elif not val and in_text:
            in_text = False
            
    return transitions

def main():
    body_img_path = Path("scratch/test_body.png")
    if not body_img_path.exists():
        print(f"File {body_img_path} does not exist. Run test_crop_ocr.py first.")
        return
        
    line_count = count_lines_projection(body_img_path)
    print(f"Number of detected text lines in body crop: {line_count}")

if __name__ == "__main__":
    main()
