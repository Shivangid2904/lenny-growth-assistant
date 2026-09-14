#!/bin/sh
set -e

echo "Applying Alembic database migrations..."
alembic upgrade head

echo "Starting Lenny Growth Assistant backend server on 0.0.0.0:8000..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
