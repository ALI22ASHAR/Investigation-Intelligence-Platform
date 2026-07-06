"""
ingestion/pdf_ocr_extractor.py

Purpose: given a PDF file (dropped in manually, downloaded, whatever),
extract its text -- trying the fast/clean method first (real embedded
text), and automatically falling back to OCR (reading it like an image)
if that produces little or nothing, which happens with scanned documents.
"""

from pathlib import Path

import pdfplumber
import pytesseract
from pdf2image import convert_from_path

# Point pytesseract directly at the Tesseract executable, since it's
# not on Windows' PATH by default. This is a one-time config, not
# something that changes per-file.
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# pdf2image needs to know where Poppler's executables live, for the
# same reason -- it's not on PATH either.
POPPLER_PATH = r"C:\poppler\poppler-26.02.0\Library\bin"


def extract_text_direct(pdf_path: Path) -> str:
    """
    Attempts to pull real, embedded text straight out of the PDF --
    fast (no image processing needed) and perfectly accurate, but only
    works if the PDF actually HAS embedded text (i.e. wasn't just a
    scanned image saved as a PDF).
    """
    text_parts = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()  # returns None if a page has no extractable text
            if page_text:
                text_parts.append(page_text)
    return "\n\n".join(text_parts)


def extract_text_via_ocr(pdf_path: Path) -> str:
    """
    Fallback path: converts each PDF page into an image, then runs
    Tesseract OCR on each image to "read" the text visually.

    This is much slower than direct extraction (real image processing
    per page) and less accurate (OCR can misread characters, especially
    on poor-quality scans) -- which is exactly why we only use it when
    direct extraction fails.
    """
    print(f"  Falling back to OCR for {pdf_path.name} (this is slower)...")
    images = convert_from_path(pdf_path, poppler_path=POPPLER_PATH)

    text_parts = []
    for page_num, image in enumerate(images, start=1):
        page_text = pytesseract.image_to_string(image)
        text_parts.append(page_text)
        print(f"    OCR'd page {page_num}/{len(images)}")

    return "\n\n".join(text_parts)


def extract_pdf_text(pdf_path: Path, min_direct_chars: int = 50) -> dict:
    """
    The main entry point: tries direct extraction first, and only falls
    back to OCR if direct extraction came back nearly empty (a strong
    signal the PDF is scanned images, not real text).

    min_direct_chars: threshold below which we consider direct
    extraction to have "failed". A real text page should produce far
    more than 50 characters; a scanned page with no embedded text
    typically produces 0.
    """
    direct_text = extract_text_direct(pdf_path)

    if len(direct_text.strip()) >= min_direct_chars:
        return {"text": direct_text, "method": "direct"}

    ocr_text = extract_text_via_ocr(pdf_path)
    return {"text": ocr_text, "method": "ocr"}


if __name__ == "__main__":
    # Point this at any real PDF you have locally to test both paths.
    # Try one normal PDF and, if you can find one, a scanned document
    # PDF too -- you should see the printout confirm which method it
    # actually used.
    test_pdf = Path("data/raw/pdfs/sample.pdf")  # adjust to a real file you have

    if not test_pdf.exists():
        print(f"No test file at {test_pdf} -- put a PDF there to test, or edit this path.")
    else:
        result = extract_pdf_text(test_pdf)
        print(f"\nExtraction method used: {result['method']}")
        print(f"Extracted {len(result['text'])} characters.")
        print("--- First 500 characters ---")
        print(result["text"][:500])
