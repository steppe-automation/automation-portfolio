"""Classify incoming emails with AI and log them to a spreadsheet (CSV / Google Sheets import).

Sources:
  --source sample          read sample_emails.json (offline demo)
  --source imap            read unread mail over IMAP (Gmail: use an App Password)
                           env: IMAP_HOST, IMAP_USER, IMAP_PASSWORD

Classifier:
  If ANTHROPIC_API_KEY is set, Claude labels each email and writes a one-line summary.
  Otherwise a keyword fallback is used, so the demo always runs.

Usage:
    python classify.py --source sample --out emails.csv
"""
import argparse
import csv
import email
import imaplib
import json
import os
from datetime import datetime
from email.header import decode_header

CATEGORIES = ["Sales lead", "Billing", "Support", "Meeting", "Newsletter", "Other"]
MODEL = "claude-haiku-5-5"

KEYWORDS = {
    "Sales lead": ["quote", "pricing", "price", "proposal for", "units"],
    "Billing": ["invoice", "payment", "due", "receipt"],
    "Support": ["broken", "refund", "replacement", "not working", "issue", "help"],
    "Meeting": ["meet", "call", "available", "free on", "schedule"],
    "Newsletter": ["newsletter", "unsubscribe", "webinar"],
}


def load_sample(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _decode(value):
    parts = []
    for text, enc in decode_header(value or ""):
        parts.append(text.decode(enc or "utf-8", "replace") if isinstance(text, bytes) else text)
    return "".join(parts)


def load_imap(limit):
    host, user, pw = os.environ["IMAP_HOST"], os.environ["IMAP_USER"], os.environ["IMAP_PASSWORD"]
    conn = imaplib.IMAP4_SSL(host)
    conn.login(user, pw)
    conn.select("INBOX", readonly=True)
    _, ids = conn.search(None, "UNSEEN")
    out = []
    for msg_id in ids[0].split()[-limit:]:
        _, data = conn.fetch(msg_id, "(BODY.PEEK[])")
        msg = email.message_from_bytes(data[0][1])
        body = ""
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                body = part.get_payload(decode=True).decode(part.get_content_charset() or "utf-8", "replace")
                break
        out.append({"from": _decode(msg["From"]), "subject": _decode(msg["Subject"]), "body": body[:2000]})
    conn.logout()
    return out


def classify_keywords(msg):
    text = f"{msg['subject']} {msg['body']}".lower()
    scores = {cat: sum(k in text for k in words) for cat, words in KEYWORDS.items()}
    best = max(scores, key=scores.get)
    category = best if scores[best] > 0 else "Other"
    return {"category": category, "summary": msg["subject"], "priority": "High" if category in ("Sales lead", "Support") else "Normal"}


def classify_claude(client, msg):
    prompt = (
        f"Classify this email into one of: {', '.join(CATEGORIES)}.\n"
        "Reply with JSON only: {\"category\": ..., \"summary\": <max 15 words>, \"priority\": \"High\"|\"Normal\"}.\n\n"
        f"From: {msg['from']}\nSubject: {msg['subject']}\n\n{msg['body']}"
    )
    resp = client.messages.create(model=MODEL, max_tokens=200, messages=[{"role": "user", "content": prompt}])
    text = resp.content[0].text
    result = json.loads(text[text.find("{"): text.rfind("}") + 1])
    if result.get("category") not in CATEGORIES:
        result["category"] = "Other"
    return result


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--source", choices=["sample", "imap"], default="sample")
    ap.add_argument("--limit", type=int, default=25)
    ap.add_argument("--out", default="emails.csv")
    args = ap.parse_args()

    msgs = load_sample(os.path.join(os.path.dirname(__file__), "sample_emails.json")) if args.source == "sample" else load_imap(args.limit)

    client = None
    if os.environ.get("ANTHROPIC_API_KEY"):
        import anthropic
        client = anthropic.Anthropic()
    print(f"Classifier: {'Claude (' + MODEL + ')' if client else 'keyword fallback'}")

    new_file = not os.path.exists(args.out)
    with open(args.out, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if new_file:
            w.writerow(["Logged at", "From", "Subject", "Category", "Priority", "Summary"])
        for m in msgs:
            try:
                r = classify_claude(client, m) if client else classify_keywords(m)
            except Exception as exc:  # never lose an email because the AI call failed
                print(f"  AI failed ({exc}); using keywords")
                r = classify_keywords(m)
            w.writerow([datetime.now().isoformat(timespec="seconds"), m["from"], m["subject"], r["category"], r["priority"], r["summary"]])
            print(f"  [{r['category']:<10}] {m['subject']}")
    print(f"Logged {len(msgs)} emails to {args.out}")


if __name__ == "__main__":
    main()
