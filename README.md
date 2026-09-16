# SYLRIX.FIT

SYLRIX.FIT is a member-focused training system with adaptive workouts, workout logging, nutrition tracking, progress history, an exercise library, and a member-aware Coach.

## Local development

```bash
python3 -m pip install -r requirements.txt
python3 app.py
```

Open `http://127.0.0.1:5001`. To use another local port, run `PORT=5002 python3 app.py`. Stop the server with `Ctrl-C` and start it again after Python changes.

Run the checks with:

```bash
python3 -m unittest discover -s tests -q
```

## Private-beta deployment

Production needs a proper WSGI server and a persistent volume. Copy `.env.example` to your deployment platform's environment configuration, set real secrets there, then use:

```bash
gunicorn --workers 2 --threads 4 --timeout 60 --bind 0.0.0.0:$PORT wsgi:app
```

`SYLRIX_ENV=production` requires a real `SYLRIX_SECRET_KEY`; `python app.py` intentionally refuses to run in production mode. Use `GET /health` for the platform health check.

The full beta runbook—including SQLite limits, persistence, safe schema behavior, backups, invite-only beta mode, and the public-launch gap list—is in [docs/private_beta_deployment.md](docs/private_beta_deployment.md).

## Live-data policy

Do not scrape creators or publish their claims as facts. Connect an official nutrition provider, keep the provider and last-sync timestamp with every food record, and route research updates through a qualified staff review queue. The app's `data_sources.py` is the single place to register those sources visibly.
