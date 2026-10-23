"""First-run preparation for the container (idempotent).

1. Apply Alembic migrations and register the champion credit model (init_db).
2. Seed the instrument master and daily prices when the database is new.
3. Rebuild the RAG index only if the image does not already carry one.
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.app.core.config import settings
from backend.app.db.init_db import init_db
from backend.app.db.models import DailyPrice, Instrument, ModelVersion
from backend.app.db.session import SessionLocal


def main() -> None:
    init_db()

    db = SessionLocal()
    try:
        active_model = db.query(ModelVersion).filter(ModelVersion.status == "active").first()
        needs_market_seed = db.query(Instrument).count() == 0 or db.query(DailyPrice).count() == 0
    finally:
        db.close()

    if active_model is None:
        print("WARNING: no active credit model is registered; /api/v1/credit/* will not work.", flush=True)
    else:
        print(f"Active credit model: {active_model.version}", flush=True)

    if needs_market_seed:
        print("New database: seeding instrument master and price history (one-off)...", flush=True)
        from scripts.build_instrument_master import main as seed_market

        seed_market()

    if not (settings.ARTIFACTS_DIR / "vector_index" / "index_metadata.json").exists():
        print("RAG index missing: rebuilding from the knowledge corpus...", flush=True)
        from scripts.build_index import build_index

        build_index()


if __name__ == "__main__":
    main()
