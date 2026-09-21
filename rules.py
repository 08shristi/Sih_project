"""
Deterministic compliance rule engine.

Deliberately NOT an LLM call — per the PPT's own "Clause-as-Code" pitch and
per how VigilBid's own docs justify it (docs/RULE-ENGINE.md): anything with
legal/statutory weight should be deterministic code, not a probabilistic
model, so the verdict is reproducible and defensible in front of a CVC
auditor. AI/OCR is reserved for the messy unstructured extraction step —
the actual pass/fail decision below is plain, auditable Python.
"""
from dataclasses import dataclass
from typing import List, Optional

from .extractors import Evidence


@dataclass
class RuleResult:
    rule_id: str
    requirement: str
    status: str  # "COMPLIANT" | "NON_COMPLIANT" | "NEEDS_REVIEW"
    evidence: Optional[Evidence]
    reason: str


# Tender requirements, modelled on the PRAMAAN PPT (SIH26100) requirement set.
# In production these come from parsing the tender PDF itself (see pipeline/extraction/tender.py
# equivalent) — here they're the fixed thresholds for the demo tender, same as the prototype.
MIN_TURNOVER_LAKH = 50.0


def check_gstin(ev: Evidence) -> RuleResult:
    if not ev.found:
        return RuleResult("R2", "Valid GST registration certificate", "NON_COMPLIANT", ev,
                           "No GSTIN found in the uploaded document.")
    if ev.confidence >= 90:
        return RuleResult("R2", "Valid GST registration certificate", "COMPLIANT", ev,
                           f"GSTIN {ev.value} found and checksum-verified.")
    return RuleResult("R2", "Valid GST registration certificate", "NEEDS_REVIEW", ev,
                       f"GSTIN {ev.value} found but checksum did not validate — needs manual check.")


def check_pan(ev: Evidence) -> RuleResult:
    if not ev.found:
        return RuleResult("R2b", "Valid PAN", "NON_COMPLIANT", ev, "No PAN found in the uploaded document.")
    return RuleResult("R2b", "Valid PAN", "COMPLIANT", ev, f"PAN {ev.value} found and format-verified.")


def check_udyam(ev: Evidence) -> RuleResult:
    if not ev.found:
        return RuleResult("R3", "Udyam (MSE) registration certificate", "NEEDS_REVIEW", ev,
                           "No Udyam number found — only required if MSE preference is claimed.")
    return RuleResult("R3", "Udyam (MSE) registration certificate", "COMPLIANT", ev,
                       f"Udyam registration {ev.value} found.")


def check_turnover(ev: Evidence) -> RuleResult:
    if not ev.found:
        return RuleResult("R1", f"Minimum average annual turnover of ₹{MIN_TURNOVER_LAKH:.0f} Lakh",
                           "NEEDS_REVIEW", ev, "No turnover figure could be extracted from the document.")
    amount = float(ev.value.replace('₹', '').replace(' Lakh', '').replace(',', ''))
    if amount >= MIN_TURNOVER_LAKH:
        return RuleResult("R1", f"Minimum average annual turnover of ₹{MIN_TURNOVER_LAKH:.0f} Lakh",
                           "COMPLIANT", ev, f"Extracted turnover ₹{amount:.1f} Lakh meets the ₹{MIN_TURNOVER_LAKH:.0f} Lakh threshold.")
    return RuleResult("R1", f"Minimum average annual turnover of ₹{MIN_TURNOVER_LAKH:.0f} Lakh",
                       "NON_COMPLIANT", ev, f"Extracted turnover ₹{amount:.1f} Lakh is below the ₹{MIN_TURNOVER_LAKH:.0f} Lakh threshold.")


def run_all_rules(extracted: dict) -> List[RuleResult]:
    return [
        check_turnover(extracted["turnover"]),
        check_gstin(extracted["gstin"]),
        check_pan(extracted["pan"]),
        check_udyam(extracted["udyam"]),
    ]


def compliance_score(results: List[RuleResult]) -> int:
    if not results:
        return 0
    points = {"COMPLIANT": 100, "NEEDS_REVIEW": 50, "NON_COMPLIANT": 0}
    return round(sum(points[r.status] for r in results) / len(results))
