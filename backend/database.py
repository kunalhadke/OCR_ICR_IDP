"""
SQLite Database setup and schema for PAN Verification System.
Single combined PDF workflow with per-page document classification.
"""

import sqlite3
import json
from datetime import datetime
from backend.config import DB_PATH


def get_connection():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    print("[DATABASE] Initializing database...")
    conn = get_connection()
    cursor = conn.cursor()

    # Drop old table if schema changed (demo use only - not for production)
    cursor.execute("DROP TABLE IF EXISTS verification_records")

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS verification_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            applicant_name TEXT,
            pan_number TEXT,

            -- Single file reference
            filename TEXT,
            total_pages INTEGER DEFAULT 0,

            -- Detected document types (comma-separated summary)
            detected_doc_types TEXT,

            -- Per-page analysis stored as JSON
            -- [{page_num, doc_type, confidence, text_snippet}, ...]
            page_analysis TEXT,

            -- Extracted from PAN application form pages
            form_name TEXT,
            form_dob TEXT,
            form_address TEXT,
            form_pincode TEXT,
            form_state TEXT,
            form_raw_text TEXT,

            -- Extracted (aggregated) from proof document pages
            proof_name TEXT,
            proof_dob TEXT,
            proof_address TEXT,
            proof_pincode TEXT,
            proof_state TEXT,
            proof_raw_text TEXT,
            proof_doc_types TEXT,

            -- Match results
            name_match INTEGER DEFAULT 0,
            dob_match INTEGER DEFAULT 0,
            address_score REAL DEFAULT 0.0,
            pincode_match INTEGER DEFAULT 0,
            overall_score REAL DEFAULT 0.0,
            verification_bucket TEXT DEFAULT 'Manual Review',

            -- SLA tracking
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            processed_at TIMESTAMP,
            status TEXT DEFAULT 'Pending'
        )
    """)

    # Batch processing table (never dropped - persistent data)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS pan_documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            applicant_name TEXT,
            pan_number TEXT,
            filename TEXT,
            original_filename TEXT,
            total_pages INTEGER DEFAULT 0,
            detected_doc_types TEXT,
            page_analysis TEXT,

            form_name TEXT,
            form_dob TEXT,
            form_address TEXT,
            form_pincode TEXT,
            form_state TEXT,
            form_raw_text TEXT,

            proof_name TEXT,
            proof_dob TEXT,
            proof_address TEXT,
            proof_pincode TEXT,
            proof_state TEXT,
            proof_raw_text TEXT,
            proof_doc_types TEXT,

            name_match INTEGER DEFAULT 0,
            dob_match INTEGER DEFAULT 0,
            address_score REAL DEFAULT 0.0,
            pincode_match INTEGER DEFAULT 0,
            overall_score REAL DEFAULT 0.0,
            verification_bucket TEXT DEFAULT 'Manual Review',

            document_status TEXT DEFAULT 'Pending',
            file_path TEXT,
            folder_location TEXT,
            batch_id TEXT,
            processing_error TEXT,
            reviewed_by TEXT,
            reviewed_at TIMESTAMP,

            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            processed_at TIMESTAMP,
            status TEXT DEFAULT 'Pending'
        )
    """)

    conn.commit()
    conn.close()
    print(f"[DATABASE] Database initialized at {DB_PATH}")


def insert_record(data: dict) -> int:
    conn = get_connection()
    cursor = conn.cursor()

    # Serialize page_analysis list to JSON
    page_analysis_json = json.dumps(data.get("page_analysis", []))

    cursor.execute("""
        INSERT INTO verification_records (
            applicant_name, pan_number,
            filename, total_pages, detected_doc_types, page_analysis,
            form_name, form_dob, form_address, form_pincode, form_state, form_raw_text,
            proof_name, proof_dob, proof_address, proof_pincode, proof_state,
            proof_raw_text, proof_doc_types,
            name_match, dob_match, address_score, pincode_match,
            overall_score, verification_bucket,
            processed_at, status
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        data.get("applicant_name", ""),
        data.get("pan_number", ""),
        data.get("filename", ""),
        data.get("total_pages", 0),
        data.get("detected_doc_types", ""),
        page_analysis_json,
        data.get("form_name", ""),
        data.get("form_dob", ""),
        data.get("form_address", ""),
        data.get("form_pincode", ""),
        data.get("form_state", ""),
        data.get("form_raw_text", ""),
        data.get("proof_name", ""),
        data.get("proof_dob", ""),
        data.get("proof_address", ""),
        data.get("proof_pincode", ""),
        data.get("proof_state", ""),
        data.get("proof_raw_text", ""),
        data.get("proof_doc_types", ""),
        data.get("name_match", 0),
        data.get("dob_match", 0),
        data.get("address_score", 0.0),
        data.get("pincode_match", 0),
        data.get("overall_score", 0.0),
        data.get("verification_bucket", "Manual Review"),
        datetime.now().isoformat(),
        "Processed"
    ))

    record_id = cursor.lastrowid
    conn.commit()
    conn.close()
    print(f"[DATABASE] Record #{record_id} inserted successfully")
    return record_id


def get_all_records():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM verification_records ORDER BY created_at DESC")
    rows = cursor.fetchall()
    conn.close()
    records = []
    for row in rows:
        r = dict(row)
        try:
            r["page_analysis"] = json.loads(r.get("page_analysis", "[]"))
        except (json.JSONDecodeError, TypeError):
            r["page_analysis"] = []
        records.append(r)
    return records


def get_record_by_id(record_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM verification_records WHERE id = ?", (record_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        r = dict(row)
        try:
            r["page_analysis"] = json.loads(r.get("page_analysis", "[]"))
        except (json.JSONDecodeError, TypeError):
            r["page_analysis"] = []
        return r
    return None


def get_dashboard_stats():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) as total FROM verification_records")
    total = cursor.fetchone()["total"]

    cursor.execute("SELECT COUNT(*) as cnt FROM verification_records WHERE verification_bucket = 'Auto Approved'")
    auto_approved = cursor.fetchone()["cnt"]

    cursor.execute("SELECT COUNT(*) as cnt FROM verification_records WHERE verification_bucket = 'Second Level Review'")
    second_level = cursor.fetchone()["cnt"]

    cursor.execute("SELECT COUNT(*) as cnt FROM verification_records WHERE verification_bucket = 'Manual Review'")
    manual_review = cursor.fetchone()["cnt"]

    cursor.execute("SELECT AVG(overall_score) as avg_score FROM verification_records")
    avg_score = cursor.fetchone()["avg_score"] or 0

    conn.close()
    return {
        "total": total,
        "auto_approved": auto_approved,
        "second_level": second_level,
        "manual_review": manual_review,
        "avg_score": round(avg_score, 2)
    }


# ─────────────── Batch pan_documents functions ───────────────

def insert_pan_document(data: dict) -> int:
    conn = get_connection()
    cursor = conn.cursor()
    page_analysis_json = json.dumps(data.get("page_analysis", []))

    cursor.execute("""
        INSERT INTO pan_documents (
            applicant_name, pan_number,
            filename, original_filename, total_pages, detected_doc_types, page_analysis,
            form_name, form_dob, form_address, form_pincode, form_state, form_raw_text,
            proof_name, proof_dob, proof_address, proof_pincode, proof_state,
            proof_raw_text, proof_doc_types,
            name_match, dob_match, address_score, pincode_match,
            overall_score, verification_bucket,
            document_status, file_path, folder_location, batch_id, processing_error,
            processed_at, status
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        data.get("applicant_name", ""),
        data.get("pan_number", ""),
        data.get("filename", ""),
        data.get("original_filename", ""),
        data.get("total_pages", 0),
        data.get("detected_doc_types", ""),
        page_analysis_json,
        data.get("form_name", ""),
        data.get("form_dob", ""),
        data.get("form_address", ""),
        data.get("form_pincode", ""),
        data.get("form_state", ""),
        data.get("form_raw_text", ""),
        data.get("proof_name", ""),
        data.get("proof_dob", ""),
        data.get("proof_address", ""),
        data.get("proof_pincode", ""),
        data.get("proof_state", ""),
        data.get("proof_raw_text", ""),
        data.get("proof_doc_types", ""),
        data.get("name_match", 0),
        data.get("dob_match", 0),
        data.get("address_score", 0.0),
        data.get("pincode_match", 0),
        data.get("overall_score", 0.0),
        data.get("verification_bucket", "Manual Review"),
        data.get("document_status", "Pending"),
        data.get("file_path", ""),
        data.get("folder_location", ""),
        data.get("batch_id", ""),
        data.get("processing_error", ""),
        datetime.now().isoformat(),
        "Processed",
    ))

    record_id = cursor.lastrowid
    conn.commit()
    conn.close()
    print(f"[DATABASE] Pan document #{record_id} inserted")
    return record_id


def _parse_pan_doc_row(row):
    if not row:
        return None
    r = dict(row)
    try:
        r["page_analysis"] = json.loads(r.get("page_analysis", "[]"))
    except (json.JSONDecodeError, TypeError):
        r["page_analysis"] = []
    return r


def get_pan_document_by_id(doc_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM pan_documents WHERE id = ?", (doc_id,))
    row = cursor.fetchone()
    conn.close()
    return _parse_pan_doc_row(row)


def get_pan_documents_by_status(status: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM pan_documents WHERE document_status = ? ORDER BY created_at DESC",
        (status,),
    )
    rows = cursor.fetchall()
    conn.close()
    return [_parse_pan_doc_row(r) for r in rows]


def get_all_pan_documents():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM pan_documents ORDER BY created_at DESC")
    rows = cursor.fetchall()
    conn.close()
    return [_parse_pan_doc_row(r) for r in rows]


def update_pan_document_status(doc_id: int, new_status: str, reviewed_by: str = ""):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE pan_documents
        SET document_status = ?, reviewed_by = ?, reviewed_at = ?
        WHERE id = ?
    """, (new_status, reviewed_by, datetime.now().isoformat(), doc_id))
    conn.commit()
    conn.close()
    print(f"[DATABASE] Pan document #{doc_id} status -> {new_status}")


def get_batch_stats():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) as total FROM pan_documents")
    total = cursor.fetchone()["total"]

    cursor.execute("SELECT COUNT(*) as cnt FROM pan_documents WHERE document_status = 'Approved'")
    approved = cursor.fetchone()["cnt"]

    cursor.execute("SELECT COUNT(*) as cnt FROM pan_documents WHERE document_status = 'Manual'")
    manual = cursor.fetchone()["cnt"]

    cursor.execute("SELECT COUNT(*) as cnt FROM pan_documents WHERE document_status = 'Rejected'")
    rejected = cursor.fetchone()["cnt"]

    cursor.execute("SELECT COUNT(*) as cnt FROM pan_documents WHERE document_status = 'Error'")
    errors = cursor.fetchone()["cnt"]

    cursor.execute("SELECT AVG(overall_score) as avg_score FROM pan_documents WHERE document_status != 'Error'")
    avg_score = cursor.fetchone()["avg_score"] or 0

    conn.close()
    return {
        "total": total,
        "approved": approved,
        "manual": manual,
        "rejected": rejected,
        "errors": errors,
        "avg_score": round(avg_score, 2),
    }
