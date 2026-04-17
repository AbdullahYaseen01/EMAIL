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
DEFAULT_SMTP_HOST = "smtp.hostinger.com"
DEFAULT_SMTP_PORT = 465
DEFAULT_IMAP_HOST = "imap.hostinger.com"
DEFAULT_IMAP_PORT = 993
MAIL_USER = os.environ.get("MAIL_USER") or os.environ.get("USR", "")
MAIL_PASS = os.environ.get("MAIL_PASS") or os.environ.get("PASS", "")

MAIL_PROVIDERS = {
  "gmx.ch": {"smtp_host": "mail.gmx.net", "smtp_port": 465, "imap_host": "imap.gmx.net", "imap_port": 993},
  "gmx.com": {"smtp_host": "mail.gmx.net", "smtp_port": 465, "imap_host": "imap.gmx.net", "imap_port": 993},
}


def _resolve_mail_servers(mail_user):
  """
  Resolve SMTP/IMAP settings from sender domain.
  Falls back to Hostinger defaults when domain is unknown.
  """
  smtp_host = os.environ.get("SMTP_HOST", DEFAULT_SMTP_HOST)
  smtp_port = int(os.environ.get("SMTP_PORT", str(DEFAULT_SMTP_PORT)))
  imap_host = os.environ.get("IMAP_HOST", DEFAULT_IMAP_HOST)
  imap_port = int(os.environ.get("IMAP_PORT", str(DEFAULT_IMAP_PORT)))

  domain = ""
  if mail_user and "@" in mail_user:
    domain = mail_user.rsplit("@", 1)[1].strip().lower()
  provider = MAIL_PROVIDERS.get(domain)
  if provider and "SMTP_HOST" not in os.environ and "IMAP_HOST" not in os.environ:
    smtp_host = provider["smtp_host"]
    smtp_port = provider["smtp_port"]
    imap_host = provider["imap_host"]
    imap_port = provider["imap_port"]
  return smtp_host, smtp_port, imap_host, imap_port

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

HEADER_ALIASES = {
  "email": ("email", "emails_found", "mail", "e-mail", "email_address"),
  "business_name": ("business name", "business", "company", "company_name", "niche"),
  "first_name": ("vorname", "first_name", "firstname", "name"),
  "city": ("city", "ort", "location"),
  "stars": ("stars", "reviewscount", "reviews_count", "reviews", "google_reviews"),
  "positive_observation": ("positive observation", "positive_observation", "observation"),
}


def _normalize_key(value):
  if value is None:
    return ""
  return "".join(ch for ch in str(value).strip().lower() if ch.isalnum())


def _build_header_map(fieldnames):
  """
  Build canonical -> actual header mapping from CSV headers.
  """
  normalized_lookup = {_normalize_key(name): name for name in fieldnames if name}
  mapped = {}
  for canonical, aliases in HEADER_ALIASES.items():
    for alias in aliases:
      actual = normalized_lookup.get(_normalize_key(alias))
      if actual:
        mapped[canonical] = actual
        break
  # Heuristic fallback: tolerate abbreviated/custom header names
  for name in fieldnames:
    normalized = _normalize_key(name)
    if not normalized:
      continue
    if "email" in normalized and "email" not in mapped:
      mapped["email"] = name
    if ("review" in normalized or "star" in normalized) and "stars" not in mapped:
      mapped["stars"] = name
    if "city" in normalized and "city" not in mapped:
      mapped["city"] = name
    if (("firstname" in normalized) or ("vorname" in normalized) or ("firstnam" in normalized)) and "first_name" not in mapped:
      mapped["first_name"] = name
    if (("business" in normalized) or ("company" in normalized) or ("niche" in normalized)) and "business_name" not in mapped:
      mapped["business_name"] = name
  return mapped


def _get_value(row, header_map, canonical_name, default=""):
  actual_header = header_map.get(canonical_name)
  if not actual_header:
    return default
  return row.get(actual_header, default)


def _sanitize_header(value):
  """Remove CR/LF from a string so it is safe for email headers (Subject, To, etc.)."""
  if value is None:
    return ""
  s = str(value).replace("\r\n", " ").replace("\r", " ").replace("\n", " ").strip()
  return " ".join(s.split())  # collapse multiple spaces


def save_to_sent_folder(msg, mail_user, mail_pass):
  """Append a copy of the message to Hostinger Sent folder so it shows in webmail."""
  try:
    smtp_host, smtp_port, imap_host, imap_port = _resolve_mail_servers(mail_user)
    if "Date" not in msg:
      msg["Date"] = formatdate(localtime=True)
    raw = msg.as_bytes()
    raw = raw.replace(b"\n", b"\r\n")
    date_time = imaplib.Time2Internaldate(time.time())
    with imaplib.IMAP4_SSL(imap_host, imap_port) as imap:
      imap.login(mail_user, mail_pass)
      imap.append("INBOX.Sent", "\\Seen", date_time, raw)
  except Exception as e:
    print(f" (copy to Sent folder skipped: {e})")


def send_email(to_email, row, mail_user, mail_pass):
  # Normalize and sanitize so headers never contain newlines/carriage returns
  smtp_host, smtp_port, imap_host, imap_port = _resolve_mail_servers(mail_user)
  header_map = row.get("__header_map__", {})
  business_name = _sanitize_header(_get_value(row, header_map, "business_name"))
  first_name = _sanitize_header(_get_value(row, header_map, "first_name")) or "there"
  city = _sanitize_header(_get_value(row, header_map, "city"))
  reviews_count = _sanitize_header(_get_value(row, header_map, "stars"))
  positive_observation = _sanitize_header(_get_value(row, header_map, "positive_observation")) or "your business"
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
  msg["From"] = mail_user
  msg["To"] = to_email
  msg.set_content(body)

  with smtplib.SMTP_SSL(smtp_host, smtp_port) as smtp:
    smtp.login(mail_user, mail_pass)
    smtp.send_message(msg)
  save_to_sent_folder(msg, mail_user, mail_pass)
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


def process_csv_path(csv_path, mail_user=None, mail_pass=None):
  """
  Process a CSV file at the given path: validate header, then send one email per row.
  Returns (success: bool, message: str, details: list).
  """
  active_mail_user = (mail_user or MAIL_USER or "").strip()
  active_mail_pass = (mail_pass or MAIL_PASS or "").strip()
  if not active_mail_user or not active_mail_pass:
    return False, (
      "Email credentials missing. Set MAIL_USER and MAIL_PASS, then restart the app."
    ), []

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
    header_map = _build_header_map(fieldnames)
    if "email" not in header_map:
      return False, (
        "CSV must include an email column (for example: Email or emails_found). "
        "Detected columns: " + ",".join(fieldnames)
      ), []
    reader = csv.DictReader(f, fieldnames=fieldnames)
    details = []
    for row in reader:
      row["__header_map__"] = header_map
      email = (_get_value(row, header_map, "email") or "").strip()
      if not email:
        continue
      if "@" not in email:
        details.append({"email": email, "ok": False, "error": "Invalid email (no @). Check CSV for newlines inside quoted fields."})
        continue
      try:
        send_email(email, row, active_mail_user, active_mail_pass)
        time.sleep(random.uniform(5, 15))
        details.append({"email": email, "ok": True})
      except smtplib.SMTPAuthenticationError:
        details.append({
          "email": email,
          "ok": False,
          "error": (
            "SMTP authentication failed (535). Check MAIL_USER/MAIL_PASS and SMTP provider settings."
          ),
        })
        return False, (
          "SMTP authentication failed (535). "
          "Fix MAIL_USER/MAIL_PASS (and SMTP provider if needed), then try again."
        ), details
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
