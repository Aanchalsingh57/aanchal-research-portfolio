#!/usr/bin/env bash
set -euo pipefail
# Versioned, non-destructive upgrades run once per service start, never per request.
# Back up your database before deploying future schema changes.
flask --app wsgi db upgrade
flask --app wsgi seed
exec gunicorn wsgi:app --bind "0.0.0.0:${PORT:-8000}" --workers "${WEB_CONCURRENCY:-1}" --threads 2 --timeout 60 --access-logfile - --error-logfile -
