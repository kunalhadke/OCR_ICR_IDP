"""
Batch Processor - Core engine for automated PAN document processing.
Picks up PDFs from PAN_documents/, runs the full verification pipeline,
classifies by score, and stores results in SQLite DB (no file movement).

Usage:
    python -m backend.batch_processor --mode once        # Process all pending, then exit
    python -m backend.batch_processor --mode continuous   # Poll folder every N seconds
"""

import time
import uuid
import argparse
from pathlib import Path

from backend.config import PAN_DOCUMENTS_DIR, PAGE_IMAGES_DIR, BATCH_POLL_INTERVAL
from backend.database import init_db, insert_pan_document
from backend.ocr_engine import extract_text_per_page
from backend.document_classifier import classify_all_pages, DOC_PAN_FORM, DOC_UNKNOWN
from backend.field_parser import parse_document, aggregate_fields
from backend.matcher import run_matching


def _classify_document_status(overall_score: float) -> str:
    """Map overall match score to batch document status (DB-only, no folders)."""
    if overall_score >= 75:
        return "Approved"
    elif overall_score >= 40:
        return "Manual"
    else:
        return "Rejected"


def process_single_document(pdf_path: Path, batch_id: str) -> dict:
    """
    Run the full verification pipeline on a single PDF:
    OCR -> classify -> parse -> match -> score -> insert DB.
    File stays in PAN_documents/. Status tracked in SQLite only.
    """
    original_filename = pdf_path.name
    file_id = str(uuid.uuid4())[:8]
    print(f"\n[BATCH] Processing: {original_filename} (batch={batch_id})")

    try:
        # Step 1: OCR
        pages_text = extract_text_per_page(str(pdf_path))
        if not pages_text:
            raise ValueError("No pages or text extracted from PDF")

        # Step 1b: Save page images for preview
        for page in pages_text:
            img = page.pop("image", None)
            if img:
                img_filename = f"batch_{file_id}_page{page['page_num']}.png"
                img_path = PAGE_IMAGES_DIR / img_filename
                img.save(str(img_path), "PNG")
                page["image_url"] = f"/page_images/{img_filename}"
            else:
                page["image_url"] = ""

        # Step 2: Classify pages
        classified_pages = classify_all_pages(pages_text)

        # Step 3: Separate form vs proof
        form_pages = []
        proof_pages = []
        for page in classified_pages:
            if page["doc_type"] == DOC_PAN_FORM:
                form_pages.append(page)
            elif page["doc_type"] != DOC_UNKNOWN:
                proof_pages.append(page)
            else:
                proof_pages.append(page)

        if not form_pages and classified_pages:
            form_pages = [classified_pages[0]]
            proof_pages = classified_pages[1:] if len(classified_pages) > 1 else []

        # Step 4: Parse fields
        form_parsed = [parse_document(p["text"], p["doc_type"]) for p in form_pages]
        proof_parsed = [parse_document(p["text"], p["doc_type"]) for p in proof_pages]

        # Step 5: Aggregate
        empty_fields = {"name": "", "dob": "", "address": "", "pincode": "", "state": ""}
        form_fields = aggregate_fields(form_parsed) if form_parsed else empty_fields
        proof_fields = aggregate_fields(proof_parsed) if proof_parsed else empty_fields

        # Step 6: Match
        match_results = run_matching(form_fields, proof_fields)

        # Step 7: Classify status (DB-only, no file movement)
        doc_status = _classify_document_status(match_results["overall_score"])

        # Build page analysis
        page_analysis = []
        for page in classified_pages:
            page_analysis.append({
                "page_num": page["page_num"],
                "doc_type": page["doc_type"],
                "confidence": page["confidence"],
                "text_snippet": page["text"],
                "image_url": page.get("image_url", ""),
            })

        detected_types = list(dict.fromkeys(p["doc_type"] for p in classified_pages))
        proof_doc_types = list(dict.fromkeys(
            p["doc_type"] for p in proof_pages if p["doc_type"] != DOC_UNKNOWN
        ))

        form_raw = "\n\n".join(p["text"] for p in form_pages)
        proof_raw = "\n\n".join(p["text"] for p in proof_pages)

        # Step 8: Insert into DB
        record_data = {
            "applicant_name": form_fields["name"] or proof_fields["name"],
            "pan_number": "",
            "filename": original_filename,
            "original_filename": original_filename,
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
            "document_status": doc_status,
            "file_path": str(pdf_path),
            "folder_location": "",
            "batch_id": batch_id,
            "processing_error": "",
            **match_results,
        }

        doc_id = insert_pan_document(record_data)
        print(f"[BATCH] {original_filename} -> {doc_status} (score={match_results['overall_score']}%, id={doc_id})")

        return {"id": doc_id, "status": doc_status, "score": match_results["overall_score"], "error": None}

    except Exception as e:
        print(f"[BATCH] ERROR processing {original_filename}: {e}")
        error_data = {
            "original_filename": original_filename,
            "filename": original_filename,
            "document_status": "Error",
            "file_path": str(pdf_path),
            "folder_location": "",
            "batch_id": batch_id,
            "processing_error": str(e),
        }
        doc_id = insert_pan_document(error_data)
        return {"id": doc_id, "status": "Error", "score": 0, "error": str(e)}


def run_batch(max_docs: int = 0) -> dict:
    """
    Process all pending PDFs in PAN_documents/ folder.
    If max_docs > 0, limit to that many documents.
    Returns summary stats.
    """
    pdf_files = sorted(PAN_DOCUMENTS_DIR.glob("*.pdf"))
    if max_docs > 0:
        pdf_files = pdf_files[:max_docs]

    if not pdf_files:
        print("[BATCH] No PDF files found in PAN_documents/")
        return {"processed": 0, "approved": 0, "manual": 0, "rejected": 0, "errors": 0}

    batch_id = str(uuid.uuid4())[:8]
    print(f"\n{'='*60}")
    print(f"[BATCH] Starting batch {batch_id}: {len(pdf_files)} document(s)")
    print(f"{'='*60}")

    stats = {"processed": 0, "approved": 0, "manual": 0, "rejected": 0, "errors": 0}

    for pdf_path in pdf_files:
        result = process_single_document(pdf_path, batch_id)
        stats["processed"] += 1
        status_key = result["status"].lower()
        if status_key in stats:
            stats[status_key] += 1
        else:
            stats["errors"] += 1

    print(f"\n{'='*60}")
    print(f"[BATCH] Batch {batch_id} complete: {stats}")
    print(f"{'='*60}\n")
    return stats


def run_continuous(poll_interval: int = None):
    """Daemon mode: poll PAN_documents/ folder every N seconds."""
    interval = poll_interval or BATCH_POLL_INTERVAL
    print(f"[BATCH] Continuous mode started (polling every {interval}s)")
    print(f"[BATCH] Watching: {PAN_DOCUMENTS_DIR}")
    print(f"[BATCH] Press Ctrl+C to stop\n")

    try:
        while True:
            pdf_files = list(PAN_DOCUMENTS_DIR.glob("*.pdf"))
            if pdf_files:
                run_batch()
            time.sleep(interval)
    except KeyboardInterrupt:
        print("\n[BATCH] Continuous mode stopped by user")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SmartPAN Batch Processor")
    parser.add_argument("--mode", choices=["once", "continuous"], default="once",
                        help="'once' processes all pending then exits; 'continuous' polls the folder")
    parser.add_argument("--max-docs", type=int, default=0,
                        help="Max documents to process per batch (0 = unlimited)")
    args = parser.parse_args()

    init_db()

    if args.mode == "once":
        run_batch(max_docs=args.max_docs)
    else:
        run_continuous()
