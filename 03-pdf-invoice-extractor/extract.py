"""Extract invoice number, date, client and totals from a folder of PDF invoices into Excel.

Usage:
    python extract.py invoices/ --out invoices.xlsx
"""
import argparse
import glob
import os
import re

import pdfplumber
from openpyxl import Workbook
from openpyxl.styles import Font

FIELDS = {
    "invoice_number": r"Invoice\s*(?:Number|No\.?|#)\s*[:#]?\s*([A-Z0-9-]+)",
    "date": r"Invoice\s*Date\s*:?\s*([0-9]{4}-[0-9]{2}-[0-9]{2}|[0-9/.-]{8,10})",
    "client": r"Bill\s*To\s*:?\s*(.+)",
    "subtotal": r"Subtotal\s*:?\s*(?:USD|\$)?\s*([0-9,]+\.\d{2})",
    "tax": r"Tax[^:]*:?\s*(?:USD|\$)?\s*([0-9,]+\.\d{2})",
    "total": r"\bTotal\s*(?:Due)?\s*:?\s*(?:USD|\$)?\s*([0-9,]+\.\d{2})",
}
MONEY = {"subtotal", "tax", "total"}


def extract(path):
    with pdfplumber.open(path) as pdf:
        text = "\n".join(page.extract_text() or "" for page in pdf.pages)
    row = {"file": os.path.basename(path)}
    for name, pattern in FIELDS.items():
        m = re.search(pattern, text, re.IGNORECASE)
        val = m.group(1).strip() if m else None
        if val and name in MONEY:
            val = float(val.replace(",", ""))
        row[name] = val
    missing = [k for k in FIELDS if row[k] is None]
    row["status"] = "OK" if not missing else "CHECK: missing " + ", ".join(missing)
    if not missing and abs(row["subtotal"] + row["tax"] - row["total"]) > 0.01:
        row["status"] = "CHECK: totals do not add up"
    return row


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("folder")
    ap.add_argument("--out", default="invoices.xlsx")
    args = ap.parse_args()

    rows = [extract(p) for p in sorted(glob.glob(os.path.join(args.folder, "*.pdf")))]
    cols = ["file", "invoice_number", "date", "client", "subtotal", "tax", "total", "status"]
    wb = Workbook()
    ws = wb.active
    ws.title = "Invoices"
    ws.append([c.replace("_", " ").title() for c in cols])
    for cell in ws[1]:
        cell.font = Font(bold=True)
    for r in rows:
        ws.append([r[c] for c in cols])
        print(f"  {r['file']}: {r['client']} total={r['total']} [{r['status']}]")
    ws.append([])
    ws.append(["TOTAL", None, None, None, None, None, f"=SUM(G2:G{len(rows) + 1})"])
    wb.save(args.out)
    print(f"Extracted {len(rows)} invoices to {args.out}")


if __name__ == "__main__":
    main()
