"""Small, safe email campaign runner.

Reads a contact list (CSV), cleans it (dedupe, invalid addresses), skips anyone who
unsubscribed or replied STOP, personalises a template and sends in small daily batches.
Every send is logged so the next run continues where the last one stopped.

Default is --dry-run: emails are written to ./outbox as .eml files instead of being sent.

Usage:
  python campaign.py --batch 3                    # dry run, 3 emails
  python campaign.py --batch 50 --send            # real send via SMTP (env vars below)
  python campaign.py --unsubscribe someone@x.com  # add to suppression list

SMTP env vars for --send: SMTP_HOST, SMTP_PORT (587), SMTP_USER, SMTP_PASSWORD, FROM_EMAIL
Optional IMAP env vars to read STOP replies: IMAP_HOST, IMAP_USER, IMAP_PASSWORD
"""
import argparse
import csv
import email
import imaplib
import json
import os
import re
import smtplib
import time
import urllib.parse
from datetime import datetime
from email.message import EmailMessage
from pathlib import Path

HERE = Path(__file__).parent
EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")
STOP_RE = re.compile(r"\b(stop|unsubscribe|remove me)\b", re.I)
LOG_FIELDS = ["timestamp", "email", "subject", "status", "detail"]


def load_contacts(path):
    """Return (clean_contacts, report) with duplicates and invalid rows removed."""
    seen, clean, invalid, dupes = set(), [], [], 0
    with open(path, newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            addr = (row.get("email") or "").strip().lower()
            if not EMAIL_RE.match(addr):
                invalid.append(row.get("email", ""))
                continue
            if addr in seen:
                dupes += 1
                continue
            seen.add(addr)
            row["email"] = addr
            clean.append(row)
    return clean, {"valid": len(clean), "duplicates": dupes, "invalid": invalid}


def load_set(path):
    if not path.exists():
        return set()
    return {line.strip().lower() for line in path.read_text().splitlines() if line.strip()}


def add_suppressed(path, addrs):
    current = load_set(path)
    new = {a.lower() for a in addrs} - current
    if new:
        with open(path, "a") as f:
            for a in sorted(new):
                f.write(a + "\n")
    return new


def stop_replies_from_json(path):
    if not path.exists():
        return set()
    replies = json.loads(path.read_text())
    return {r["from"].lower() for r in replies if STOP_RE.search(r.get("subject", "") + " " + r.get("body", ""))}


def stop_replies_from_imap():
    host, user, pw = os.getenv("IMAP_HOST"), os.getenv("IMAP_USER"), os.getenv("IMAP_PASSWORD")
    if not (host and user and pw):
        return set()
    found = set()
    with imaplib.IMAP4_SSL(host) as m:
        m.login(user, pw)
        m.select("INBOX", readonly=True)
        _, ids = m.search(None, "SINCE", (datetime.now()).strftime("01-%b-%Y"))
        for i in ids[0].split():
            _, data = m.fetch(i, "(RFC822)")
            msg = email.message_from_bytes(data[0][1])
            body = ""
            part = msg.get_payload(0) if msg.is_multipart() else msg
            try:
                body = part.get_payload(decode=True).decode(errors="ignore")
            except Exception:
                pass
            if STOP_RE.search(f"{msg.get('Subject', '')} {body[:500]}"):
                found.add(email.utils.parseaddr(msg.get("From"))[1].lower())
    return found


def already_sent(log_path):
    if not log_path.exists():
        return set()
    with open(log_path, newline="") as f:
        return {r["email"] for r in csv.DictReader(f) if r["status"] in ("sent", "dry-run")}


def render(template, contact, unsub_base):
    fields = {k: (v or "").strip() for k, v in contact.items()}
    fields["first_name"] = fields.get("first_name") or "there"
    fields["unsubscribe_url"] = f"{unsub_base}?email={urllib.parse.quote(contact['email'])}"
    text = template.format(**fields)
    subject, _, body = text.partition("\n")
    return subject.replace("Subject:", "").strip(), body.strip() + "\n"


def log(log_path, row):
    new = not log_path.exists()
    with open(log_path, "a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=LOG_FIELDS)
        if new:
            w.writeheader()
        w.writerow(row)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--contacts", default=HERE / "contacts.csv", type=Path)
    ap.add_argument("--template", default=HERE / "template.txt", type=Path)
    ap.add_argument("--replies", default=HERE / "replies.json", type=Path, help="sample replies for STOP detection")
    ap.add_argument("--suppress", default=HERE / "suppression.txt", type=Path)
    ap.add_argument("--log", default=HERE / "send_log.csv", type=Path)
    ap.add_argument("--outbox", default=HERE / "outbox", type=Path)
    ap.add_argument("--batch", type=int, default=50, help="max emails this run (daily batch)")
    ap.add_argument("--delay", type=float, default=2.0, help="seconds between real sends")
    ap.add_argument("--unsub-url", default="https://example.com/unsubscribe")
    ap.add_argument("--send", action="store_true", help="really send via SMTP (default: dry run)")
    ap.add_argument("--unsubscribe", metavar="EMAIL", help="add an address to the suppression list and exit")
    a = ap.parse_args()

    if a.unsubscribe:
        add_suppressed(a.suppress, [a.unsubscribe.strip()])
        print(f"Suppressed {a.unsubscribe}")
        return

    contacts, report = load_contacts(a.contacts)
    print(f"Contacts: {report['valid']} valid, {report['duplicates']} duplicates removed, "
          f"{len(report['invalid'])} invalid {report['invalid']}")

    stops = stop_replies_from_json(a.replies) | stop_replies_from_imap()
    new = add_suppressed(a.suppress, stops)
    if new:
        print(f"STOP replies found, suppressed: {sorted(new)}")
    suppressed, sent = load_set(a.suppress), already_sent(a.log)

    queue = [c for c in contacts if c["email"] not in suppressed and c["email"] not in sent]
    print(f"Suppressed: {len(suppressed)} | already sent: {len(sent)} | remaining: {len(queue)} | this batch: {min(a.batch, len(queue))}")

    template = a.template.read_text()
    smtp = None
    if a.send:
        smtp = smtplib.SMTP(os.environ["SMTP_HOST"], int(os.getenv("SMTP_PORT", "587")))
        smtp.starttls()
        smtp.login(os.environ["SMTP_USER"], os.environ["SMTP_PASSWORD"])
    else:
        a.outbox.mkdir(exist_ok=True)

    for c in queue[: a.batch]:
        subject, body = render(template, c, a.unsub_url)
        msg = EmailMessage()
        msg["From"] = os.getenv("FROM_EMAIL", "you@example.com")
        msg["To"] = c["email"]
        msg["Subject"] = subject
        msg["List-Unsubscribe"] = f"<{a.unsub_url}?email={urllib.parse.quote(c['email'])}>"
        msg.set_content(body)
        row = {"timestamp": datetime.now().isoformat(timespec="seconds"), "email": c["email"], "subject": subject}
        try:
            if smtp:
                smtp.send_message(msg)
                row.update(status="sent", detail="")
                time.sleep(a.delay)
            else:
                (a.outbox / f"{c['email']}.eml").write_bytes(bytes(msg))
                row.update(status="dry-run", detail=str(a.outbox.name))
        except Exception as e:  # keep going; failures are logged and retried next run
            row.update(status="failed", detail=str(e)[:200])
        log(a.log, row)
        print(f"  {row['status']:8} {c['email']}")

    if smtp:
        smtp.quit()


if __name__ == "__main__":
    main()
