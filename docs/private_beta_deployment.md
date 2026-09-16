# SYLRIX private-beta deployment

SYLRIX is ready for a small, managed private beta—not an unrestricted public launch.

## Required production configuration

Set these values in the deployment platform's secret/environment manager; do not place real values in Git:

- `SYLRIX_ENV=production`
- `SYLRIX_SECRET_KEY` — a unique high-entropy secret
- `SYLRIX_DATABASE_PATH` — an absolute path on a persistent volume
- `SYLRIX_COOKIE_SECURE=1`
- `SYLRIX_CSRF_ENABLED=1`

Set `OPENAI_API_KEY` only when using the hosted Coach provider. The application can use its local fallback where configured.

To restrict new accounts during beta, set `SYLRIX_BETA_MODE=1` and a non-empty `SYLRIX_BETA_INVITE_CODE`. Keep that code in the platform's secret manager.

## Start command

Install dependencies, then run:

```bash
gunicorn --workers 2 --threads 4 --timeout 60 --bind 0.0.0.0:$PORT wsgi:app
```

Do not run `python app.py` in production; it intentionally refuses production mode. For local development, use `python3 app.py`.

## SQLite and storage

SQLite is suitable only for a small beta with a persistent disk and modest concurrent writes. Mount the same persistent volume for `SYLRIX_DATABASE_PATH` and the `uploads/` directory across restarts. Do not deploy to ephemeral filesystem storage.

Run a small number of Gunicorn workers (the provided command uses two). SQLite locking and single-node storage mean this architecture must be replaced with a managed multi-user database before a larger public launch or horizontal scaling.

`setup_database()` only creates missing tables and adds missing columns; it does not reset member data. Review and back up the database before any future migration that changes or removes schema.

## Backups and recovery

Back up the SQLite database and `uploads/` directory together at least daily, retain multiple dated copies, and test a restore on a separate environment. Prefer SQLite's backup command while the app is live:

```bash
sqlite3 "$SYLRIX_DATABASE_PATH" ".backup '/secure/backup/location/sylrix-YYYY-MM-DD.db'"
```

Restore only during a planned maintenance window, after preserving the current database copy. Progress photos are separate files and must be restored alongside their database records.

## Operational checks

- Configure the platform health check to request `GET /health`.
- Terminate TLS at the host or proxy; secure cookies require HTTPS.
- Watch server logs for unexpected errors, database failures, and Coach provider failures. Never log secrets, passwords, cookies, or complete member data.
- Keep environment secrets out of terminal output, screenshots, and support tickets.

## Before a public launch

Add durable rate limiting, email verification and account recovery, formal privacy/terms review, monitored automated backups, malware scanning/object storage for uploads, a production database migration plan, and load/security testing.
