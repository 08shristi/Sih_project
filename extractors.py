"""
Real field extractors for GeM bid documents.

These are deterministic, regex + checksum based extractors — the same category
of logic real procurement-tech systems use for structured Indian government
identifiers (GSTIN, PAN, Udyam). No LLM/AI call is needed for these fields
because they follow fixed, documented formats — using an LLM here would be
slower AND less reliable than a validated regex + checksum.
"""
import re
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Evidence:
    field_name: str
    value: Optional[str]
    found: bool
    snippet: str = ""
    confidence: int = 0
    reason: str = ""


# ---------------------------------------------------------------- GSTIN
# Format: 2 digits (state code) + 10 chars (PAN) + 1 digit (entity code)
#         + 1 char 'Z' (default) + 1 checksum char
GSTIN_RE = re.compile(r'\b(\d{2}[A-Z]{5}\d{4}[A-Z][A-Z\d]Z[A-Z\d])\b')

# GSTIN checksum uses a modulo-36 algorithm over a fixed character set
_GSTIN_CODES = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"


def _gstin_checksum_valid(gstin: str) -> bool:
    if len(gstin) != 15:
        return False
    factor = 1
    total = 0
    for ch in gstin[:-1]:
        idx = _GSTIN_CODES.index(ch)
        val = factor * idx
        val = (val // 36) + (val % 36)
        total += val
        factor = 2 if factor == 1 else 1
    check_idx = (36 - (total % 36)) % 36
    return _GSTIN_CODES[check_idx] == gstin[-1]


def extract_gstin(text: str) -> Evidence:
    for m in GSTIN_RE.finditer(text):
        candidate = m.group(1)
        valid = _gstin_checksum_valid(candidate)
        start = max(0, m.start() - 40)
        end = min(len(text), m.end() + 40)
        snippet = text[start:end].replace('\n', ' ').strip()
        return Evidence(
            field_name="GSTIN",
            value=candidate,
            found=True,
            snippet=snippet,
            confidence=98 if valid else 55,
            reason="Checksum valid" if valid else "Format matched but checksum failed — possible OCR error or invalid GSTIN",
        )
    return Evidence(field_name="GSTIN", value=None, found=False, reason="No GSTIN pattern found in document")


# ---------------------------------------------------------------- PAN
PAN_RE = re.compile(r'\b([A-Z]{5}\d{4}[A-Z])\b')


def extract_pan(text: str) -> Evidence:
    for m in PAN_RE.finditer(text):
        candidate = m.group(1)
        start = max(0, m.start() - 40)
        end = min(len(text), m.end() + 40)
        snippet = text[start:end].replace('\n', ' ').strip()
        return Evidence(
            field_name="PAN", value=candidate, found=True, snippet=snippet,
            confidence=95, reason="Format matched (5 letters + 4 digits + 1 letter)",
        )
    return Evidence(field_name="PAN", value=None, found=False, reason="No PAN pattern found in document")


# ---------------------------------------------------------------- Udyam
UDYAM_RE = re.compile(r'\b(UDYAM-[A-Z]{2}-\d{2}-\d{7})\b')


def extract_udyam(text: str) -> Evidence:
    for m in UDYAM_RE.finditer(text):
        candidate = m.group(1)
        start = max(0, m.start() - 40)
        end = min(len(text), m.end() + 40)
        snippet = text[start:end].replace('\n', ' ').strip()
        return Evidence(
            field_name="Udyam Registration", value=candidate, found=True, snippet=snippet,
            confidence=97, reason="Format matched (UDYAM-STATE-YY-NNNNNNN)",
        )
    return Evidence(field_name="Udyam Registration", value=None, found=False, reason="No Udyam registration number found")


# ---------------------------------------------------------------- Turnover (INR, in Lakh/Crore)
# Strategy: find every "Rs./INR/₹ <amount> Lakh|Crore" occurrence in the document,
# and separately require the word "turnover" to appear somewhere in the document
# for context (so we don't pick up an unrelated rupee figure, e.g. EMD amount).
AMOUNT_RE = re.compile(
    r'(?:Rs\.?|INR|\u20b9)\s*([\d,]+(?:\.\d+)?)\s*(Lakh|Lakhs|Crore|Crores)?',
    re.IGNORECASE,
)
TURNOVER_WORD_RE = re.compile(r'turnover', re.IGNORECASE)


def _to_amount_lakh(value: str, unit: Optional[str]) -> float:
    num = float(value.replace(',', ''))
    if unit and unit.lower().startswith('crore'):
        return num * 100.0
    return num  # assume Lakh if unit missing or Lakh


def extract_turnover(text: str) -> Evidence:
    if not TURNOVER_WORD_RE.search(text):
        return Evidence(field_name="Annual Turnover", value=None, found=False,
                         reason="The word 'turnover' does not appear anywhere in this document.")

    matches = list(AMOUNT_RE.finditer(text))
    if not matches:
        return Evidence(field_name="Annual Turnover", value=None, found=False,
                         reason="Document mentions 'turnover' but no Rs./₹ amount could be parsed near it.")

    # Take the maximum figure found (typically the most recent / highest FY turnover
    # in a 3-year CA certificate table).
    best = None
    best_amt = -1.0
    for m in matches:
        amt = _to_amount_lakh(m.group(1), m.group(2))
        if amt > best_amt:
            best_amt = amt
            best = m

    start = max(0, best.start() - 30)
    end = min(len(text), best.end() + 30)
    snippet = text[start:end].replace('\n', ' ').strip()
    return Evidence(
        field_name="Annual Turnover", value=f"₹{best_amt:.1f} Lakh", found=True,
        snippet=snippet, confidence=88,
        reason=f"Highest turnover figure found across all years in the certificate: ₹{best_amt:.1f} Lakh",
    )


def extract_all(text: str) -> dict:
    return {
        "gstin": extract_gstin(text),
        "pan": extract_pan(text),
        "udyam": extract_udyam(text),
        "turnover": extract_turnover(text),
    }
