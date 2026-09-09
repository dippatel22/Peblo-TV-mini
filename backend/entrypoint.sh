#!/bin/sh
set -eu

# The postgres image only creates POSTGRES_DB during first initialization.
# Existing volumes may therefore contain the server but not the application DB.
# Create the application database idempotently before running migrations.
export PGPASSWORD="${POSTGRES_PASSWORD:-peblo}"

until pg_isready -h db -U "${POSTGRES_USER:-peblo}" -d postgres >/dev/null 2>&1; do
  sleep 1
done

if ! psql -h db -U "${POSTGRES_USER:-peblo}" -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname = 'peblo'" | grep -q 1; then
  psql -h db -U "${POSTGRES_USER:-peblo}" -d postgres -v ON_ERROR_STOP=1 -c 'CREATE DATABASE peblo'
fi

alembic upgrade head
python -m app.seed
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
