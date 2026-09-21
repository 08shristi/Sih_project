# PRAMAAN — Real Verification Engine (SIH26100)

AI-Powered Bid Compliance Verification Platform for GeM Procurement
**Problem Statement:** SIH26100 — Ministry of Petroleum & Natural Gas

This is the **real backend engine** behind the PRAMAAN prototype — it is not
a mock. It reads an actual PDF, extracts real identifiers with validated
formats, and runs a deterministic compliance rule engine against them.

## What is real here (and what is not — yet)

| Piece | Status |
|---|---|
| PDF text extraction (PyMuPDF) | ✅ Real — reads the actual file bytes |
| GSTIN extraction + mod-36 checksum validation | ✅ Real — implements the published GSTN checksum algorithm |
| PAN / Udyam format extraction | ✅ Real — regex-validated against the official format |
| Turnover extraction from CA certificates | ✅ Real — parses ₹/Rs. amounts near the word "turnover" |
| Compliance rule engine (turnover / GSTIN / PAN / Udyam) | ✅ Real — deterministic Python, not an LLM call |
| Evidence snippets returned to the officer | ✅ Real — always a verbatim substring of the source document (tested, see `test_evidence_snippet_is_grounded_in_real_document_text`) |
| OCR for scanned (image-only) PDFs | ❌ Not yet wired in — the API returns an honest 422 error instead of guessing |
| Cross-document contradiction detection | ❌ Not yet built |
| Government registry live lookups (GSTN/Udyam APIs) | ❌ Not yet built — would need production API credentials |
| Officer review UI, audit trail, dossier PDF | ❌ Lives only in the frontend prototype (mocked) so far |

We're deliberately explicit about this table — a reviewer or judge can ask
"is this real?" about any specific claim in the pitch and get a straight
answer instead of a vague "yes, mostly."

## Why deterministic rules, not an LLM, for the pass/fail decision

Anything with legal/statutory weight (turnover threshold, GSTIN checksum,
format validation) is decided by plain, auditable Python — not a
probabilistic model — so the verdict is reproducible and defensible in
front of a CVC auditor. An LLM/AI step would only be justified for the
*messy, unstructured* part of the job (reading varied document layouts,
matching fuzzy clause wording) — which is exactly where the roadmap adds
OCR and semantic matching next, not in the rule engine itself.

## Quickstart

```bash
git clone <this-repo>
cd pramaan-backend
pip install -r requirements.txt

# Generate 2 sample bidder PDFs to test with
python scripts/make_sample_pdfs.py

# Run the test suite
pytest tests/ -v

# Start the API
uvicorn app.main:app --reload --port 8000
```

Open `http://localhost:8000/docs` for interactive Swagger docs, or:

```bash
curl -X POST http://localhost:8000/api/verify \
  -F "file=@sample_docs/bidder_A_bharat_safety.pdf"
```

## Project structure

```
pramaan-backend/
├── app/
│   ├── main.py          # FastAPI app + /api/verify endpoint
│   ├── pdf_reader.py     # Real PDF text extraction (PyMuPDF)
│   ├── extractors.py     # GSTIN / PAN / Udyam / turnover extraction + validation
│   └── rules.py          # Deterministic compliance rule engine
├── scripts/
│   └── make_sample_pdfs.py   # Generates realistic test bidder PDFs
├── sample_docs/           # Generated sample PDFs (compliant + non-compliant bidder)
├── tests/
│   └── test_pipeline.py   # 9 automated tests incl. an anti-hallucination check
└── requirements.txt
```

## Roadmap (next real pieces to build)

1. Tesseract OCR fallback for scanned PDFs (`is_likely_scanned` already detects this case)
2. Semantic clause-to-evidence matching (RAG) for free-text tender requirements
3. A `/api/verify-tender` endpoint that parses the tender PDF itself, instead
   of hardcoded thresholds in `rules.py`
4. Wire the existing frontend prototype to call this API instead of using
   mock data
5. Seller/bidder pre-check mode — a genuine differentiator most competing
   systems for this problem statement only build for the buyer/officer side

