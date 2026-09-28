from PIL import Image
import pytesseract
import sys

# Tell pytesseract where Tesseract is installed
pytesseract.pytesseract.tesseract_cmd = (
    r"C:\Program Files\Tesseract-OCR\tesseract.exe"
)


def extract_text(image_path: str) -> str:
    image = Image.open(image_path)

    # OCR
    text = pytesseract.image_to_string(
        image,
        config="--psm 6"
    )

    return text.strip()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage:")
        print("python ocr_test.py prescription.jpg")
        raise SystemExit(1)

    image_path = sys.argv[1]

    try:
        text = extract_text(image_path)

        print("\n========== OCR RESULT ==========\n")

        if text:
            print(text)
        else:
            print("No text detected.")

        print("\n================================")

    except Exception as exc:
        print(f"OCR failed: {exc}")