"""
Batch Auto-Processor: python run_batch.py

Automatically picks up all PDFs from PAN_documents/ folder,
processes them one-by-one through the verification pipeline,
and stores results in SQLite DB with status based on score threshold:
  >= 75%  → Approved
  40-75%  → Manual (needs human review)
  < 40%   → Rejected

After all files are processed, the script exits.
Results are visible at http://127.0.0.1:8000/batch/dashboard (run run.py for web UI).
"""

import sys
from pathlib import Path

from backend.config import PAN_DOCUMENTS_DIR
from backend.database import init_db
from backend.batch_processor import process_single_document

import uuid


def main():
    # Initialize database (creates pan_documents table if not exists)
    init_db()

    # Find all PDFs in PAN_documents/ folder
    pdf_files = sorted(PAN_DOCUMENTS_DIR.glob("*.pdf"))

    if not pdf_files:
        print(f"\n[BATCH] No PDF files found in: {PAN_DOCUMENTS_DIR}")
        print(f"[BATCH] Place your PAN document PDFs in that folder and run again.")
        sys.exit(0)

    batch_id = str(uuid.uuid4())[:8]
    total = len(pdf_files)

    print(f"\n{'='*60}")
    print(f"  SmartPAN Batch Auto-Processor")
    print(f"  Found {total} PDF(s) in PAN_documents/")
    print(f"  Batch ID: {batch_id}")
    print(f"{'='*60}\n")

    # Track results
    results = {"approved": 0, "manual": 0, "rejected": 0, "errors": 0}

    for i, pdf_path in enumerate(pdf_files, 1):
        print(f"\n--- [{i}/{total}] {pdf_path.name} ---")
        result = process_single_document(pdf_path, batch_id)

        status = result["status"]
        score = result["score"]

        if status == "Approved":
            results["approved"] += 1
            print(f"    ✓ APPROVED (score={score}%) → Saved to DB")
        elif status == "Manual":
            results["manual"] += 1
            print(f"    ⚠ MANUAL REVIEW (score={score}%) → Saved to DB")
        elif status == "Rejected":
            results["rejected"] += 1
            print(f"    ✗ REJECTED (score={score}%) → Saved to DB")
        else:
            results["errors"] += 1
            print(f"    ✗ ERROR: {result['error']}")

    # Summary
    print(f"\n{'='*60}")
    print(f"  BATCH COMPLETE")
    print(f"  Total: {total} | Approved: {results['approved']} | Manual: {results['manual']} | Rejected: {results['rejected']} | Errors: {results['errors']}")
    print(f"{'='*60}")
    print(f"\n  → Run 'python run.py' and open http://127.0.0.1:8000/batch/dashboard to see results")
    print(f"  → Manual review documents visible at http://127.0.0.1:8000/batch/review\n")


if __name__ == "__main__":
    main()
