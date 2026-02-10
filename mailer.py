import smtplib
import imaplib
import csv
import sys
import time
import random
import os
from email.message import EmailMessage
from email.utils import formatdate

# Config
# CSV columns: Business Name, Email, City, Vorname, Stars (optional: Positive Observation)
# On Vercel/production set MAIL_USER and MAIL_PASS in environment variables.
SMTP_HOST = "smtp.hostinger.com"
SMTP_PORT = 465
IMAP_HOST = "imap.hostinger.com"
IMAP_PORT = 993
MAIL_USER = os.environ.get("MAIL_USER", "")
MAIL_PASS = os.environ.get("MAIL_PASS", "")

EMAIL_SUBJECT_TEMPLATE = "Quick question about {BusinessName}"

EMAIL_BODY_TEMPLATE = """\
Hallo {First_Name},

ich schaue mir aktuell einige {{Branche}}-Betriebe in {{City}} an und bin dabei auf {{BusinessName}} gestossen.
Mir ist aufgefallen, dass Sie aktuell bei {{ReviewsCount}} Google-Bewertungen stehen, während {{Competitor1}} und {{KCompetitor2}} in Ihrer Nähe deutlich mehr Sichtbarkeit über Google Maps haben.
Was schade ist – gerade weil {{PositiveObservation}} wirklich positiv heraussticht.
Falls Sie Ihre lokale Sichtbarkeit verbessern möchten, habe ich eine sehr einfache Idee, mit der Sie in den nächsten 30 Tagen – mit minimalem Aufwand – deutlich sichtbarer werden können.
Möchten Sie, dass ich Ihnen das kurz, kostenlos und unverbindlich zeige?
Beste Grüsse

Afrem
"""


def _sanitize_header(value):
  """Remove CR/LF from a string so it is safe for email headers (Subject, To, etc.)."""
  if value is None:
    return ""
  s = str(value).replace("\r\n", " ").replace("\r", " ").replace("\n", " ").strip()
  return " ".join(s.split())  # collapse multiple spaces


def save_to_sent_folder(msg):
  """Append a copy of the message to Hostinger Sent folder so it shows in webmail."""
  try:
    if "Date" not in msg:
      msg["Date"] = formatdate(localtime=True)
    raw = msg.as_bytes()
    raw = raw.replace(b"\n", b"\r\n")
    date_time = imaplib.Time2Internaldate(time.time())
    with imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT) as imap:
      imap.login(MAIL_USER, MAIL_PASS)
      imap.append("INBOX.Sent", "\\Seen", date_time, raw)
  except Exception as e:
    print(f" (copy to Sent folder skipped: {e})")


def send_email(to_email, row):
  # Normalize and sanitize so headers never contain newlines/carriage returns
  business_name = _sanitize_header(row.get("Business Name"))
  first_name = _sanitize_header(row.get("Vorname")) or "there"
  city = _sanitize_header(row.get("City"))
  reviews_count = _sanitize_header(row.get("Stars"))
  positive_observation = _sanitize_header(row.get("Positive Observation")) or "your business"
  to_email = _sanitize_header(to_email)

  subject = EMAIL_SUBJECT_TEMPLATE.format(BusinessName=business_name or "your business")
  body = EMAIL_BODY_TEMPLATE.format(
    First_Name=first_name,
    City=city or "your area",
    BusinessName=business_name or "your business",
    ReviewsCount=reviews_count or "—",
    PositiveObservation=positive_observation,
  )

  msg = EmailMessage()
  msg["Subject"] = subject
  msg["From"] = MAIL_USER
  msg["To"] = to_email
  msg.set_content(body)

  with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT) as smtp:
    smtp.login(MAIL_USER, MAIL_PASS)
    smtp.send_message(msg)
  save_to_sent_folder(msg)
  print(f"Sent to {to_email}")


def get_csv_file():
  """Use CSV from command line, or auto-detect the newest .csv in current folder."""
  if len(sys.argv) > 1:
    return sys.argv[1].strip()
  folder = os.path.dirname(os.path.abspath(__file__)) or "."
  csvs = [f for f in os.listdir(folder) if f.endswith(".csv")]
  if not csvs:
    return None
  # Use newest CSV by modification time
  csvs.sort(key=lambda f: os.path.getmtime(os.path.join(folder, f)), reverse=True)
  return csvs[0]


def process_csv_path(csv_path):
  """
  Process a CSV file at the given path: validate header, then send one email per row.
  Returns (success: bool, message: str, details: list).
  """
  try:
    f = open(csv_path, newline="", encoding="utf-8")
  except FileNotFoundError:
    return False, f"File not found: {csv_path}", []
  except OSError as e:
    return False, str(e), []
  with f:
    first_row = next(csv.reader(f), None)
    if not first_row:
      return False, "CSV is empty. Add header: Business Name,Email,City,Vorname,Stars", []
    fieldnames = [c.strip().lstrip("\ufeff") for c in first_row]
    if "Email" not in fieldnames:
      return False, "CSV must have 'Email' column. Expected: Business Name,Email,City,Vorname,Stars", []
    reader = csv.DictReader(f, fieldnames=fieldnames)
    details = []
    for row in reader:
      email = (row.get("Email") or "").strip()
      if not email:
        continue
      if "@" not in email:
        details.append({"email": email, "ok": False, "error": "Invalid email (no @). Check CSV for newlines inside quoted fields."})
        continue
      try:
        send_email(email, row)
        time.sleep(random.uniform(5, 15))
        details.append({"email": email, "ok": True})
      except Exception as e:
        details.append({"email": email, "ok": False, "error": str(e)})
    return True, f"Processed {len(details)} recipients.", details


def main():
  csv_file = get_csv_file()
  if not csv_file:
    print("No CSV file found. Put a .csv file here or run: python code.py yourfile.csv")
    return
  folder = os.path.dirname(os.path.abspath(__file__)) or "."
  full_path = os.path.join(folder, csv_file) if not os.path.isabs(csv_file) else csv_file
  print(f"Using: {csv_file}\n")
  ok, msg, details = process_csv_path(full_path)
  if not ok:
    print(msg)
    return
  for d in details:
    if d.get("ok"):
      print(f"Sent to {d['email']}")
    else:
      print(f"Failed {d['email']}: {d.get('error', '')}")


if __name__ == "__main__":
  main()
