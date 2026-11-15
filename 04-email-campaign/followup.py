"""3-touch re-engagement sequence on top of campaign.py.

Touch 1 "Is it time?" -> wait N days -> Touch 2 "How did the quotes go?" -> wait -> Touch 3 last check-in.
Anyone who replies is removed from the sequence; STOP/DONE/unsubscribe replies are also suppressed forever.
Dry run by default (writes .eml to outbox/), same SMTP env vars as campaign.py with --send.

Usage: python followup.py --today 2026-11-20 [--gap 3] [--batch 50] [--send]
"""
import argparse, csv, json, os, re, smtplib
from datetime import date, timedelta
from email.message import EmailMessage
from pathlib import Path
import campaign as c

HERE = Path(__file__).parent
TOUCHES = [
    ("Quick check on your project", "Hi {first_name},\n\nIs it time to get your project at {centre_name} started? Happy to help with a quote.\n"),
    ("How did the quotes go?", "Hi {first_name},\n\nDid the quotes you collected work out? If not, we can beat them - just reply.\n"),
    ("Closing the loop", "Hi {first_name},\n\nLast note from us. If the project is done or on hold, no reply needed and we won't email again.\n"),
]
STATE = HERE / "followup_state.csv"


def load_state():
    if not STATE.exists():
        return {}
    with open(STATE, newline="") as f:
        return {r["email"]: r for r in csv.DictReader(f)}


def save_state(state):
    with open(STATE, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["email", "touch", "last_sent", "status"])
        w.writeheader(); w.writerows(state.values())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--today", default=date.today().isoformat())
    ap.add_argument("--gap", type=int, default=3, help="days between touches")
    ap.add_argument("--batch", type=int, default=50, help="max sends per run (per account cap)")
    ap.add_argument("--send", action="store_true")
    a = ap.parse_args()
    today = date.fromisoformat(a.today)

    contacts, _ = c.load_contacts(HERE / "contacts.csv")
    replies = json.loads((HERE / "replies.json").read_text()) if (HERE / "replies.json").exists() else []
    replied = {r["from"].lower() for r in replies}
    c.add_suppressed(HERE / "suppression.txt", c.stop_replies_from_json(HERE / "replies.json"))
    suppressed = c.load_set(HERE / "suppression.txt")
    state = load_state()

    smtp = None
    if a.send:
        smtp = smtplib.SMTP(os.environ["SMTP_HOST"], int(os.getenv("SMTP_PORT", "587"))); smtp.starttls()
        smtp.login(os.environ["SMTP_USER"], os.environ["SMTP_PASSWORD"])
    (HERE / "outbox").mkdir(exist_ok=True)

    sent = 0
    for ct in contacts:
        e = ct["email"]
        st = state.setdefault(e, {"email": e, "touch": "0", "last_sent": "", "status": "active"})
        if e in suppressed: st["status"] = "stopped"
        elif e in replied: st["status"] = "replied"
        if st["status"] != "active" or int(st["touch"]) >= len(TOUCHES) or sent >= a.batch:
            continue
        if st["last_sent"] and today < date.fromisoformat(st["last_sent"]) + timedelta(days=a.gap):
            continue
        n = int(st["touch"])
        subj, body = TOUCHES[n]
        fields = {k: (v or "").strip() for k, v in ct.items()}; fields["first_name"] = fields.get("first_name") or "there"
        msg = EmailMessage(); msg["To"] = e; msg["From"] = os.getenv("FROM_EMAIL", "you@example.com"); msg["Subject"] = subj
        msg.set_content(body.format(**fields) + "\nReply STOP to opt out.\n")
        if smtp: smtp.send_message(msg)
        else: (HERE / "outbox" / f"{e}.touch{n + 1}.eml").write_bytes(bytes(msg))
        st.update(touch=str(n + 1), last_sent=today.isoformat()); sent += 1
        print(f"  touch {n + 1}  {e}")
    save_state(state)
    counts = {}
    for st in state.values():
        k = st["status"] if st["status"] != "active" else f"after touch {st['touch']}"
        counts[k] = counts.get(k, 0) + 1
    print(f"{today}: sent {sent} | {counts}")
    if smtp: smtp.quit()


if __name__ == "__main__":
    main()
