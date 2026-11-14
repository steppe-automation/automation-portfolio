"""Scrape product names, prices and stock from a catalogue site into Excel.

Demo target: https://books.toscrape.com (a public sandbox built for scraping practice).

Usage:
    python scraper.py --pages 3 --out books.xlsx
"""
import argparse
import time
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from openpyxl import Workbook
from openpyxl.styles import Font
from openpyxl.utils import get_column_letter

BASE = "https://books.toscrape.com/"
RATING = {"One": 1, "Two": 2, "Three": 3, "Four": 4, "Five": 5}
HEADERS = {"User-Agent": "Mozilla/5.0 (portfolio-demo scraper)"}


def fetch(session, url, retries=3):
    for attempt in range(1, retries + 1):
        try:
            resp = session.get(url, timeout=15)
            resp.raise_for_status()
            resp.encoding = "utf-8"
            return resp.text
        except requests.RequestException as exc:
            if attempt == retries:
                raise
            wait = 2 * attempt
            print(f"  retry {attempt} after error: {exc} (waiting {wait}s)")
            time.sleep(wait)


def parse_page(html, page_url):
    soup = BeautifulSoup(html, "html.parser")
    rows = []
    for card in soup.select("article.product_pod"):
        link = card.h3.a
        price_text = card.select_one(".price_color").get_text(strip=True)
        rating_word = card.select_one(".star-rating")["class"][1]
        rows.append({
            "title": link["title"],
            "price_gbp": float(price_text.replace("£", "").replace("Â", "")),
            "rating": RATING.get(rating_word, 0),
            "in_stock": "In stock" in card.select_one(".availability").get_text(),
            "url": urljoin(page_url, link["href"]),
        })
    nxt = soup.select_one("li.next a")
    next_url = urljoin(page_url, nxt["href"]) if nxt else None
    return rows, next_url


def scrape(max_pages, delay):
    session = requests.Session()
    session.headers.update(HEADERS)
    url, page, all_rows = BASE, 0, []
    while url and page < max_pages:
        page += 1
        print(f"Page {page}: {url}")
        rows, url = parse_page(fetch(session, url), url)
        all_rows.extend(rows)
        time.sleep(delay)  # be polite to the server
    return all_rows


def save_excel(rows, path):
    wb = Workbook()
    ws = wb.active
    ws.title = "Products"
    cols = ["title", "price_gbp", "rating", "in_stock", "url"]
    ws.append(["Title", "Price (GBP)", "Rating (1-5)", "In stock", "URL"])
    for cell in ws[1]:
        cell.font = Font(bold=True)
    for r in rows:
        ws.append([r[c] for c in cols])
    for i, width in enumerate([55, 12, 12, 10, 70], start=1):
        ws.column_dimensions[get_column_letter(i)].width = width
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = ws.dimensions
    wb.save(path)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--pages", type=int, default=3, help="max pages to scrape")
    ap.add_argument("--delay", type=float, default=1.0, help="seconds between requests")
    ap.add_argument("--out", default="products.xlsx")
    args = ap.parse_args()
    rows = scrape(args.pages, args.delay)
    save_excel(rows, args.out)
    print(f"Saved {len(rows)} products to {args.out}")


if __name__ == "__main__":
    main()
