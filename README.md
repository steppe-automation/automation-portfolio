# Automation Portfolio

Four small, working automation tools in Python by [steppe-automation](https://github.com/steppe-automation). Each runs end to end on sample data and is built to be adapted to a client's real data in hours, not days.

Need something like this for your data? Message me on Upwork or Fiverr.

| Project | What it does | Output |
| --- | --- | --- |
| [01-price-scraper](01-price-scraper/) | Scrapes product name, price, rating and stock across paginated catalogue pages, with retries and polite delays | Formatted Excel (filters, frozen header) |
| [02-email-classifier](02-email-classifier/) | Reads unread mail over IMAP, labels each email with Claude AI (lead, billing, support, meeting, newsletter), writes a one-line summary and priority | CSV ready for Google Sheets |
| [03-pdf-invoice-extractor](03-pdf-invoice-extractor/) | Pulls invoice number, date, client, subtotal, tax and total from a folder of PDFs, and flags invoices whose totals don't add up | Excel with a running total |
| [04-email-campaign](04-email-campaign/) | Cleans a contact list (duplicates, invalid addresses), skips STOP replies and unsubscribes, and sends personalised emails in small daily batches that resume where they stopped | `.eml` previews (dry run) or SMTP sends, plus a send log |

## Run

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

```bash
cd 01-price-scraper && ../.venv/bin/python scraper.py --pages 3 --out books.xlsx
```

```bash
cd 02-email-classifier && ../.venv/bin/python classify.py --source sample
```

```bash
cd 03-pdf-invoice-extractor && ../.venv/bin/python make_samples.py && ../.venv/bin/python extract.py invoices
```

```bash
cd 04-email-campaign && ../.venv/bin/python campaign.py --batch 3
```

The email classifier uses Claude when `ANTHROPIC_API_KEY` is set and falls back to keyword rules otherwise, so it never stops on an API error. For Gmail, set `IMAP_HOST=imap.gmail.com`, `IMAP_USER` and an App Password in `IMAP_PASSWORD`, then run with `--source imap`.

The scraper demo targets books.toscrape.com, a public sandbox made for scraping practice. Client sites are scraped only where their terms allow it.
