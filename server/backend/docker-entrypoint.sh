#!/bin/sh
# ==============================================================================
# LABORA Production Docker Entrypoint Script
# Handles database connection readiness check, automatic migration, and static collection
# ==============================================================================
set -e

# Wait for PostgreSQL database if configured
if [ -n "$POSTGRES_HOST" ]; then
  echo "[LABORA-ENTRYPOINT] Checking database connectivity at ${POSTGRES_HOST}:${POSTGRES_PORT:-5432}..."
  MAX_RETRIES=30
  COUNT=0
  while ! nc -z "$POSTGRES_HOST" "${POSTGRES_PORT:-5432}"; do
    COUNT=$((COUNT + 1))
    if [ "$COUNT" -ge "$MAX_RETRIES" ]; then
      echo "[LABORA-ENTRYPOINT] ERROR: Timed out waiting for database."
      exit 1
    fi
    sleep 1
  done
  echo "[LABORA-ENTRYPOINT] Database is reachable."
fi

# If starting Gunicorn web server, apply migrations and collect static assets
if [ "$1" = "gunicorn" ]; then
  echo "[LABORA-ENTRYPOINT] Running database migrations..."
  python manage.py migrate --noinput
  echo "[LABORA-ENTRYPOINT] Collecting static files..."
  python manage.py collectstatic --noinput || true
fi

echo "[LABORA-ENTRYPOINT] Executing command: $@"
exec "$@"
