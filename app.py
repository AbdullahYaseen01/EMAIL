import os
import csv
import tempfile
from flask import Flask, request, redirect, url_for, render_template, jsonify

import mailer

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-change-in-production")


def csv_preview(path, max_rows=10):
    """Return (headers, rows, total_count) for preview. Does not send anything."""
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        first = next(reader, None)
        if not first:
            return None, [], 0
        headers = [c.strip().lstrip("\ufeff") for c in first]
        rows = []
        for i, row in enumerate(reader):
            if i >= max_rows:
                extra = sum(1 for _ in reader)
                return headers, rows, max_rows + extra
            rows.append(dict(zip(headers, (c.strip() for c in row))))
        return headers, rows, len(rows)


@app.route("/")
def index():
    """Single page: step 2 and 3 are filled by JS (serverless-friendly, no session)."""
    return render_template("index.html")


@app.route("/upload", methods=["POST"])
def upload():
    """Accept CSV, return preview as JSON. No server-side storage (for Vercel/Netlify)."""
    if "csv_file" not in request.files:
        return jsonify({"ok": False, "error": "No file"}), 400
    f = request.files["csv_file"]
    if not f or f.filename == "" or not f.filename.lower().endswith(".csv"):
        return jsonify({"ok": False, "error": "Please choose a .csv file"}), 400
    fd, path = tempfile.mkstemp(suffix=".csv")
    try:
        f.save(path)
        headers, rows, total = csv_preview(path)
        if not headers:
            return jsonify({"ok": False, "error": "CSV is empty or invalid"}), 400
        return jsonify({
            "ok": True,
            "filename": f.filename,
            "headers": headers,
            "rows": rows,
            "total": total,
        })
    finally:
        try:
            os.close(fd)
            os.unlink(path)
        except OSError:
            pass


@app.route("/send", methods=["POST"])
def send():
    """Accept CSV file in request, process and send emails. Stateless for serverless."""
    if "csv_file" not in request.files:
        return jsonify({"ok": False, "message": "No file uploaded.", "details": []}), 400
    f = request.files["csv_file"]
    if not f or f.filename == "":
        return jsonify({"ok": False, "message": "No file selected.", "details": []}), 400
    mail_user = (request.form.get("mail_user") or "").strip()
    mail_pass = (request.form.get("mail_pass") or "").strip()
    fd, path = tempfile.mkstemp(suffix=".csv")
    try:
        f.save(path)
        ok, message, details = mailer.process_csv_path(path, mail_user=mail_user, mail_pass=mail_pass)
        return jsonify({"ok": ok, "message": message, "details": details})
    finally:
        try:
            os.close(fd)
            os.unlink(path)
        except OSError:
            pass


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
