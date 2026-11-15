# Email campaign runner (small, safe batches)

Cleans a contact list and sends a personalised email campaign in small daily batches.

- Removes duplicates (case/space-insensitive) and invalid addresses
- Skips anyone who replied **STOP** (IMAP inbox or `replies.json`) or is on `suppression.txt`
- Adds an unsubscribe link and a `List-Unsubscribe` header to every email
- Logs every send to `send_log.csv`; the next run continues where the last one stopped
- Dry-run by default: writes `.eml` files to `outbox/` so you can review before sending

```bash
python campaign.py --batch 3                    # dry run
python campaign.py --unsubscribe someone@x.com  # suppress an address
SMTP_HOST=... SMTP_USER=... SMTP_PASSWORD=... FROM_EMAIL=... python campaign.py --batch 50 --send
```

Sample run on `contacts.csv` (10 rows): 8 valid, 1 duplicate removed, 1 invalid, 1 STOP reply suppressed,
batches of 3 resume correctly, and blank first names fall back to "there".

## 3-touch follow-up sequence (`followup.py`)

Touch 1 "Is it time?" -> Touch 2 "How did the quotes go?" -> Touch 3 last check-in, N days apart. Anyone who replies leaves the sequence; STOP/DONE replies are suppressed forever.

```bash
python followup.py --today 2026-11-20 --gap 3 --batch 50
```

Tested over 5 simulated days: 6 contacts got exactly 3 touches 3 days apart, 1 STOP and 1 reply were never emailed again.
