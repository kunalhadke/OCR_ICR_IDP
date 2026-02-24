"""
Field Parser: Extracts structured fields (Name, DOB, Address, Pincode, State)
from raw OCR text using regex and pattern matching.
Supports document-type-aware parsing for better accuracy.

PAN Form 49A has structured fields:
  - Last Name / Surname
  - First Name
  - Middle Name
  - Father's Name (Last Name, First Name, Middle Name)
These are extracted separately and combined for comparison.
"""

import re

# Indian states and union territories
INDIAN_STATES = [
    "Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar", "Chhattisgarh",
    "Goa", "Gujarat", "Haryana", "Himachal Pradesh", "Jharkhand", "Karnataka",
    "Kerala", "Madhya Pradesh", "Maharashtra", "Manipur", "Meghalaya", "Mizoram",
    "Nagaland", "Odisha", "Punjab", "Rajasthan", "Sikkim", "Tamil Nadu",
    "Telangana", "Tripura", "Uttar Pradesh", "Uttarakhand", "West Bengal",
    "Andaman and Nicobar Islands", "Chandigarh", "Dadra and Nagar Haveli and Daman and Diu",
    "Delhi", "Jammu and Kashmir", "Ladakh", "Lakshadweep", "Puducherry",
    "New Delhi", "NCT of Delhi"
]

# Words that are form labels/instructions, NOT actual name values
_NOISE_WORDS = {
    "name", "first", "middle", "last", "surname", "father", "mother",
    "mentioned", "appearing", "proof", "identity", "applicant", "shri",
    "smt", "mr", "mrs", "ms", "son", "daughter", "wife", "of", "date",
    "dob", "address", "gender", "male", "female", "office", "signature",
    "photograph", "form", "49a", "pan", "permanent", "account", "number",
    "income", "tax", "department", "nsdl", "utiitsl", "assessment",
    "please", "tick", "fill", "applicable", "mandatory", "field",
    "to", "be", "as", "in", "the", "a", "an", "is", "for",
    # Common non-name words from documents
    "mobile", "phone", "email", "telephone", "fax", "website",
    "government", "india", "republic", "uidai", "aadhaar", "aadhar",
    "election", "commission", "transport", "passport", "voter",
    "district", "state", "country", "pincode", "pin",
    "enrollment", "download", "generated", "valid", "verified",
    "vid", "virtual", "digital", "electronic",
}


def _clean_spaced_text(text: str) -> str:
    """
    Clean OCR text from box-style forms where each letter is in a separate box.
    'S H A R M A' -> 'SHARMA', 'R A H U L' -> 'RAHUL'
    Also handles mixed: 'SHARMA' stays 'SHARMA'.
    """
    # Check if text looks like spaced-out letters (single chars separated by spaces)
    parts = text.strip().split()
    if all(len(p) == 1 for p in parts) and len(parts) >= 2:
        return "".join(parts)
    return text.strip()


def _is_valid_name(name: str) -> bool:
    """Check if extracted text is a real name, not a form label/instruction."""
    if not name or len(name) < 2:
        return False
    words = name.lower().split()
    # Reject if most words are noise/labels
    noise_count = sum(1 for w in words if w.strip(".") in _NOISE_WORDS)
    if noise_count > len(words) * 0.5:
        return False
    # Reject if it contains instruction-like phrases
    noise_phrases = [
        "to be mentioned", "as appearing", "proof of identity",
        "please tick", "fill in", "applicable", "mandatory",
        "income tax", "permanent account", "assessment year",
        "of office",
    ]
    name_lower = name.lower()
    for phrase in noise_phrases:
        if phrase in name_lower:
            return False
    return True


def _get_value_after_label(text: str, label_pattern: str, name_mode: bool = True) -> str:
    """
    Given OCR text and a label pattern, find the label and extract the
    value that appears after it (same line or next line).
    Handles box-format (spaced letters) and normal text.

    name_mode=True  -> strict validation (for name fields: mostly alpha, not noise)
    name_mode=False -> relaxed validation (for address fields: allow numbers, slashes, etc.)
    """
    match = re.search(label_pattern, text, re.IGNORECASE)
    if not match:
        return ""

    # Get text after the label on the same line
    after_label = text[match.end():]
    lines = after_label.split("\n")

    for line in lines[:3]:  # Check up to 3 lines after label
        line = line.strip()
        if not line:
            continue
        cleaned = _clean_spaced_text(line)
        # Remove common delimiters/punctuation at start
        cleaned = re.sub(r"^[\s:\-\.]+", "", cleaned).strip()
        if not cleaned or len(cleaned) < 1:
            continue

        if name_mode:
            # Strict: must look like a name (mostly letters, not noise)
            alpha_ratio = sum(1 for c in cleaned if c.isalpha()) / max(len(cleaned), 1)
            if alpha_ratio >= 0.7 and len(cleaned) >= 2 and _is_valid_name(cleaned):
                return cleaned
        else:
            # Relaxed: accept any non-trivial text (for address/pin fields)
            # Just reject if it's purely a label or instruction
            if len(cleaned) >= 1 and not re.match(
                r"^(Name\s*of|Flat|Road|Area|Town|State|PIN|ZIP|Country|Please|Tick|Select)\b",
                cleaned, re.IGNORECASE
            ):
                return cleaned

    return ""


def _extract_pan_form_name(text: str) -> str:
    """
    Extract full name from PAN Application Form 49A.
    The form has separate fields:
      - Last Name / Surname
      - First Name
      - Middle Name
    We extract each and combine as 'First Middle Last'.
    """
    print("[PARSER-PAN] Extracting structured name from PAN form")

    last_name = _get_value_after_label(text, r"(?:Last\s*Name|Surname)\s*[/\-]?\s*(?:Surname|Last\s*Name)?")
    first_name = _get_value_after_label(text, r"First\s*Name")
    middle_name = _get_value_after_label(text, r"Middle\s*Name")

    print(f"[PARSER-PAN]   Last Name  : '{last_name}'")
    print(f"[PARSER-PAN]   First Name : '{first_name}'")
    print(f"[PARSER-PAN]   Middle Name: '{middle_name}'")

    # Build full name: First Middle Last
    parts = [p for p in [first_name, middle_name, last_name] if p]
    full_name = " ".join(parts)

    if full_name and _is_valid_name(full_name):
        print(f"[PARSER-PAN]   Full Name  : '{full_name}'")
        return full_name

    # Fallback: try "Name" field that sometimes appears on filled forms
    name_val = _get_value_after_label(text, r"(?:Applicant(?:'s)?\s*Name|Full\s*Name)\s*[:\-]?")
    if name_val and _is_valid_name(name_val):
        print(f"[PARSER-PAN]   Fallback Name: '{name_val}'")
        return name_val

    return ""


def _extract_pan_form_father_name(text: str) -> str:
    """
    Extract father's name from PAN Form 49A.
    The form has father's name with sub-fields or a single 'Father's Name' field.
    """
    # Try structured father's name fields
    father_last = _get_value_after_label(text, r"Father(?:'s)?\s*(?:Last\s*Name|Surname)")
    father_first = _get_value_after_label(text, r"Father(?:'s)?\s*First\s*Name")
    father_middle = _get_value_after_label(text, r"Father(?:'s)?\s*Middle\s*Name")

    parts = [p for p in [father_first, father_middle, father_last] if p]
    if parts:
        return " ".join(parts)

    # Fallback: single Father's Name field
    father_name = _get_value_after_label(text, r"Father(?:'s)?\s*Name")
    if father_name and _is_valid_name(father_name):
        return father_name

    return ""


def _extract_aadhaar_name(text: str) -> str:
    """
    Extract name from Aadhaar card OCR text.
    Aadhaar cards have the name printed prominently. Common OCR layouts:
      1. "Name: YOGESH MANSARAM BHAMARE"  (with label)
      2. Lines of text where one line is the person's all-caps name
      3. Name appears before DOB line
    """
    print("[PARSER-AADHAAR] Extracting name from Aadhaar")

    # Strategy 1: Explicit "Name" label
    name_patterns = [
        r"(?:Name|Naam)\s*[:\-]?\s*([A-Z][A-Za-z\s\.]{2,60})",
    ]
    for pattern in name_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            name = match.group(1).strip()
            # Truncate at known stop words
            name = re.sub(
                r"\s+(?:Date|DOB|Address|Father|Son|Daughter|House|Flat|Year|Gender|Male|Female|Mobile|Phone|S/O|D/O|W/O|C/O|VID).*",
                "", name, flags=re.IGNORECASE
            ).strip()
            if len(name) >= 3 and _is_valid_name(name):
                print(f"[PARSER-AADHAAR]   Found via label: '{name}'")
                return name

    # Strategy 2: Find prominent all-caps name lines (before DOB/Address)
    # Look for lines that are 2-4 words, all uppercase/titlecase, look like person names
    lines = text.split("\n")
    for i, line in enumerate(lines):
        line = line.strip()
        if not line or len(line) < 4:
            continue
        # Skip lines that are clearly labels or non-name content
        line_lower = line.lower()
        if any(kw in line_lower for kw in [
            "government", "india", "uidai", "aadhaar", "aadhar",
            "enrol", "download", "mobile", "phone", "address",
            "dob", "date of birth", "male", "female", "vid",
            "unique identification", "/", ":", "=",
            "election", "passport", "driving", "licence",
        ]):
            continue
        # Check if line looks like a person name (2-4 words, mostly alpha, each word capitalized)
        words = line.split()
        if 2 <= len(words) <= 5:
            alpha_chars = sum(1 for c in line if c.isalpha())
            if alpha_chars / max(len(line), 1) >= 0.85 and _is_valid_name(line):
                print(f"[PARSER-AADHAAR]   Found via line scan: '{line}'")
                return line

    return ""


def extract_name(text: str, doc_type: str = "") -> str:
    """Extract name from OCR text with document-type hints."""

    # PAN Application Form - use structured extraction
    if "PAN" in doc_type:
        name = _extract_pan_form_name(text)
        if name:
            return name
        # Fall through to generic if PAN-specific fails

    # Aadhaar - specialized extraction
    if "Aadhaar" in doc_type:
        name = _extract_aadhaar_name(text)
        if name:
            return name
        # Fall through to generic

    patterns = []

    if "Passport" in doc_type:
        patterns = [
            r"(?:Given\s*Name|Surname|Name)\s*[:\-/]?\s*([A-Z][A-Za-z\s\.]{2,50})",
            r"(?:GIVEN\s*NAME|SURNAME)\s*[:\-/]?\s*\n?\s*([A-Z][A-Za-z\s\.]{2,50})",
        ]
    elif "Driving" in doc_type:
        patterns = [
            r"(?:Name|Holder)\s*[:\-]?\s*([A-Z][A-Za-z\s\.]{2,50})",
        ]
    elif "Voter" in doc_type:
        patterns = [
            r"(?:Name|Elector)\s*[:\-]?\s*([A-Z][A-Za-z\s\.]{2,50})",
        ]

    # Generic fallback patterns
    patterns.extend([
        r"(?:Applicant(?:'s)?\s*Name|Full\s*Name)\s*[:\-]?\s*([A-Z][A-Za-z\s\.]{2,50})",
        r"(?:Shri|Smt|Mr|Mrs|Ms)\.?\s+([A-Z][A-Za-z\s\.]{2,50})",
    ])

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            name = match.group(1).strip()
            name = re.sub(
                r"\s+(?:Date|DOB|Address|Father|Son|Daughter|House|Flat|Year|Gender|Male|Female|Mobile|Phone).*",
                "", name, flags=re.IGNORECASE
            )
            name = name.strip()
            if len(name) >= 2 and _is_valid_name(name):
                return name
    return ""


def extract_dob(text: str, doc_type: str = "") -> str:
    """Extract Date of Birth in DD/MM/YYYY format."""
    patterns = [
        r"(?:Date\s*of\s*Birth|DOB|D\.O\.B|Birth\s*Date)\s*[:\-]?\s*(\d{1,2}[\-/\.]\d{1,2}[\-/\.]\d{2,4})",
    ]

    if "Aadhaar" in doc_type:
        patterns.insert(0, r"(?:DOB|Year\s*of\s*Birth)\s*[:\-]?\s*(\d{1,2}[\-/\.]\d{1,2}[\-/\.]\d{2,4})")
    elif "Passport" in doc_type:
        patterns.insert(0, r"(?:Date\s*of\s*Birth|DOB)\s*[:\-/]?\s*(\d{1,2}[\-/\.]\d{1,2}[\-/\.]\d{2,4})")

    # Generic fallback
    patterns.append(r"(\d{1,2}[\-/\.]\d{1,2}[\-/\.]\d{4})")

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            dob = match.group(1).strip()
            dob = dob.replace("-", "/").replace(".", "/")
            return dob
    return ""


def extract_pincode(text: str) -> str:
    """Extract 6-digit Indian pincode."""
    patterns = [
        r"(?:Pin\s*(?:Code)?|Pincode|PIN)\s*[:\-]?\s*(\d{6})",
        r"\b(\d{6})\b",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            pin = match.group(1)
            if pin[0] != "0":
                return pin
    return ""


def extract_state(text: str) -> str:
    """Extract Indian state name."""
    text_upper = text.upper()
    for state in INDIAN_STATES:
        if state.upper() in text_upper:
            return state
    abbr_map = {
        "MH": "Maharashtra", "DL": "Delhi", "KA": "Karnataka",
        "TN": "Tamil Nadu", "UP": "Uttar Pradesh", "GJ": "Gujarat",
        "RJ": "Rajasthan", "MP": "Madhya Pradesh", "WB": "West Bengal",
        "AP": "Andhra Pradesh", "TS": "Telangana", "KL": "Kerala",
        "PB": "Punjab", "HR": "Haryana", "BR": "Bihar",
    }
    for abbr, full_state in abbr_map.items():
        if re.search(rf"\b{abbr}\b", text):
            return full_state
    return ""


def _extract_pan_form_address(text: str) -> dict:
    """
    Extract structured address from PAN Application Form 49A.
    The form has separate labeled fields with values in boxes:
      - Name of office
      - Flat / Room / Door / Block No.
      - Name of Premises / Building / Village
      - Road / Street / Lane / Post Office
      - Area / Locality / Taluka / Sub-Division
      - Town / City / District
      - State / Union Territory
      - PIN Code
    We extract the VALUE after each label and combine.
    """
    print("[PARSER-PAN] Extracting structured address from PAN form")

    # Each tuple: (field_name, regex to find the label, then capture the value after it)
    address_fields = [
        ("flat",     r"Flat\s*/?\s*Room\s*/?\s*Door\s*/?\s*Block\s*(?:No\.?)?"),
        ("premises", r"Name\s*of\s*Premises\s*/?\s*Building\s*/?\s*Village"),
        ("road",     r"Road\s*/?\s*Street\s*/?\s*Lane\s*/?\s*Post\s*Office"),
        ("area",     r"Area\s*/?\s*Locality\s*/?\s*Taluka\s*/?\s*Sub[\-\s]*Division"),
        ("town",     r"Town\s*/?\s*City\s*/?\s*District"),
        ("state",    r"State\s*/?\s*Union\s*Terr(?:itory)?"),
        ("pin",      r"PIN\s*Code"),
    ]

    parts = {}
    for field_name, label_pattern in address_fields:
        val = _get_value_after_label(text, label_pattern, name_mode=False)
        # Also try: label followed by value on same line (OCR may put them together)
        if not val:
            match = re.search(label_pattern + r"[\s:\-\.]*([A-Z0-9][A-Za-z0-9\s/\-\.,]{1,100})", text, re.IGNORECASE)
            if match:
                candidate = match.group(1).strip()
                candidate = _clean_spaced_text(candidate)
                # Reject if it's another label
                if not re.match(r"^(Name|Road|Area|Town|State|Flat|PIN|ZIP)", candidate, re.IGNORECASE):
                    val = candidate
        if val:
            # Clean up: remove trailing labels that OCR may have merged
            val = re.split(
                r"\b(?:Name\s*of|Flat|Road|Area|Town|State|PIN\s*Code|ZIP\s*Code|Country)\b",
                val, flags=re.IGNORECASE
            )[0].strip().rstrip(",. ")
            parts[field_name] = val
            print(f"[PARSER-PAN]   {field_name:10s}: '{val}'")

    return parts


def _extract_aadhaar_address(text: str) -> str:
    """
    Extract address from Aadhaar card OCR text.
    Aadhaar addresses come in multiple formats:
      1. Simple: "Address: 7/98B, Water Tank Street, K.R.K Puram, Chittoor, AP 517583"
      2. Structured (e-Aadhaar): "VTC: Sarade, PO: Sarde, Sub District: Baglan, District: Nashik, State: Maharashtra, 423204"
      3. S/O prefix: "S/O KRISHNA REDD, 7/98B ..."
    Also cleans common OCR artifacts from Aadhaar cards.
    """
    print("[PARSER-AADHAAR] Extracting address from Aadhaar")

    # Strategy 1: Extract structured VTC/PO/District format
    vtc_parts = {}
    structured_labels = [
        ("house",        r"(?:House|H\.?\s*No|Flat|Door)\s*[:\-]?\s*([A-Za-z0-9/\-\.,\s]{1,80})"),
        ("vtc",          r"VTC\s*[:\-]?\s*([A-Za-z\s\.]{2,50})"),
        ("po",           r"PO\s*[:\-]?\s*([A-Za-z\s\.]{2,50})"),
        ("sub_district", r"Sub\s*District\s*[:\-]?\s*([A-Za-z\s\.]{2,50})"),
        ("district",     r"District\s*[:\-]?\s*([A-Za-z\s\.]{2,50})"),
        ("state",        r"State\s*[:\-]?\s*([A-Za-z\s\.]{2,50})"),
    ]
    for field_name, pattern in structured_labels:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            val = match.group(1).strip()
            # Clean: stop at next label or comma+label
            val = re.split(r"[,\n]?\s*(?:VTC|PO|Sub\s*District|District|State|PIN|Mobile|Phone|\d{4}\s*\d{4}\s*\d{4})", val, flags=re.IGNORECASE)[0].strip()
            val = val.rstrip(",. ")
            if val and len(val) >= 2:
                vtc_parts[field_name] = val

    if len(vtc_parts) >= 2:
        # Also capture the free-text part BEFORE VTC labels (locality, street, etc.)
        prefix_text = ""
        addr_match = re.search(r"(?:Address)\s*[:\-]?\s*(.+?)(?:VTC|PO\s*[:\-]|Sub\s*District|District\s*[:\-])", text, re.IGNORECASE | re.DOTALL)
        if addr_match:
            prefix_text = addr_match.group(1).strip()
            # Clean OCR noise from prefix
            prefix_text = _clean_aadhaar_address(prefix_text)
            # Remove person's name if it appears at the start of address
            # (Aadhaar often repeats the person's name in the address block)
            prefix_text = re.sub(r"^[\s,]*$", "", prefix_text).strip()

        ordered = ["house", "vtc", "po", "sub_district", "district", "state"]
        structured = ", ".join(vtc_parts[k] for k in ordered if k in vtc_parts)

        if prefix_text and len(prefix_text) >= 3:
            addr = f"{prefix_text}, {structured}"
        else:
            addr = structured
        # Remove duplicate commas
        addr = re.sub(r",\s*,+", ",", addr).strip(", ")
        print(f"[PARSER-AADHAAR]   Structured address: '{addr}'")
        return addr

    # Strategy 2: Generic "Address:" or "S/O|D/O|W/O|C/O" label
    patterns = [
        r"(?:Address)\s*[:\-]?\s*(.{10,300})",
        r"(?:S/O|D/O|W/O|C/O)\s*[:\-]?\s*(.{10,300})",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        if match:
            addr = match.group(1).strip()
            addr = _clean_aadhaar_address(addr)
            if addr and len(addr) >= 5:
                print(f"[PARSER-AADHAAR]   Address via label: '{addr}'")
                return addr

    return ""


def _clean_aadhaar_address(addr: str) -> str:
    """Clean OCR artifacts common in Aadhaar card address text."""
    if not addr:
        return ""

    # Stop at known end markers
    addr = re.split(
        r"(?:Telephone|Phone|Mobile|Email|PAN|Signature|Photo|Date\s*of|DOB|Gender)",
        addr, flags=re.IGNORECASE
    )[0]

    # Remove Aadhaar number (12 digits)
    addr = re.sub(r"\b\d{4}\s*\d{4}\s*\d{4}\b.*$", "", addr).strip()
    # Remove VID
    addr = re.sub(r"\bVID\s*[:\-]?\s*\d+.*$", "", addr, flags=re.IGNORECASE).strip()

    # Remove common Aadhaar OCR noise words/phrases
    aadhaar_noise = [
        r"aadhaa?r\s*is\s*proof\s*o?f?\s*identity[,.\s]*",
        r"m\s*aadhaa?rs?\b",
        r"\bnf\s+citizshi\s*r?\b",
        r"\baadhaa?r\b",
        r"\buidai\b",
        r"\benrollment\b",
        r"\bdownload\b",
        r"\bgenerated\b",
        r"\bverified\b",
    ]
    for noise in aadhaar_noise:
        addr = re.sub(noise, "", addr, flags=re.IGNORECASE)

    # Clean up VTC/PO/District labels into just values
    addr = re.sub(r"\bVTC\s*[:\-]?\s*", "", addr, flags=re.IGNORECASE)
    addr = re.sub(r"\bPO\s*[:\-]?\s*", "", addr, flags=re.IGNORECASE)
    addr = re.sub(r"\bSub\s*District\s*[:\-]?\s*", "", addr, flags=re.IGNORECASE)
    addr = re.sub(r"\bDistrict\s*[:\-]?\s*", "", addr, flags=re.IGNORECASE)
    addr = re.sub(r"\bState\s*[:\-]?\s*", "", addr, flags=re.IGNORECASE)

    # Remove stray single characters and OCR fragments (like "h/", "/y", "H3")
    addr = re.sub(r"\b[a-zA-Z][/\\]\s*", "", addr)
    addr = re.sub(r"\s[/\\][a-zA-Z]\b", "", addr)
    addr = re.sub(r"\b[A-Z]\d\b", "", addr)

    # Clean up whitespace and punctuation
    addr = re.sub(r"\s+", " ", addr).strip()
    addr = re.sub(r"[,\s]+,", ",", addr)  # multiple commas
    addr = re.sub(r"^[\s,\-\.]+|[\s,\-\.]+$", "", addr)

    return _clean_extracted_address(addr)


def extract_address(text: str, doc_type: str = "") -> str:
    """Extract address block from OCR text."""

    # PAN Application Form - use structured field extraction
    if "PAN" in doc_type:
        parts = _extract_pan_form_address(text)
        if parts:
            ordered = ["flat", "premises", "road", "area", "town"]
            addr_parts = [parts[k] for k in ordered if k in parts and parts[k]]
            if parts.get("state"):
                addr_parts.append(parts["state"])
            if parts.get("pin"):
                addr_parts.append(parts["pin"])
            combined = ", ".join(addr_parts)
            if len(combined) >= 5:
                print(f"[PARSER-PAN]   Full Address: '{combined}'")
                return combined

    # Aadhaar Card - specialized extraction
    if "Aadhaar" in doc_type:
        addr = _extract_aadhaar_address(text)
        if addr:
            return addr

    # Generic fallback for other document types
    patterns = []
    if "Passport" in doc_type:
        patterns.append(r"(?:Address|Place\s*of\s*Birth)\s*[:\-]?\s*(.{10,250})")

    patterns.extend([
        r"(?:Address|Residential\s*Address|Correspondence\s*Address|Permanent\s*Address)\s*[:\-]?\s*(.{10,200})",
    ])

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        if match:
            addr = match.group(1).strip()
            addr = re.split(
                r"(?:Telephone|Phone|Mobile|Email|PAN|Signature|Photo|Date\s*of|DOB|Gender)",
                addr, flags=re.IGNORECASE
            )[0]
            addr = re.sub(r"\b\d{4}\s*\d{4}\s*\d{4}\b.*$", "", addr).strip()
            addr = re.sub(r"\s+", " ", addr).strip()
            addr = _clean_extracted_address(addr)
            if addr and len(addr) >= 5:
                return addr[:300]
    return ""


# PAN form label fragments that should NEVER appear in a real address
_ADDRESS_NOISE_PHRASES = [
    "name of office", "flat / room / door / block",
    "name of premises / building / village",
    "road / street / lane / post office",
    "road / street / lane/post office",
    "area / locality / taluka",
    "town / city / district",
    "state / union terr",
    "pin code", "zip code",
    "please select title", "as applicable",
    "shri smt kumari", "m/s",
    "sub- division", "sub-division", "sub division",
]


def _clean_extracted_address(addr: str) -> str:
    """
    Remove PAN form label text that got accidentally captured in an address.
    These are field labels like 'Flat / Room / Door / Block No.' that are NOT
    actual address values.
    """
    if not addr:
        return ""

    addr_lower = addr.lower()

    # If the address is mostly PAN form labels, reject it entirely
    noise_count = sum(1 for phrase in _ADDRESS_NOISE_PHRASES if phrase in addr_lower)
    if noise_count >= 2:
        print(f"[PARSER] Address rejected (contains {noise_count} form label phrases): '{addr[:80]}...'")
        return ""

    # Remove any individual noise phrases that snuck in
    cleaned = addr
    for phrase in _ADDRESS_NOISE_PHRASES:
        cleaned = re.sub(re.escape(phrase), "", cleaned, flags=re.IGNORECASE)

    # Clean up leftover whitespace and punctuation
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    cleaned = re.sub(r"^[\s,\-\.]+|[\s,\-\.]+$", "", cleaned)

    return cleaned


def parse_document(raw_text: str, doc_type: str = "") -> dict:
    """Parse all fields from raw OCR text with optional document type hint."""
    print(f"\n[PARSER] Parsing fields for doc_type='{doc_type}'")
    fields = {
        "name": extract_name(raw_text, doc_type),
        "dob": extract_dob(raw_text, doc_type),
        "address": "",
        "pincode": extract_pincode(raw_text),
        "state": extract_state(raw_text),
        "father_name": "",
    }

    # PAN form: use structured address extraction, also get pin/state from address fields
    if "PAN" in doc_type:
        fields["father_name"] = _extract_pan_form_father_name(raw_text)
        pan_addr_parts = _extract_pan_form_address(raw_text)
        if pan_addr_parts:
            ordered = ["flat", "premises", "road", "area", "town"]
            addr_parts = [pan_addr_parts[k] for k in ordered if k in pan_addr_parts and pan_addr_parts[k]]
            if pan_addr_parts.get("state"):
                addr_parts.append(pan_addr_parts["state"])
            if pan_addr_parts.get("pin"):
                addr_parts.append(pan_addr_parts["pin"])
            combined = ", ".join(addr_parts)
            if len(combined) >= 5:
                fields["address"] = combined
            # Use structured pin/state if generic extraction missed them
            if not fields["pincode"] and pan_addr_parts.get("pin"):
                pin = re.search(r"\d{6}", pan_addr_parts["pin"])
                if pin:
                    fields["pincode"] = pin.group()
            if not fields["state"] and pan_addr_parts.get("state"):
                fields["state"] = pan_addr_parts["state"]

    # Non-PAN documents: use generic address extraction
    if not fields["address"]:
        fields["address"] = extract_address(raw_text, doc_type)

    # Post-processing: remove person's name from address (Aadhaar often repeats it)
    if fields["name"] and fields["address"]:
        name_lower = fields["name"].lower().strip()
        addr_lower = fields["address"].lower()
        if name_lower in addr_lower:
            fields["address"] = re.sub(
                re.escape(fields["name"]), "", fields["address"], count=1, flags=re.IGNORECASE
            ).strip().lstrip(",. ").strip()

    # Post-processing: deduplicate address parts (e.g., "Baglan, Baglan" -> "Baglan")
    if fields["address"]:
        parts = [p.strip() for p in fields["address"].split(",") if p.strip()]
        seen = []
        for p in parts:
            if p.lower() not in [s.lower() for s in seen]:
                seen.append(p)
        fields["address"] = ", ".join(seen)

    print(f"[PARSER] Extracted fields:")
    print(f"  Name        : {fields['name'] or '(not found)'}")
    if fields.get("father_name"):
        print(f"  Father Name : {fields['father_name']}")
    print(f"  DOB         : {fields['dob'] or '(not found)'}")
    print(f"  Address     : {fields['address'][:80] + '...' if len(fields['address']) > 80 else fields['address'] or '(not found)'}")
    print(f"  Pincode     : {fields['pincode'] or '(not found)'}")
    print(f"  State       : {fields['state'] or '(not found)'}")
    return fields


def aggregate_fields(parsed_pages: list[dict]) -> dict:
    """
    Aggregate extracted fields from multiple pages of the same category.
    Picks the first non-empty value for each field across pages.
    """
    print(f"\n[PARSER] Aggregating fields from {len(parsed_pages)} page(s)")
    aggregated = {"name": "", "father_name": "", "dob": "", "address": "", "pincode": "", "state": ""}
    for page_fields in parsed_pages:
        for field in aggregated:
            if not aggregated[field] and page_fields.get(field):
                aggregated[field] = page_fields[field]
    print(f"[PARSER] Aggregated result:")
    for k, v in aggregated.items():
        print(f"  {k:8s}: {v or '(empty)'}")
    return aggregated
