"""
PRAMAAN backend — real engine (not mocked).

Run: uvicorn app.main:app --reload --port 8000
Docs: http://localhost:8000/docs
"""
import shutil
import tempfile
import time
from pathlib import Path

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .pdf_reader import read_pdf, find_page_for_snippet
from .extractors import extract_all
from .rules import run_all_rules, compliance_score

app = FastAPI(
    title="PRAMAAN API",
    description="Real bid-document verification engine for SIH26100 (GeM Bid Compliance).",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class EvidenceOut(BaseModel):
    field: str
    value: str | None
    found: bool
    confidence: int
    page: int | None
    snippet: str
    reason: str


class RuleOut(BaseModel):
    rule_id: str
    requirement: str
    status: str
    reason: str
    evidence: EvidenceOut | None


class VerifyResponse(BaseModel):
    filename: str
    page_count: int
    is_likely_scanned: bool
    processing_ms: int
    compliance_score: int
    results: list[RuleOut]


@app.get("/health")
def health():
    return {"status": "ok", "service": "pramaan-backend"}


@app.post("/api/verify", response_model=VerifyResponse)
async def verify_document(file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported right now.")

    t0 = time.time()
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name

    try:
        doc = read_pdf(tmp_path, filename=file.filename)
    finally:
        Path(tmp_path).unlink(missing_ok=True)

    if doc.is_likely_scanned:
        # Honest failure mode — no OCR wired up yet in this slice of the backend.
        raise HTTPException(
            status_code=422,
            detail="This PDF appears to be a scanned image with no extractable text layer. "
                   "OCR fallback (Tesseract) is planned but not yet wired into this endpoint.",
        )

    extracted = extract_all(doc.full_text)
    rule_results = run_all_rules(extracted)
    score = compliance_score(rule_results)

    out_results = []
    for r in rule_results:
        ev = r.evidence
        page = find_page_for_snippet(doc, ev.snippet) if ev and ev.found else None
        out_results.append(RuleOut(
            rule_id=r.rule_id,
            requirement=r.requirement,
            status=r.status,
            reason=r.reason,
            evidence=EvidenceOut(
                field=ev.field_name, value=ev.value, found=ev.found,
                confidence=ev.confidence, page=page, snippet=ev.snippet, reason=ev.reason,
            ) if ev else None,
        ))

    return VerifyResponse(
        filename=doc.filename,
        page_count=doc.page_count,
        is_likely_scanned=doc.is_likely_scanned,
        processing_ms=int((time.time() - t0) * 1000),
        compliance_score=score,
        results=out_results,
    )
