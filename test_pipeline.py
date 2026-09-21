"""
Real automated tests — run with: pytest tests/ -v

These test the actual extraction + rule logic against real generated PDFs,
not hardcoded fixtures pretending to be results.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.pdf_reader import read_pdf
from app.extractors import extract_gstin, extract_pan, extract_turnover, _gstin_checksum_valid
from app.rules import run_all_rules, compliance_score

SAMPLE_DIR = os.path.join(os.path.dirname(__file__), "..", "sample_docs")


# ---------------------------------------------------------------- unit tests
def test_gstin_checksum_valid_known_good():
    assert _gstin_checksum_valid("27AAAPL1234C1ZE") is True


def test_gstin_checksum_rejects_tampered():
    # flip the last character — checksum must now fail
    assert _gstin_checksum_valid("27AAAPL1234C1ZA") is False


def test_pan_extraction_from_plain_text():
    ev = extract_pan("Please find enclosed PAN: AAAPL1234C for verification.")
    assert ev.found is True
    assert ev.value == "AAAPL1234C"


def test_gstin_not_found_returns_honest_negative():
    ev = extract_gstin("This document has no tax identifiers at all.")
    assert ev.found is False
    assert ev.value is None


def test_turnover_picks_highest_of_multiple_years():
    text = "turnover FY22: Rs. 20 Lakh FY23: Rs. 45 Lakh FY24: Rs. 30 Lakh"
    ev = extract_turnover(text)
    assert ev.found is True
    assert "45.0" in ev.value


def test_turnover_absent_without_keyword():
    ev = extract_turnover("Total contract value: Rs. 45 Lakh")
    assert ev.found is False  # no 'turnover' keyword — must not guess


# ---------------------------------------------------------------- integration tests (real PDFs)
def test_compliant_bidder_end_to_end():
    path = os.path.join(SAMPLE_DIR, "bidder_A_bharat_safety.pdf")
    doc = read_pdf(path)
    assert doc.is_likely_scanned is False
    from app.extractors import extract_all
    results = run_all_rules(extract_all(doc.full_text))
    score = compliance_score(results)
    assert score == 100
    assert all(r.status == "COMPLIANT" for r in results)


def test_low_turnover_bidder_is_flagged_non_compliant():
    path = os.path.join(SAMPLE_DIR, "bidder_B_shree_industries.pdf")
    doc = read_pdf(path)
    from app.extractors import extract_all
    results = run_all_rules(extract_all(doc.full_text))
    turnover_result = next(r for r in results if r.rule_id == "R1")
    assert turnover_result.status == "NON_COMPLIANT"
    assert "38.2" in turnover_result.evidence.value


def test_evidence_snippet_is_grounded_in_real_document_text():
    """Anti-hallucination check: every evidence snippet returned must be a
    substring that actually exists in the source document, never invented.
    (Snippets are whitespace-normalized for display, so we compare against a
    whitespace-normalized copy of the source text too.)"""
    import re
    path = os.path.join(SAMPLE_DIR, "bidder_A_bharat_safety.pdf")
    doc = read_pdf(path)
    from app.extractors import extract_all
    extracted = extract_all(doc.full_text)
    normalized_source = re.sub(r'\s+', ' ', doc.full_text)
    for field, ev in extracted.items():
        if ev.found:
            normalized_snippet = re.sub(r'\s+', ' ', ev.snippet)
            assert normalized_snippet in normalized_source, f"{field} snippet was not found verbatim in source text"
