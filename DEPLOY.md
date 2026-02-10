# Deploy Email Campaign App

## Vercel (recommended)

Vercel supports Flask with zero config. Your `app.py` is auto-detected.

### Steps

1. **Push your code to GitHub** (if not already).

2. **Import on Vercel**
   - Go to [vercel.com/new](https://vercel.com/new)
   - Import your repository
   - Root directory: leave as is (or `.`)

3. **Set environment variables** (required for sending email)
   - In the Vercel project: **Settings → Environment Variables**
   - Add:
     - `MAIL_USER` = your sending email (e.g. `afrem@agency.yarbug-media.ch`)
     - `MAIL_PASS` = your email password
   - Optional: `SECRET_KEY` for session signing (Vercel can generate one)

4. **Deploy**
   - Click Deploy. Vercel will run `pip install -r requirements.txt` and deploy the Flask app.

5. **Use the app**
   - Open the provided URL (e.g. `https://your-project.vercel.app`).

### Local test with Vercel CLI

```bash
pip install -r requirements.txt
vercel dev
```

---

## Netlify

Netlify Functions currently support **TypeScript, JavaScript, and Go** only. They do **not** run Python/Flask as serverless functions.

**Options:**

1. **Use Vercel** for this app (easiest).
2. **Use another host for the backend** (e.g. [Render](https://render.com), [Railway](https://railway.app), [Fly.io](https://fly.io)) and point Netlify to it via redirects or a separate frontend.
3. **Netlify + external API**: Build a static frontend on Netlify that calls your Flask API hosted elsewhere.

For a single Flask app with file upload and email sending, **Vercel is the simplest choice**.
