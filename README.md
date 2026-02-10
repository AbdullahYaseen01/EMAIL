# Email campaign

Send personalized emails from a CSV (Business Name, Email, City, Vorname, Stars). Step-by-step web UI: upload CSV → preview → send.

## Setup

1. **Clone and install**
   ```bash
   pip install -r requirements.txt
   ```

2. **Set email credentials** (required)
   - **MAIL_USER** – sending email address (e.g. from Hostinger or Gmail)
   - **MAIL_PASS** – password for that account (or [Gmail App Password](https://myaccount.google.com/apppasswords) if using Gmail)

   **Local:** create a `.env` file or set in your shell:
   ```bash
   set MAIL_USER=your@email.com
   set MAIL_PASS=yourpassword
   ```
   (On Mac/Linux use `export` instead of `set`.)

3. **Run**
   ```bash
   python app.py
   ```
   Open http://127.0.0.1:5000

## Deploy (Vercel)

See [DEPLOY.md](DEPLOY.md). Add **MAIL_USER** and **MAIL_PASS** in Vercel → Settings → Environment Variables.

## CLI (no web)

```bash
python mailer.py              # uses newest .csv in folder
python mailer.py yourfile.csv
```
