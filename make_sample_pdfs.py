"""Generate 2 realistic sample bidder documents (as real PDFs) to prove the
extraction pipeline actually works on real files, not fixtures."""
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
import os

OUT = os.path.join(os.path.dirname(__file__), "..", "sample_docs")
os.makedirs(OUT, exist_ok=True)


def write_pdf(path, lines):
    c = canvas.Canvas(path, pagesize=A4)
    width, height = A4
    y = height - 80
    c.setFont("Helvetica-Bold", 14)
    c.drawString(60, height - 50, "CHARTERED ACCOUNTANT CERTIFICATE")
    c.setFont("Helvetica", 11)
    for line in lines:
        if y < 60:
            c.showPage()
            y = height - 60
            c.setFont("Helvetica", 11)
        c.drawString(60, y, line)
        y -= 22
    c.save()


# Bidder A — a genuinely compliant bidder (valid GSTIN checksum, turnover above threshold)
write_pdf(os.path.join(OUT, "bidder_A_bharat_safety.pdf"), [
    "M/s Bharat Safety Systems Pvt. Ltd.",
    "GSTIN: 27AAAPL1234C1ZE",
    "PAN: AAAPL1234C",
    "Udyam Registration: UDYAM-MP-03-0041231",
    "",
    "This is to certify that the average annual turnover of the above",
    "named entity for the last three financial years is as follows:",
    "",
    "FY 2022-23:  Rs. 68.4 Lakh",
    "FY 2023-24:  Rs. 74.1 Lakh",
    "FY 2024-25:  Rs. 81.2 Lakh",
    "",
    "Certified by: R.K. Associates, Chartered Accountants",
    "UDIN: 24123456BGFRTS9081",
])

# Bidder B — a bidder with a real compliance gap (turnover below threshold)
write_pdf(os.path.join(OUT, "bidder_B_shree_industries.pdf"), [
    "M/s Shree Industries",
    "GSTIN: 09XYZAB5678D1Z2",
    "PAN: XYZAB5678D",
    "",
    "This is to certify that the average annual turnover of the above",
    "named entity for the last three financial years is as follows:",
    "",
    "FY 2022-23:  Rs. 31.6 Lakh",
    "FY 2023-24:  Rs. 34.8 Lakh",
    "FY 2024-25:  Rs. 38.2 Lakh",
    "",
    "Certified by: N. Gupta & Co., Chartered Accountants",
])

print("Sample PDFs written to", os.path.abspath(OUT))
