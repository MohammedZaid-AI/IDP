from PIL import Image
from pathlib import Path

def main():
    uploads_dir = Path("uploads")
    for img_path in sorted(uploads_dir.glob("*")):
        if img_path.suffix.lower() in [".png", ".jpg", ".jpeg", ".webp"]:
            try:
                with Image.open(img_path) as img:
                    print(f"{img_path.name}: {img.size[0]}x{img.size[1]} pixels")
            except Exception as e:
                print(f"Error reading {img_path.name}: {e}")

if __name__ == "__main__":
    main()
