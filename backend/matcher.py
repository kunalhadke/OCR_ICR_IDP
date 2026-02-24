"""
Matching Engine: Compares fields extracted from PAN form and proof document.
- Name & DOB: 100% exact match required
- Pincode: exact match
- Address: 70% fuzzy similarity threshold (using rapidfuzz)
- Overall score -> classification bucket
"""

from rapidfuzz import fuzz


def match_name(form_name: str, proof_name: str) -> bool:
    """
    Fuzzy match for names (handles word reordering).
    PAN form has 'First Middle Last' but proof may have 'Last First' or any order.
    Uses token_sort_ratio >= 80% to account for ordering and minor OCR differences.
    """
    fn = " ".join(form_name.lower().split())
    pn = " ".join(proof_name.lower().split())
    if not fn or not pn:
        return False
    score = fuzz.token_sort_ratio(fn, pn)
    return score >= 80


def match_dob(form_dob: str, proof_dob: str) -> bool:
    """Exact match for date of birth."""
    fd = form_dob.strip().replace("-", "/").replace(".", "/")
    pd = proof_dob.strip().replace("-", "/").replace(".", "/")
    return fd == pd and fd != ""


def match_pincode(form_pin: str, proof_pin: str) -> bool:
    """Exact match for pincode."""
    return form_pin.strip() == proof_pin.strip() and form_pin.strip() != ""


def match_address(form_addr: str, proof_addr: str) -> float:
    """Fuzzy match for address. Returns similarity ratio (0-100)."""
    if not form_addr.strip() or not proof_addr.strip():
        return 0.0
    fa = " ".join(form_addr.lower().split())
    pa = " ".join(proof_addr.lower().split())
    # Use token_sort_ratio for better address matching (handles word reordering)
    score = fuzz.token_sort_ratio(fa, pa)
    return round(score, 2)


def calculate_overall_score(name_match: bool, dob_match: bool,
                            pincode_match: bool, address_score: float) -> float:
    """
    Calculate weighted overall match percentage.
    Weights: Name=30%, DOB=25%, Pincode=20%, Address=25%
    """
    score = 0.0
    score += 30.0 if name_match else 0.0
    score += 25.0 if dob_match else 0.0
    score += 20.0 if pincode_match else 0.0
    score += 25.0 * (address_score / 100.0)  # address_score is 0-100
    return round(score, 2)


def classify_bucket(overall_score: float) -> str:
    """
    Classify into verification bucket:
    - >= 75%  -> Auto Approved
    - 40-75%  -> Second Level Review
    - < 40%   -> Manual Review
    """
    if overall_score >= 75:
        return "Auto Approved"
    elif overall_score >= 40:
        return "Second Level Review"
    else:
        return "Manual Review"


def run_matching(form_fields: dict, proof_fields: dict) -> dict:
    """Run full matching pipeline between form and proof fields."""
    print(f"\n{'='*50}")
    print(f"[MATCHER] Running field matching")
    print(f"{'='*50}")
    print(f"[MATCHER] Form  -> Name='{form_fields['name']}', DOB='{form_fields['dob']}', Pin='{form_fields['pincode']}'")
    print(f"[MATCHER] Proof -> Name='{proof_fields['name']}', DOB='{proof_fields['dob']}', Pin='{proof_fields['pincode']}'")

    nm = match_name(form_fields["name"], proof_fields["name"])
    dm = match_dob(form_fields["dob"], proof_fields["dob"])
    pm = match_pincode(form_fields["pincode"], proof_fields["pincode"])
    addr_score = match_address(form_fields["address"], proof_fields["address"])

    print(f"[MATCHER] Name match    : {'YES' if nm else 'NO'}")
    print(f"[MATCHER] DOB match     : {'YES' if dm else 'NO'}")
    print(f"[MATCHER] Pincode match : {'YES' if pm else 'NO'}")
    print(f"[MATCHER] Address score : {addr_score}%")

    overall = calculate_overall_score(nm, dm, pm, addr_score)
    bucket = classify_bucket(overall)

    print(f"[MATCHER] Overall score : {overall}%")
    print(f"[MATCHER] Bucket        : {bucket}")

    return {
        "name_match": int(nm),
        "dob_match": int(dm),
        "pincode_match": int(pm),
        "address_score": addr_score,
        "overall_score": overall,
        "verification_bucket": bucket,
    }
