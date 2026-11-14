"""Generate a few fake invoice PDFs so the extractor demo has input."""
import os

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

INVOICES = [
    ("INV-1001", "2026-10-02", "Northwind Traders", [("Web scraping setup", 1, 150.00), ("Monthly maintenance", 1, 60.00)]),
    ("INV-1002", "2026-10-15", "Blue Harbor LLC", [("Email automation", 1, 220.00), ("Training call (hours)", 2, 25.00)]),
    ("INV-1003", "2026-11-01", "Cedar & Co", [("PDF data extraction", 3, 40.00)]),
]


def make(path, number, date, client, items):
    c = canvas.Canvas(path, pagesize=A4)
    y = 800
    c.setFont("Helvetica-Bold", 18)
    c.drawString(50, y, "INVOICE")
    c.setFont("Helvetica", 11)
    for line in [f"Invoice Number: {number}", f"Invoice Date: {date}", f"Bill To: {client}"]:
        y -= 22
        c.drawString(50, y, line)
    y -= 36
    c.setFont("Helvetica-Bold", 11)
    c.drawString(50, y, "Description")
    c.drawString(330, y, "Qty")
    c.drawString(400, y, "Unit")
    c.drawString(480, y, "Amount")
    c.setFont("Helvetica", 11)
    subtotal = 0.0
    for desc, qty, unit in items:
        y -= 20
        amount = qty * unit
        subtotal += amount
        c.drawString(50, y, desc)
        c.drawString(330, y, str(qty))
        c.drawString(400, y, f"{unit:.2f}")
        c.drawString(480, y, f"{amount:.2f}")
    tax = round(subtotal * 0.10, 2)
    for label, val in [("Subtotal", subtotal), ("Tax (10%)", tax), ("Total Due", subtotal + tax)]:
        y -= 24
        c.drawString(380, y, f"{label}: USD {val:.2f}")
    c.save()


if __name__ == "__main__":
    os.makedirs("invoices", exist_ok=True)
    for number, date, client, items in INVOICES:
        make(os.path.join("invoices", f"{number}.pdf"), number, date, client, items)
    print(f"Wrote {len(INVOICES)} sample invoices to invoices/")
