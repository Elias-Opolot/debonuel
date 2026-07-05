# DEBONUEL — Streamlit Setup Guide

## What you need (all free)
- GitHub account ✅ (you have one)
- Google account ✅ (you have one)
- Streamlit account (sign up free at streamlit.io)

---

## STEP 1 — Upload files to GitHub

1. Go to github.com/Elias-Opolot/debonuel (your existing repo)
2. Upload ALL these files:
   - app.py
   - sheets.py
   - requirements.txt
   - .streamlit/config.toml
3. Commit changes

---

## STEP 2 — Create Google Service Account

This is how Streamlit connects to your Google Sheet securely.

1. Go to console.cloud.google.com
2. Select your DEBONUEL project (or create new one)
3. Search "Google Sheets API" → Enable it
4. Search "Google Drive API" → Enable it
5. Go to "Credentials" → "Create Credentials" → "Service Account"
6. Name it: debonuel-sheets
7. Click Done (skip optional steps)
8. Click on the new service account email
9. Go to "Keys" tab → "Add Key" → "Create new key" → JSON
10. A JSON file downloads to your computer — KEEP THIS SAFE

---

## STEP 3 — Share your Google Sheet with the service account

1. Open the JSON file you downloaded (use Notepad)
2. Find the line that says "client_email" — copy that email address
   (looks like: debonuel-sheets@your-project.iam.gserviceaccount.com)
3. Open your Google Sheet (DEBONUEL Sales Data)
4. Click Share (top right)
5. Paste that email address
6. Set role to "Editor"
7. Click Share

---

## STEP 4 — Deploy on Streamlit

1. Go to streamlit.io → Sign up with GitHub
2. Click "New app"
3. Select your GitHub repo: Elias-Opolot/debonuel
4. Main file: app.py
5. Click "Advanced settings" → "Secrets"
6. Open the JSON file you downloaded in Step 2
7. Fill in the secrets_template.toml with values from the JSON
8. Paste the filled template into the Secrets box
9. Click Deploy

Your app will be live at:
https://debonuel.streamlit.app

---

## What each file does

- app.py — the main app with all screens
- sheets.py — handles reading/writing to Google Sheets
- requirements.txt — libraries Streamlit needs to install
- .streamlit/config.toml — dark theme and settings

---

## Data Storage

All data saves directly to your Google Sheet in real time:
- Products tab — your stock
- Sales tab — every sale header
- Sale_Items tab — every line item sold
- Suppliers tab — your suppliers

You can open the sheet anytime at sheets.google.com to see everything.
