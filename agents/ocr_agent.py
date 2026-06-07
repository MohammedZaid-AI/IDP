import fitz
import easyocr
import os

reader = easyocr.Reader(
    ['en', 'ar'],
    gpu=False
)

IMAGE_EXTENSIONS = [
    ".png",
    ".jpg",
    ".jpeg",
    ".bmp",
    ".tiff",
    ".webp"
]


def extract_text(file_path):

    ext = os.path.splitext(
        file_path
    )[1].lower()

    # IMAGE

    if ext in IMAGE_EXTENSIONS:

        result = reader.readtext(
            file_path,
            detail=0
        )

        return "\n".join(result)

    # PDF

    text = ""

    doc = fitz.open(file_path)

    for page_num in range(len(doc)):

        page = doc[page_num]

        pix = page.get_pixmap()

        image_file = f"temp_{page_num}.png"

        pix.save(image_file)

        result = reader.readtext(
            image_file,
            detail=0
        )

        text += "\n".join(result)

    return text