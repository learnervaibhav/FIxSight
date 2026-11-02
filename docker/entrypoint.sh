#!/bin/sh
# Backend container start-up: wait for Postgres, migrate, ensure models + seed data, serve.
set -e

echo "[fixsight] waiting for database..."
python - <<'PY'
import os, sys, time
from sqlalchemy import create_engine, text

url = os.environ["DATABASE_URL"]
for attempt in range(60):
    try:
        with create_engine(url).connect() as conn:
            conn.execute(text("SELECT 1"))
        print("[fixsight] database is ready")
        sys.exit(0)
    except Exception as exc:  # noqa: BLE001
        print(f"[fixsight] database not ready ({exc.__class__.__name__}), retry {attempt + 1}/60")
        time.sleep(2)
sys.exit("[fixsight] database never became ready")
PY

echo "[fixsight] applying migrations..."
alembic upgrade head

if [ ! -f ml_models/xgb_fault_classifier.json ]; then
    echo "[fixsight] ml_models/ missing: generating a small dataset and training models (one-off, a few minutes)..."
    python scripts/generate_dataset.py --out dataset --vehicles 8 --days 20 --sample-every 2
    python scripts/train_model.py --dataset dataset --out ml_models --sample 0.5 --no-eval
fi

echo "[fixsight] seeding demo data (idempotent)..."
python scripts/bootstrap.py

echo "[fixsight] starting API on :8000"
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --proxy-headers
