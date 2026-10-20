from pathlib import Path

from alembic.config import Config
from backend.app.db.models import Base
from sqlalchemy import create_engine, inspect

from alembic import command


def test_alembic_migrations_lifecycle_and_schema_parity(tmp_path):
    """
    Verifies that Alembic migration upgrade head and downgrade base work cleanly
    on a fresh SQLite file, and that the migrated schema strictly matches
    the SQLAlchemy Base.metadata models for all 10 PRD Section 9 tables.
    """
    db_file = tmp_path / "fresh_migration_test.db"
    db_url = f"sqlite:///{db_file.as_posix()}"

    repo_root = Path(__file__).resolve().parent.parent.parent.parent
    alembic_ini_path = repo_root / "alembic.ini"
    alembic_cfg = Config(str(alembic_ini_path))
    alembic_cfg.set_main_option("sqlalchemy.url", db_url)

    # 1. Upgrade to head
    command.upgrade(alembic_cfg, "head")

    # 2. Inspect migrated database
    engine = create_engine(db_url)
    inspector = inspect(engine)
    migrated_tables = set(inspector.get_table_names())

    # Check Alembic version table exists plus all 10 PRD tables
    expected_tables = {
        "model_versions",
        "assessment_runs",
        "stress_runs",
        "portfolio_definitions",
        "market_data_manifests",
        "market_risk_runs",
        "var_validation_runs",
        "drift_runs",
        "monitoring_alerts",
        "audit_events",
    }

    assert expected_tables.issubset(migrated_tables), (
        f"Missing tables in migration: {expected_tables - migrated_tables}"
    )

    # 3. Compare table columns against SQLAlchemy model metadata
    for table_name, model_table in Base.metadata.tables.items():
        assert table_name in migrated_tables, f"Model table {table_name} not found in migrated DB"
        migrated_columns = {col["name"] for col in inspector.get_columns(table_name)}
        model_columns = {col.name for col in model_table.columns}
        assert model_columns == migrated_columns, (
            f"Column mismatch in {table_name}: expected {model_columns}, found {migrated_columns}"
        )

    engine.dispose()

    # 4. Downgrade to base
    command.downgrade(alembic_cfg, "base")

    engine = create_engine(db_url)
    inspector = inspect(engine)
    tables_after_downgrade = set(inspector.get_table_names())
    # Only alembic_version (or empty) should remain, all 10 tables dropped
    assert expected_tables.intersection(tables_after_downgrade) == set(), (
        f"Tables remained after downgrade: {expected_tables.intersection(tables_after_downgrade)}"
    )
    engine.dispose()

    # 5. Re-upgrade to head works cleanly
    command.upgrade(alembic_cfg, "head")
    engine = create_engine(db_url)
    inspector = inspect(engine)
    assert expected_tables.issubset(set(inspector.get_table_names()))
    engine.dispose()
