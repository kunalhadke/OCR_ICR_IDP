"""
Centralized Configuration - All paths and settings resolved dynamically.
Override any setting via environment variables.
"""

import os
from pathlib import Path

# ── Project Root (auto-detected from this file's location) ──
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# ── Server Settings ──
HOST = os.environ.get("APP_HOST", "127.0.0.1")
PORT = int(os.environ.get("APP_PORT", "8000"))

# ── Directory Paths (all relative to project root, overridable) ──
UPLOAD_DIR = Path(os.environ.get("UPLOAD_DIR", str(PROJECT_ROOT / "uploads")))
TEMPLATE_DIR = Path(os.environ.get("TEMPLATE_DIR", str(PROJECT_ROOT / "frontend" / "templates")))
STATIC_DIR = Path(os.environ.get("STATIC_DIR", str(PROJECT_ROOT / "frontend" / "static")))

# ── Database ──
DB_PATH = Path(os.environ.get("DB_PATH", str(PROJECT_ROOT / "pan_verification.db")))

# ── Poppler (for pdf2image: auto-detect or override via env) ──
# Set POPPLER_PATH env var if poppler is not in system PATH
# e.g., POPPLER_PATH=C:\poppler\Library\bin  or  /usr/local/bin
_DEFAULT_POPPLER = str(Path.home() / "poppler" / "poppler-24.08.0" / "Library" / "bin")
POPPLER_PATH = os.environ.get("POPPLER_PATH", _DEFAULT_POPPLER)

# ── OCR Settings ──
OCR_LANG = os.environ.get("OCR_LANG", "en")
OCR_DPI = int(os.environ.get("OCR_DPI", "300"))

# ── Page Images (saved during OCR for preview) ──
PAGE_IMAGES_DIR = Path(os.environ.get("PAGE_IMAGES_DIR", str(PROJECT_ROOT / "page_images")))

# ── Batch Processing ──
PAN_DOCUMENTS_DIR = Path(os.environ.get("PAN_DOCUMENTS_DIR", str(PROJECT_ROOT / "PAN_documents")))
BATCH_POLL_INTERVAL = int(os.environ.get("BATCH_POLL_INTERVAL", "10"))  # seconds

# ── Ensure directories exist ──
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
PAGE_IMAGES_DIR.mkdir(parents=True, exist_ok=True)
PAN_DOCUMENTS_DIR.mkdir(parents=True, exist_ok=True)


def get_poppler_path():
    """Return poppler path for pdf2image, or None to use system PATH."""
    if POPPLER_PATH and Path(POPPLER_PATH).exists():
        return str(POPPLER_PATH)
    return None
