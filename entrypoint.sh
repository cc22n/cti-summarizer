#!/bin/sh
# Container startup: create all tables, stamp alembic, seed, then run the main command.
set -e

echo "[startup] Creating database tables..."
python -c "
from app.database import Base, get_engine
from app.models import alert, category, ingestion_log, source, summary, trend_prediction, user
Base.metadata.create_all(bind=get_engine())
print('[startup] Tables OK')
"

echo "[startup] Stamping Alembic head..."
alembic stamp head

echo "[startup] Seeding initial data..."
python -c "
try:
    from scripts.setup_db import seed_data
    seed_data()
except Exception as e:
    print('[startup] Seed warning:', e)
"

echo "[startup] Done. Starting: $*"
exec "$@"
