"""
Document Classifier: Detects document type from OCR-extracted text per page.
Supports: PAN Application Form, Aadhaar Card, Passport, Driving License,
Voter ID, and Unknown/Other.
"""

import re

# Document type constants
DOC_PAN_FORM = "PAN Application Form"
DOC_AADHAAR = "Aadhaar Card"
DOC_PASSPORT = "Passport"
DOC_DRIVING_LICENSE = "Driving License"
DOC_VOTER_ID = "Voter ID"
DOC_UNKNOWN = "Unknown"

# Keywords/patterns that identify each document type (case-insensitive matching)
DOCUMENT_SIGNATURES = {
    DOC_PAN_FORM: {
        "keywords": [
            "form 49a", "form 49aa", "permanent account number",
            "income tax department", "application for allotment",
            "pan card", "nsdl", "utiitsl", "uti infrastructure",
            "assessment year", "assessing officer", "ward/circle",
            "source of income", "aadhaar seeding",
        ],
        "patterns": [
            r"form\s*(?:no\.?\s*)?49\s*a",
            r"permanent\s*account\s*number",
            r"income\s*tax\s*(?:department|pan)",
            r"application\s*for\s*(?:allotment|new\s*pan)",
            r"(?:nsdl|utiitsl|protean)",
        ],
        "min_score": 2,  # Need at least 2 keyword/pattern hits
    },
    DOC_AADHAAR: {
        "keywords": [
            "aadhaar", "aadhar", "unique identification",
            "uidai", "enrollment", "mera aadhaar",
            "government of india", "vid",
        ],
        "patterns": [
            r"aadhaa?r",
            r"\b\d{4}\s*\d{4}\s*\d{4}\b",  # 12-digit Aadhaar number
            r"unique\s*identification",
            r"uidai",
        ],
        "min_score": 2,
    },
    DOC_PASSPORT: {
        "keywords": [
            "passport", "republic of india", "nationality",
            "place of birth", "place of issue", "date of issue",
            "date of expiry", "passport no", "type p",
            "ministry of external affairs", "emigration",
        ],
        "patterns": [
            r"passport\s*(?:no\.?|number)?",
            r"republic\s*of\s*india",
            r"date\s*of\s*(?:issue|expiry)",
            r"place\s*of\s*(?:birth|issue)",
            r"[A-Z]\d{7}",  # Passport number format
        ],
        "min_score": 2,
    },
    DOC_DRIVING_LICENSE: {
        "keywords": [
            "driving licence", "driving license", "motor vehicle",
            "transport department", "licence no", "license no",
            "class of vehicle", "cov", "rto",
            "non-transport", "transport",
            "validity", "blood group",
        ],
        "patterns": [
            r"driving\s*licen[cs]e",
            r"licen[cs]e\s*no",
            r"class\s*of\s*vehicle",
            r"motor\s*vehicle",
            r"transport\s*department",
            r"[A-Z]{2}\d{2}\s*\d{11}",  # DL number format
        ],
        "min_score": 2,
    },
    DOC_VOTER_ID: {
        "keywords": [
            "election commission", "voter", "electoral",
            "electors photo", "epic", "voter id",
            "polling station", "constituency",
            "election card",
        ],
        "patterns": [
            r"election\s*commission",
            r"voter\s*(?:id|identity)",
            r"electoral\s*(?:roll|photo)",
            r"electors?\s*photo",
            r"[A-Z]{3}\d{7}",  # EPIC number format
        ],
        "min_score": 2,
    },
}


def _score_document_type(text: str, signature: dict) -> int:
    """Calculate how many keyword/pattern hits match for a given document type."""
    text_lower = text.lower()
    score = 0

    # Check keywords
    for keyword in signature["keywords"]:
        if keyword.lower() in text_lower:
            score += 1

    # Check regex patterns
    for pattern in signature["patterns"]:
        if re.search(pattern, text, re.IGNORECASE):
            score += 1

    return score


def classify_page(page_text: str) -> dict:
    """
    Classify a single page's OCR text into a document type.
    Returns: {"doc_type": str, "confidence": float, "scores": dict}
    """
    if not page_text or len(page_text.strip()) < 10:
        print("[CLASSIFIER] Page text too short or empty -> Unknown")
        return {"doc_type": DOC_UNKNOWN, "confidence": 0.0, "scores": {}}

    scores = {}
    for doc_type, signature in DOCUMENT_SIGNATURES.items():
        scores[doc_type] = _score_document_type(page_text, signature)

    print(f"[CLASSIFIER] Scores: {scores}")

    # Find best match
    best_type = max(scores, key=scores.get)
    best_score = scores[best_type]
    min_required = DOCUMENT_SIGNATURES[best_type]["min_score"]

    if best_score >= min_required:
        # Calculate confidence as ratio of score to total possible hits
        total_possible = len(DOCUMENT_SIGNATURES[best_type]["keywords"]) + len(DOCUMENT_SIGNATURES[best_type]["patterns"])
        confidence = round(min(best_score / max(total_possible * 0.4, 1), 1.0) * 100, 1)
        print(f"[CLASSIFIER] Result: {best_type} (confidence={confidence}%, score={best_score})")
        return {"doc_type": best_type, "confidence": confidence, "scores": scores}
    else:
        print(f"[CLASSIFIER] Result: Unknown (best was {best_type} with score={best_score}, needed {min_required})")
        return {"doc_type": DOC_UNKNOWN, "confidence": 0.0, "scores": scores}


def classify_all_pages(pages_text: list[dict]) -> list[dict]:
    """
    Classify all pages from a combined PDF.
    Input:  [{"page_num": 1, "text": "..."}, ...]
    Output: [{"page_num": 1, "text": "...", "doc_type": "...", "confidence": ...}, ...]
    """
    print(f"\n{'='*50}")
    print(f"[CLASSIFIER] Classifying {len(pages_text)} page(s)")
    print(f"{'='*50}")
    results = []
    for page in pages_text:
        print(f"\n[CLASSIFIER] --- Page {page['page_num']} ---")
        classification = classify_page(page["text"])
        results.append({
            **page,
            "doc_type": classification["doc_type"],
            "confidence": classification["confidence"],
        })
    print(f"\n[CLASSIFIER] Classification summary:")
    for r in results:
        print(f"  Page {r['page_num']}: {r['doc_type']} ({r['confidence']}%)")
    return results


def get_doc_type_icon(doc_type: str) -> str:
    """Return a Bootstrap icon class for each document type (for frontend use)."""
    icons = {
        DOC_PAN_FORM: "bi-file-earmark-text",
        DOC_AADHAAR: "bi-person-badge",
        DOC_PASSPORT: "bi-globe",
        DOC_DRIVING_LICENSE: "bi-car-front",
        DOC_VOTER_ID: "bi-card-checklist",
        DOC_UNKNOWN: "bi-question-circle",
    }
    return icons.get(doc_type, "bi-file-earmark")


def get_doc_type_color(doc_type: str) -> str:
    """Return a Bootstrap color class for each document type."""
    colors = {
        DOC_PAN_FORM: "primary",
        DOC_AADHAAR: "success",
        DOC_PASSPORT: "info",
        DOC_DRIVING_LICENSE: "warning",
        DOC_VOTER_ID: "secondary",
        DOC_UNKNOWN: "danger",
    }
    return colors.get(doc_type, "dark")
