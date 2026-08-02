#!/bin/sh
set -eu

python - <<'PY'
import time
from sqlalchemy import create_engine, text
from src.app.settings import get_settings

engine = create_engine(get_settings().database_url, pool_pre_ping=True)
for attempt in range(30):
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        break
    except Exception:
        if attempt == 29:
            raise
        time.sleep(1)
engine.dispose()
PY

alembic upgrade head

if [ "${SEED_FOODS_ON_START:-false}" = "true" ]; then
    python scripts/seed_food_catalog.py
fi

exec "$@"
