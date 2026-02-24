"""
OCR Engine using PaddleOCR for text extraction from PDF documents.
Converts PDF pages to images, then runs OCR on each page individually.
Returns per-page results for document classification.
"""

import os
import tempfile
from pdf2image import convert_from_path
from paddleocr import PaddleOCR
from backend.config import get_poppler_path, OCR_LANG, OCR_DPI

# Initialize PaddleOCR once
ocr = PaddleOCR(use_angle_cls=True, lang=OCR_LANG, show_log=False)


def pdf_to_images(pdf_path: str) -> list:
    """Convert PDF pages to PIL images using dynamically resolved poppler."""
    print(f"[OCR] Converting PDF to images: {pdf_path}")
    try:
        poppler = get_poppler_path()
        print(f"[OCR] Poppler path: {poppler}")
        images = convert_from_path(pdf_path, dpi=OCR_DPI, poppler_path=poppler)
        print(f"[OCR] Converted {len(images)} page(s) to images (DPI={OCR_DPI})")
        return images
    except Exception as e:
        print(f"[OCR] ERROR - PDF to image conversion failed: {e}")
        raise RuntimeError(f"PDF to image conversion failed: {str(e)}")


def extract_text_from_image(image) -> str:
    """Run PaddleOCR on a single PIL image and return extracted text."""
    print(f"[OCR] Running PaddleOCR on image (size={image.size})")
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        image.save(tmp.name, "PNG")
        tmp_path = tmp.name

    try:
        result = ocr.ocr(tmp_path, cls=True)
        lines = []
        if result and result[0]:
            for line in result[0]:
                text = line[1][0]
                lines.append(text)
        extracted = "\n".join(lines)
        print(f"[OCR] Extracted {len(lines)} line(s), {len(extracted)} char(s)")
        return extracted
    finally:
        os.unlink(tmp_path)


def extract_text_per_page(pdf_path: str) -> list[dict]:
    """
    Full pipeline: PDF -> Images -> OCR per page.
    Returns list of {"page_num": int, "text": str, "image": PIL.Image} for each page.
    """
    print(f"\n{'='*50}")
    print(f"[OCR] Starting full OCR pipeline for: {pdf_path}")
    print(f"{'='*50}")
    images = pdf_to_images(pdf_path)
    pages = []
    for idx, img in enumerate(images, start=1):
        print(f"\n[OCR] --- Processing Page {idx}/{len(images)} ---")
        page_text = extract_text_from_image(img)
        pages.append({"page_num": idx, "text": page_text, "image": img})
    print(f"\n[OCR] OCR complete: {len(pages)} page(s) processed")
    return pages
