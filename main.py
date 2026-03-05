"""
SmartPAN Verification System - Main FastAPI Application
========================================================
AI-based PAN document verification system that accepts a single combined PDF
containing PAN application form + supporting proof documents, detects document
type per page using PaddleOCR, extracts fields, runs matching, and classifies.
"""

import shutil
import uuid

from fastapi import FastAPI, File, UploadFile, Request, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from backend.config import UPLOAD_DIR, TEMPLATE_DIR, STATIC_DIR, PAGE_IMAGES_DIR, HOST, PORT
from backend.database import (
    init_db, insert_record, get_all_records, get_record_by_id, get_dashboard_stats,
    get_all_pan_documents, get_pan_documents_by_status, get_pan_document_by_id,
    update_pan_document_status, get_batch_stats,
)
from backend.ocr_engine import extract_text_per_page
from backend.document_classifier import classify_all_pages, DOC_PAN_FORM, DOC_UNKNOWN
from backend.field_parser import parse_document, aggregate_fields
from backend.matcher import run_matching
from backend.batch_processor import run_batch

# Initialize app
app = FastAPI(title="SmartPAN Verification System", version="2.0.0")

# Templates and static files - paths from config
templates = Jinja2Templates(directory=str(TEMPLATE_DIR))
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
app.mount("/page_images", StaticFiles(directory=str(PAGE_IMAGES_DIR)), name="page_images")


@app.on_event("startup")
def startup():
    """Initialize database on startup."""
    init_db()
    print("=" * 55)
    print("  SmartPAN Verification System v2.0 Started")
    print("  Single Combined PDF Upload Mode")
    print(f"  Open http://{HOST}:{PORT} in your browser")
    print("=" * 55)

# ─────────────────────────── Pages ───────────────────────────

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Landing page with single upload form."""
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Dashboard showing all verification records."""
    records = get_all_records()
    stats = get_dashboard_stats()
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "records": records,
        "stats": stats,
    })


@app.get("/record/{record_id}", response_class=HTMLResponse)
async def record_detail(request: Request, record_id: int):
    """Detailed view of a single verification record."""
    record = get_record_by_id(record_id)
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")
    return templates.TemplateResponse("record_detail.html", {
        "request": request,
        "record": record,
    })


# ─────────────────────────── API ───────────────────────────

@app.post("/verify")
async def verify_documents(
    request: Request,
    combined_pdf: UploadFile = File(..., description="Combined PDF (PAN form + proof docs)"),
):
    """
    Main verification endpoint for single combined PDF:
    1. Save uploaded PDF
    2. Convert each page to image & OCR via PaddleOCR
    3. Classify each page's document type
    4. Parse structured fields per page
    5. Aggregate into form data vs proof data
    6. Run matching logic
    7. Classify into verification bucket
    8. Store in database with per-page analysis
    """
    print(f"\n{'#'*60}")
    print(f"[VERIFY] New verification request: {combined_pdf.filename}")
    print(f"{'#'*60}")

    # Validate file type
    if not combined_pdf.filename.lower().endswith(".pdf"):
        print(f"[VERIFY] ERROR - Invalid file type: {combined_pdf.filename}")
        raise HTTPException(status_code=400, detail=f"Only PDF files accepted. Got: {combined_pdf.filename}")

    # Save uploaded file to dynamic upload dir
    file_id = str(uuid.uuid4())[:8]
    pdf_path = UPLOAD_DIR / f"{file_id}_{combined_pdf.filename}"

    try:
        with open(pdf_path, "wb") as f:
            shutil.copyfileobj(combined_pdf.file, f)
        print(f"[VERIFY] File saved: {pdf_path}")
    except Exception as e:
        print(f"[VERIFY] ERROR - File save failed: {e}")
        raise HTTPException(status_code=500, detail=f"File upload failed: {str(e)}")

    # ── Step 1: OCR - Extract text per page ──
    print(f"\n[VERIFY] Step 1: OCR text extraction")
    try:
        pages_text = extract_text_per_page(str(pdf_path))
    except Exception as e:
        print(f"[VERIFY] ERROR - OCR failed: {e}")
        raise HTTPException(status_code=500, detail=f"OCR extraction failed: {str(e)}")

    if not pages_text:
        print(f"[VERIFY] ERROR - No pages/text extracted")
        raise HTTPException(status_code=400, detail="PDF has no pages or OCR could not extract text.")

    print(f"[VERIFY] OCR extracted text from {len(pages_text)} page(s)")

    # ── Step 1b: Save page images for preview ──
    print(f"[VERIFY] Saving page images for preview")
    for page in pages_text:
        img = page.pop("image", None)
        if img:
            img_filename = f"{file_id}_page{page['page_num']}.png"
            img_path = PAGE_IMAGES_DIR / img_filename
            img.save(str(img_path), "PNG")
            page["image_url"] = f"/page_images/{img_filename}"
            print(f"[VERIFY] Saved page {page['page_num']} image: {img_filename}")
        else:
            page["image_url"] = ""

    # ── Step 2: Classify each page's document type ──
    print(f"\n[VERIFY] Step 2: Document classification")
    classified_pages = classify_all_pages(pages_text)

    # ── Step 3: Separate pages into form vs proof ──
    print(f"\n[VERIFY] Step 3: Separating form vs proof pages")
    form_pages = []
    proof_pages = []

    for page in classified_pages:
        if page["doc_type"] == DOC_PAN_FORM:
            form_pages.append(page)
        elif page["doc_type"] != DOC_UNKNOWN:
            proof_pages.append(page)
        else:
            # Unknown pages: try to use as proof if we already have a form
            proof_pages.append(page)

    # If no PAN form detected, treat first page as form, rest as proof
    if not form_pages and len(classified_pages) > 0:
        print(f"[VERIFY] No PAN form detected, using page 1 as form")
        form_pages = [classified_pages[0]]
        proof_pages = classified_pages[1:] if len(classified_pages) > 1 else []

    print(f"[VERIFY] Form pages: {len(form_pages)}, Proof pages: {len(proof_pages)}")

    # ── Step 4: Parse fields from each page (document-type-aware) ──
    print(f"\n[VERIFY] Step 4: Parsing fields from pages")
    form_parsed = []
    for page in form_pages:
        print(f"[VERIFY] Parsing FORM page {page['page_num']} ({page['doc_type']})")
        fields = parse_document(page["text"], page["doc_type"])
        form_parsed.append(fields)

    proof_parsed = []
    for page in proof_pages:
        print(f"[VERIFY] Parsing PROOF page {page['page_num']} ({page['doc_type']})")
        fields = parse_document(page["text"], page["doc_type"])
        proof_parsed.append(fields)

    # ── Step 5: Aggregate fields ──
    print(f"\n[VERIFY] Step 5: Aggregating fields")
    form_fields = aggregate_fields(form_parsed) if form_parsed else {
        "name": "", "dob": "", "address": "", "pincode": "", "state": ""
    }
    proof_fields = aggregate_fields(proof_parsed) if proof_parsed else {
        "name": "", "dob": "", "address": "", "pincode": "", "state": ""
    }

    # ── Step 6: Run matching ──
    print(f"\n[VERIFY] Step 6: Running matching engine")
    match_results = run_matching(form_fields, proof_fields)

    # ── Step 7: Build per-page analysis for storage ──
    page_analysis = []
    for page in classified_pages:
        page_analysis.append({
            "page_num": page["page_num"],
            "doc_type": page["doc_type"],
            "confidence": page["confidence"],
            "text_snippet": page["text"],
            "image_url": page.get("image_url", ""),
        })

    # Collect detected document types
    detected_types = list(dict.fromkeys(p["doc_type"] for p in classified_pages))
    proof_doc_types = list(dict.fromkeys(
        p["doc_type"] for p in proof_pages if p["doc_type"] != DOC_UNKNOWN
    ))

    # Combine raw text
    form_raw = "\n\n".join(p["text"] for p in form_pages)
    proof_raw = "\n\n".join(p["text"] for p in proof_pages)

    # ── Step 8: Store in database ──
    record_data = {
        "applicant_name": form_fields["name"] or proof_fields["name"],
        "pan_number": "",
        "filename": combined_pdf.filename,
        "total_pages": len(classified_pages),
        "detected_doc_types": ", ".join(detected_types),
        "page_analysis": page_analysis,
        "form_name": form_fields["name"],
        "form_dob": form_fields["dob"],
        "form_address": form_fields["address"],
        "form_pincode": form_fields["pincode"],
        "form_state": form_fields["state"],
        "form_raw_text": form_raw[:5000],
        "proof_name": proof_fields["name"],
        "proof_dob": proof_fields["dob"],
        "proof_address": proof_fields["address"],
        "proof_pincode": proof_fields["pincode"],
        "proof_state": proof_fields["state"],
        "proof_raw_text": proof_raw[:5000],
        "proof_doc_types": ", ".join(proof_doc_types) if proof_doc_types else "None detected",
        **match_results,
    }

    print(f"\n[VERIFY] Step 8: Saving to database")
    record_id = insert_record(record_data)

    print(f"\n{'#'*60}")
    print(f"[VERIFY] DONE! Record #{record_id} saved")
    print(f"[VERIFY] Result: {match_results['verification_bucket']} (score={match_results['overall_score']}%)")
    print(f"{'#'*60}\n")

    return RedirectResponse(url=f"/record/{record_id}", status_code=303)


# ─────────────────────── Batch Page Routes ────────────────────────

@app.get("/batch/dashboard", response_class=HTMLResponse)
async def batch_dashboard(request: Request):
    """Batch processing overview with DB stats and document table."""
    documents = get_all_pan_documents()
    stats = get_batch_stats()
    return templates.TemplateResponse("batch_dashboard.html", {
        "request": request,
        "documents": documents,
        "stats": stats,
    })


@app.get("/batch/review", response_class=HTMLResponse)
async def batch_review(request: Request):
    """Manual review queue - documents with status=Manual."""
    documents = get_pan_documents_by_status("Manual")
    return templates.TemplateResponse("batch_review.html", {
        "request": request,
        "documents": documents,
    })


@app.get("/batch/document/{doc_id}", response_class=HTMLResponse)
async def batch_document_detail(request: Request, doc_id: int):
    """Detail view of a batch-processed document."""
    doc = get_pan_document_by_id(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return templates.TemplateResponse("batch_document_detail.html", {
        "request": request,
        "doc": doc,
    })


@app.post("/batch/approve/{doc_id}")
async def batch_approve(request: Request, doc_id: int):
    """Approve a manual review document -> update status in DB."""
    doc = get_pan_document_by_id(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    if doc["document_status"] != "Manual":
        raise HTTPException(status_code=400, detail="Only Manual-status documents can be approved")

    update_pan_document_status(doc_id, "Approved", reviewed_by="operator")
    return RedirectResponse(url="/batch/review", status_code=303)


@app.post("/batch/reject/{doc_id}")
async def batch_reject(request: Request, doc_id: int):
    """Reject a manual review document -> update status in DB."""
    doc = get_pan_document_by_id(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    if doc["document_status"] != "Manual":
        raise HTTPException(status_code=400, detail="Only Manual-status documents can be rejected")

    update_pan_document_status(doc_id, "Rejected", reviewed_by="operator")
    return RedirectResponse(url="/batch/review", status_code=303)


# ─────────────────────── Batch API Routes ─────────────────────────

@app.get("/api/batch/stats")
async def api_batch_stats():
    """JSON stats for batch processing."""
    return get_batch_stats()


@app.get("/api/batch/documents")
async def api_batch_documents(status: str = None):
    """JSON document list, optionally filterable by status."""
    if status:
        return get_pan_documents_by_status(status)
    return get_all_pan_documents()


@app.post("/api/batch/trigger")
async def api_batch_trigger(max_docs: int = 0):
    """Trigger a batch processing run from the web UI."""
    result = run_batch(max_docs=max_docs)
    return {"message": "Batch processing complete", **result}


# ─────────────────── Original API Routes ──────────────────────

@app.get("/api/stats")
async def api_stats():
    """API endpoint for dashboard statistics."""
    return get_dashboard_stats()


@app.get("/api/records")
async def api_records():
    """API endpoint returning all records as JSON."""
    return get_all_records()
