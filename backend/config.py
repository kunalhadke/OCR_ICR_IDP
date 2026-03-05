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
# Set POPPLER_PATH env var to override, otherwise auto-detected from WinGet install
def _find_poppler_auto() -> str:
    """Auto-detect Poppler from WinGet or legacy manual install locations."""
    # 1. WinGet install path (oschwartz10612.Poppler)
    winget_pkgs = Path.home() / "AppData" / "Local" / "Microsoft" / "WinGet" / "Packages"
    if winget_pkgs.exists():
        for pkg in sorted(winget_pkgs.glob("oschwartz*"), reverse=True):
            for bin_dir in pkg.rglob("Library/bin"):
                if (bin_dir / "pdftoppm.exe").exists():
                    return str(bin_dir)
    # 2. Legacy manual install path
    legacy = Path.home() / "poppler" / "poppler-24.08.0" / "Library" / "bin"
    if legacy.exists():
        return str(legacy)
    # 3. Let pdf2image use system PATH
    return ""

POPPLER_PATH = os.environ.get("POPPLER_PATH", _find_poppler_auto())

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
