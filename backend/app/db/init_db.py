from pathlib import Path

from alembic.config import Config
from scripts.register_models import register_models
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from alembic import command
from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.db.models import ModelVersion


def init_db(database_url: str | None = None) -> None:
    """
    Applies Alembic migrations to head.
    Explicitly decoupled from Base.metadata.create_all to ensure all DDL
    is strictly version-controlled via Alembic migrations.
    """
    logger.info("Applying database migrations via Alembic...")
    # Repo root is 3 levels up from backend/app/db
    alembic_ini_path = Path(__file__).resolve().parent.parent.parent.parent / "alembic.ini"
    alembic_cfg = Config(str(alembic_ini_path))

    target_url = database_url or settings.DATABASE_URL
    alembic_cfg.set_main_option("sqlalchemy.url", target_url)

    command.upgrade(alembic_cfg, "head")
    logger.info("Database schema migrated to head successfully via Alembic.")

    # Auto-register champion model if none is active (ensures fresh clone / Docker runs immediately)
    try:
        connect_args = {"check_same_thread": False} if target_url.startswith("sqlite") else {}
        engine = create_engine(target_url, connect_args=connect_args)
        Session = sessionmaker(bind=engine)
        session = Session()
        try:
            active_model = session.query(ModelVersion).filter(ModelVersion.status == "active").first()
            if not active_model:
                logger.info("No active model found in database. Auto-registering champion models...")
                register_models(db_url=target_url)
                logger.info("Champion model auto-registered successfully.")
        finally:
            session.close()
            engine.dispose()
    except (OSError, ValueError, RuntimeError, KeyError) as e:
        logger.warning("Could not auto-register champion models: %s", e)


if __name__ == "__main__":
    init_db()
