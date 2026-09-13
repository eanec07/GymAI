# GymAI

GymAI is a starter web app for a gym's member workout notebook. It includes:

- goal-, experience-, schedule-, and equipment-aware workout splits
- a public `/daily` workout page that can be placed behind a gym QR code
- lift logging, calorie/protein targets, and progress-photo uploads
- a realistic physique-inspiration planner
- a transparent source-status page for future nutrition and research integrations

## Run locally

```bash
python3 -m pip install -r requirements.txt
python3 app.py
```

Open `http://127.0.0.1:5000` in a browser. The public QR destination is `http://127.0.0.1:5000/daily` locally; use your deployed domain plus `/daily` when you create the gym QR code.

## Before deployment

Set a strong, private `GYMAI_SECRET_KEY`. SQLite and local uploaded images are appropriate for local development only. A real gym deployment should use a managed database, private object storage for photos, real user authentication, backups, and a privacy policy.

## Live-data policy

Do not scrape creators or publish their claims as facts. Connect an official nutrition provider, keep the provider and last-sync timestamp with every food record, and route research updates through a qualified staff review queue. The app's `data_sources.py` is the single place to register those sources visibly.
