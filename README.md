# SmartPAN Verification System v2.0

AI-powered PAN document verification MVP that accepts a **single combined PDF** containing the PAN application form and all supporting proof documents. The system auto-detects document types per page, extracts fields using PaddleOCR, runs matching logic, and classifies results.

## Project Structure

```
SmartPanVerification_System/
├── main.py                          # FastAPI app - single PDF upload pipeline
├── run.py                           # Quick-start script (reads config dynamically)
├── requirements.txt                 # Python dependencies
├── pan_verification.db              # SQLite database (auto-created)
├── backend/
│   ├── __init__.py
│   ├── config.py                    # Centralized config (all paths via env vars)
│   ├── database.py                  # SQLite schema (per-page analysis + JSON)
│   ├── ocr_engine.py                # PaddleOCR per-page text extraction
│   ├── document_classifier.py       # Document type detection per page
│   ├── field_parser.py              # Doc-type-aware regex field extraction
│   └── matcher.py                   # Matching logic & bucket classification
├── frontend/
│   ├── templates/
│   │   ├── base.html                # Base layout with navbar
│   │   ├── index.html               # Single PDF upload page
│   │   ├── dashboard.html           # Dashboard with doc type columns
│   │   └── record_detail.html       # Per-page detection + field comparison
│   └── static/
│       └── style.css
└── uploads/                         # Uploaded PDFs (auto-created)
```

## Configuration (Environment Variables)

All paths and settings are **dynamic** — resolved from `backend/config.py` using env vars with sensible defaults.

| Variable | Default | Description |
|----------|---------|-------------|
| `APP_HOST` | `127.0.0.1` | Server bind host |
| `APP_PORT` | `8000` | Server bind port |
| `UPLOAD_DIR` | `<project>/uploads` | Where uploaded PDFs are stored |
| `DB_PATH` | `<project>/pan_verification.db` | SQLite database file path |
| `TEMPLATE_DIR` | `<project>/frontend/templates` | Jinja2 template directory |
| `STATIC_DIR` | `<project>/frontend/static` | Static files directory |
| `POPPLER_PATH` | *(system PATH)* | Path to poppler binaries (for pdf2image) |
| `OCR_LANG` | `en` | PaddleOCR language |
| `OCR_DPI` | `300` | DPI for PDF-to-image conversion |

**Example overrides:**
```bash
# Linux/macOS
export POPPLER_PATH=/usr/local/bin
export APP_PORT=9000

# Windows PowerShell
$env:POPPLER_PATH="D:\tools\poppler\Library\bin"
$env:APP_PORT="9000"
```

## Prerequisites

- Python 3.9+
- Poppler (required by pdf2image for PDF-to-image conversion)

### Install Poppler

**Windows:** Download from https://github.com/oschwartz10612/poppler-windows/releases, extract anywhere, and set the `POPPLER_PATH` environment variable to the `Library\bin` folder inside it.

**macOS:** `brew install poppler`

**Ubuntu/Debian:** `sudo apt-get install poppler-utils`

## Installation

```bash
cd SmartPanVerification_System
python -m venv venv

# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

pip install -r requirements.txt
```

## Running

```bash
python run.py
# or
uvicorn main:app --reload
```

The server URL will be printed on startup (default: `http://127.0.0.1:8000`).

## Processing Pipeline

```
Single Combined PDF
    │
    ├── Page 1 → OCR → Classify → "PAN Application Form" → Extract fields
    ├── Page 2 → OCR → Classify → "Aadhaar Card"         → Extract fields
    ├── Page 3 → OCR → Classify → "Driving License"      → Extract fields
    └── ...
    │
    ├── Aggregate: PAN form pages → Application Data
    ├── Aggregate: Proof pages    → Proof Data
    │
    ├── Match: Name (exact), DOB (exact), Pincode (exact), Address (fuzzy≥70%)
    │
    └── Classify: ≥75% Auto Approved │ 40-74% Second Level │ <40% Manual
```

## Matching Rules

| Field   | Method          | Weight |
|---------|-----------------|--------|
| Name    | Exact match     | 30%    |
| DOB     | Exact match     | 25%    |
| Pincode | Exact match     | 20%    |
| Address | Fuzzy (≥70%)    | 25%    |

## Supported Document Types

| Document | Detection Method |
|----------|-----------------|
| PAN Application Form (49A/49AA) | Keywords: "form 49a", "permanent account number", etc. |
| Aadhaar Card | Keywords: "aadhaar", "uidai", 12-digit number pattern |
| Passport | Keywords: "passport", "republic of india", passport number pattern |
| Driving License | Keywords: "driving licence", "motor vehicle", DL number pattern |
| Voter ID | Keywords: "election commission", "voter id", EPIC number pattern |

## API Endpoints

| Method | Path              | Description                    |
|--------|-------------------|--------------------------------|
| GET    | `/`               | Upload page (single PDF)        |
| POST   | `/verify`         | Process uploaded combined PDF    |
| GET    | `/dashboard`      | Dashboard with all records       |
| GET    | `/record/{id}`    | Per-page detection + comparison  |
| GET    | `/api/stats`      | JSON: dashboard statistics       |
| GET    | `/api/records`    | JSON: all verification records   |

---
*Demo/MVP - Not for production use*
