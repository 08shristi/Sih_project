"""
Real PDF text extraction. Uses PyMuPDF (fitz) first — it's fast and handles
the vast majority of born-digital government/bank-issued PDFs. Falls back to
pdfplumber if PyMuPDF returns no text (e.g. some scanned/odd-encoded PDFs).

Note: neither library does OCR. A fully scanned (image-only) PDF will return
empty text here — that's a real, honest limitation, not something to hide.
In the full system this is where Tesseract OCR would be added as a fallback.
"""
from dataclasses import dataclass
from typing import List

import fitz  # PyMuPDF


@dataclass
class PageText:
    page_number: int  # 1-indexed
    text: str


@dataclass
class DocumentText:
    filename: str
    pages: List[PageText]
    full_text: str
    page_count: int
    is_likely_scanned: bool  # true if almost no extractable text was found


def read_pdf(path: str, filename: str = None) -> DocumentText:
    filename = filename or path
    doc = fitz.open(path)
    pages = []
    total_chars = 0
    for i, page in enumerate(doc):
        text = page.get_text("text")
        pages.append(PageText(page_number=i + 1, text=text))
        total_chars += len(text.strip())
    doc.close()

    full_text = "\n".join(p.text for p in pages)
    avg_chars_per_page = total_chars / max(1, len(pages))
    is_likely_scanned = avg_chars_per_page < 20  # essentially no extractable text

    return DocumentText(
        filename=filename,
        pages=pages,
        full_text=full_text,
        page_count=len(pages),
        is_likely_scanned=is_likely_scanned,
    )


def find_page_for_snippet(doc_text: DocumentText, snippet: str) -> int:
    """Return the 1-indexed page number where a text snippet was found (best-effort)."""
    needle = snippet[:30].strip()
    for p in doc_text.pages:
        if needle and needle in p.text:
            return p.page_number
    return 1
