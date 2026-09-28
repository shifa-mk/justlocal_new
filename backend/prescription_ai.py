import os
import re
import json
import cv2
import torch
import pytesseract

from PIL import Image, ImageEnhance, ImageFilter
from transformers import TrOCRProcessor, VisionEncoderDecoderModel


# ============================================================
# CONFIG
# ============================================================

TESSERACT_PATH = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

TROCR_MODEL_NAME = "microsoft/trocr-base-handwritten"

pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"


# ============================================================
# LOAD MODEL
# ============================================================

print("Loading handwriting OCR model...")

processor = TrOCRProcessor.from_pretrained(
    TROCR_MODEL_NAME
)

trocr_model = VisionEncoderDecoderModel.from_pretrained(
    TROCR_MODEL_NAME
)

trocr_model.to(DEVICE)
trocr_model.eval()

print(f"TrOCR loaded successfully on: {DEVICE}")


# ============================================================
# IMAGE LOADING
# ============================================================

def load_image(image_path: str):

    image = cv2.imread(image_path)

    if image is None:
        raise FileNotFoundError(
            f"Could not read image:\n{image_path}"
        )

    return image


# ============================================================
# GENERAL IMAGE PREPROCESSING
# ============================================================

def preprocess_for_tesseract(image):

    # Upscale
    image = cv2.resize(
        image,
        None,
        fx=2,
        fy=2,
        interpolation=cv2.INTER_CUBIC
    )

    gray = cv2.cvtColor(
        image,
        cv2.COLOR_BGR2GRAY
    )

    # Improve contrast
    gray = cv2.equalizeHist(gray)

    # Reduce small noise
    gray = cv2.GaussianBlur(
        gray,
        (3, 3),
        0
    )

    # Adaptive threshold
    threshold = cv2.adaptiveThreshold(
        gray,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        31,
        11
    )

    return image, gray, threshold


# ============================================================
# TESSERACT
# ============================================================

def run_tesseract(image):

    text = pytesseract.image_to_string(
        image,
        config="--psm 6"
    )

    return clean_text(text)


# ============================================================
# TEXT CLEANING
# ============================================================

def clean_text(text):

    if not text:
        return ""

    text = text.replace("\n\n", "\n")

    text = re.sub(
        r"[ \t]+",
        " ",
        text
    )

    return text.strip()


# ============================================================
# FIND HANDWRITTEN AREA
# ============================================================

def get_prescription_area(image):

    height, width = image.shape[:2]

    # Keep lower-middle/right portion where the handwritten
    # prescription is expected in this test image.
    y1 = int(height * 0.42)
    y2 = int(height * 0.93)

    x1 = int(width * 0.28)
    x2 = int(width * 0.98)

    region = image[
        y1:y2,
        x1:x2
    ]

    return region


# ============================================================
# DETECT POSSIBLE HANDWRITTEN LINES
# ============================================================

def detect_text_lines(region):

    gray = cv2.cvtColor(
        region,
        cv2.COLOR_BGR2GRAY
    )

    # Threshold dark handwriting
    binary = cv2.threshold(
        gray,
        0,
        255,
        cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU
    )[1]

    # Connect letters belonging to the same horizontal line.
    kernel = cv2.getStructuringElement(
        cv2.MORPH_RECT,
        (35, 3)
    )

    connected = cv2.morphologyEx(
        binary,
        cv2.MORPH_CLOSE,
        kernel
    )

    # Slight dilation helps connect handwritten characters.
    kernel2 = cv2.getStructuringElement(
        cv2.MORPH_RECT,
        (5, 2)
    )

    connected = cv2.dilate(
        connected,
        kernel2,
        iterations=1
    )

    contours, _ = cv2.findContours(
        connected,
        cv2.RETR_EXTERNAL,
        cv2.CHAIN_APPROX_SIMPLE
    )

    height, width = gray.shape

    boxes = []

    for contour in contours:

        x, y, w, h = cv2.boundingRect(contour)

        # Ignore tiny noise
        if w < 40:
            continue

        if h < 8:
            continue

        # Ignore huge blocks
        if w > width * 0.98 and h > height * 0.50:
            continue

        # Text-line-like regions
        if 8 <= h <= height * 0.20:

            boxes.append(
                (x, y, w, h)
            )

    # Sort top -> bottom
    boxes.sort(
        key=lambda box: box[1]
    )

    # Merge overlapping/nearby boxes
    merged = []

    for box in boxes:

        x, y, w, h = box

        if not merged:
            merged.append(box)
            continue

        px, py, pw, ph = merged[-1]

        vertical_gap = y - (py + ph)

        overlap = min(
            y + h,
            py + ph
        ) - max(
            y,
            py
        )

        if vertical_gap < 15 and overlap > 0:

            nx = min(x, px)
            ny = min(y, py)

            right = max(
                x + w,
                px + pw
            )

            bottom = max(
                y + h,
                py + ph
            )

            merged[-1] = (
                nx,
                ny,
                right - nx,
                bottom - ny
            )

        else:
            merged.append(box)

    return merged


# ============================================================
# PREPARE A SINGLE HANDWRITTEN LINE
# ============================================================

def prepare_line_for_trocr(line):

    # Convert BGR -> RGB
    line = cv2.cvtColor(
        line,
        cv2.COLOR_BGR2RGB
    )

    pil = Image.fromarray(line)

    # Add white border
    border = 20

    canvas = Image.new(
        "RGB",
        (
            pil.width + border * 2,
            pil.height + border * 2
        ),
        "white"
    )

    canvas.paste(
        pil,
        (border, border)
    )

    # Improve contrast
    canvas = ImageEnhance.Contrast(
        canvas
    ).enhance(1.5)

    # Mild sharpening
    canvas = canvas.filter(
        ImageFilter.SHARPEN
    )

    return canvas


# ============================================================
# TROCR SINGLE LINE
# ============================================================

def trocr_line(line_image):

    pixel_values = processor(
        images=line_image,
        return_tensors="pt"
    ).pixel_values

    pixel_values = pixel_values.to(
        DEVICE
    )

    with torch.no_grad():

        generated_ids = trocr_model.generate(
            pixel_values,
            max_new_tokens=64,
            num_beams=4,
            early_stopping=True
        )

    text = processor.batch_decode(
        generated_ids,
        skip_special_tokens=True
    )[0]

    return clean_text(text)


# ============================================================
# HANDWRITING OCR
# ============================================================

def handwriting_ocr(region):

    boxes = detect_text_lines(
        region
    )

    results = []

    height, width = region.shape[:2]

    for index, (x, y, w, h) in enumerate(boxes):

        # Padding around line
        pad_x = max(
            10,
            int(w * 0.05)
        )

        pad_y = max(
            12,
            int(h * 0.50)
        )

        x1 = max(
            0,
            x - pad_x
        )

        y1 = max(
            0,
            y - pad_y
        )

        x2 = min(
            width,
            x + w + pad_x
        )

        y2 = min(
            height,
            y + h + pad_y
        )

        line = region[
            y1:y2,
            x1:x2
        ]

        if line.size == 0:
            continue

        prepared = prepare_line_for_trocr(
            line
        )

        try:

            text = trocr_line(
                prepared
            )

        except Exception as exc:

            print(
                f"TrOCR failed on line {index + 1}: {exc}"
            )

            text = ""

        if text:

            results.append({
                "line": index + 1,
                "text": text,
                "box": {
                    "x": int(x),
                    "y": int(y),
                    "width": int(w),
                    "height": int(h)
                }
            })

    return results


# ============================================================
# MEDICINE EXTRACTION
# ============================================================

def extract_medicine_candidates(text):

    candidates = []

    # Common medicine + strength pattern
    pattern = re.compile(
        r"\b("
        r"[A-Za-z][A-Za-z0-9\-]{2,40}"
        r")"
        r"\s*"
        r"(\d+(?:\.\d+)?)"
        r"\s*"
        r"(mg|mcg|g|ml|iu)"
        r"\b",
        re.IGNORECASE
    )

    for match in pattern.finditer(text):

        name = match.group(1)
        strength = match.group(2)
        unit = match.group(3)

        candidates.append({
            "name": name,
            "strength": f"{strength} {unit}",
            "source": "ocr_candidate",
            "requires_confirmation": True
        })

    # Remove duplicates
    unique = []

    seen = set()

    for medicine in candidates:

        key = (
            medicine["name"].lower(),
            medicine["strength"].lower()
        )

        if key not in seen:

            seen.add(key)
            unique.append(medicine)

    return unique


# ============================================================
# MEDICINE NORMALIZATION
# ============================================================

def normalize_medicines(candidates):

    normalized = []

    for medicine in candidates:

        name = medicine["name"].strip()

        normalized.append({
            "raw_name": name,
            "normalized_name": name.lower(),
            "strength": medicine["strength"],
            "source": medicine["source"],
            "requires_confirmation": True
        })

    return normalized


# ============================================================
# SAVE DEBUG IMAGE
# ============================================================

def save_debug_lines(
    region,
    boxes,
    output_path="ocr_debug_lines.jpg"
):

    debug = region.copy()

    for index, (x, y, w, h) in enumerate(boxes):

        cv2.rectangle(
            debug,
            (x, y),
            (x + w, y + h),
            (0, 0, 255),
            2
        )

        cv2.putText(
            debug,
            str(index + 1),
            (x, max(20, y - 5)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (255, 0, 0),
            2
        )

    cv2.imwrite(
        output_path,
        debug
    )


# ============================================================
# COMPLETE ANALYSIS
# ============================================================

def analyze_prescription(image_path):

    print("\n========================================")
    print("PRESCRIPTION ANALYSIS")
    print("========================================\n")

    # --------------------------------------------------------
    # 1. Load
    # --------------------------------------------------------

    original = load_image(
        image_path
    )

    print(
        "[1/7] Image loaded."
    )

    # --------------------------------------------------------
    # 2. Preprocess
    # --------------------------------------------------------

    resized, gray, threshold = (
        preprocess_for_tesseract(
            original
        )
    )

    print(
        "[2/7] Image preprocessing completed."
    )

    # --------------------------------------------------------
    # 3. Printed OCR
    # --------------------------------------------------------

    printed_text = run_tesseract(
        threshold
    )

    print(
        "[3/7] Printed OCR completed."
    )

    # --------------------------------------------------------
    # 4. Handwritten area
    # --------------------------------------------------------

    region = get_prescription_area(
        original
    )

    print(
        "[4/7] Prescription region extracted."
    )

    # --------------------------------------------------------
    # 5. Detect lines
    # --------------------------------------------------------

    boxes = detect_text_lines(
        region
    )

    save_debug_lines(
        region,
        boxes
    )

    print(
        f"[5/7] Detected {len(boxes)} possible handwritten lines."
    )

    # --------------------------------------------------------
    # 6. TrOCR
    # --------------------------------------------------------

    handwriting_results = handwriting_ocr(
        region
    )

    print(
        "[6/7] Handwriting OCR completed."
    )

    # --------------------------------------------------------
    # 7. Medicine extraction
    # --------------------------------------------------------

    handwritten_text = "\n".join(
        item["text"]
        for item in handwriting_results
    )

    combined_text = (
        printed_text
        + "\n"
        + handwritten_text
    )

    candidates = extract_medicine_candidates(
        combined_text
    )

    medicines = normalize_medicines(
        candidates
    )

    print(
        "[7/7] Medicine extraction completed."
    )

    return {

        "success": True,

        "ocr": {

            "printed_text":
                printed_text,

            "handwritten_lines":
                handwriting_results,

            "handwritten_text":
                handwritten_text,

            "combined_text":
                combined_text
        },

        "medicines":
            medicines,

        "requires_confirmation":
            True,

        "warning":
            (
                "OCR results are candidates only. "
                "Confirm extracted medicines before "
                "relying on them."
            )
    }


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    import sys

    if len(sys.argv) < 2:

        print(
            "Usage:"
        )

        print(
            'python prescription_ai.py '
            '"C:\\path\\to\\prescription.jpeg"'
        )

        raise SystemExit(1)

    image_path = sys.argv[1]

    if not os.path.exists(
        image_path
    ):

        print(
            f"ERROR: File does not exist:\n{image_path}"
        )

        raise SystemExit(1)

    try:

        result = analyze_prescription(
            image_path
        )

        print(
            "\n========================================"
        )

        print(
            "FINAL RESULT"
        )

        print(
            "========================================\n"
        )

        print(
            json.dumps(
                result,
                indent=2,
                ensure_ascii=False
            )
        )

        print(
            "\nDebug image saved as:"
        )

        print(
            os.path.abspath(
                "ocr_debug_lines.jpg"
            )
        )

    except Exception as exc:

        print(
            "\n========================================"
        )

        print(
            "ERROR"
        )

        print(
            "========================================"
        )

        print(
            str(exc)
        )