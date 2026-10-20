import json
from pathlib import Path

import pytest
from backend.app.db.models import Base, ModelVersion
from scripts.register_models import register_models
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent


def test_register_models_with_custom_metrics(tmp_path):
    """
    Assert that registering a model from a temporary copy of model_comparison.json
    with custom modified numbers successfully writes those new numbers to the database,
    not any hardcoded or old values.
    """
    db_file = tmp_path / "custom_reg_test.db"
    db_url = f"sqlite:///{db_file.as_posix()}"

    engine = create_engine(db_url, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)

    # Read original metrics and alter with distinct custom numbers
    orig_metrics_path = REPO_ROOT / "artifacts" / "evaluation" / "model_comparison.json"
    with open(orig_metrics_path, "r", encoding="utf-8") as f:
        metrics_data = json.load(f)

    custom_metrics_data = dict(metrics_data)
    custom_metrics_data["xgboost"] = {
        "roc_auc": 0.9142,
        "pr_auc": 0.8351,
        "f1_score": 0.7788,
        "brier_score": 0.0892,
        "decision_threshold": 0.42,
        "risk_band_cutoffs": {"low": 0.05, "moderate": 0.15, "elevated": 0.35}
    }

    temp_metrics_file = tmp_path / "temp_comparison.json"
    with open(temp_metrics_file, "w", encoding="utf-8") as f:
        json.dump(custom_metrics_data, f, indent=2)

    # Run register_models pointing to temp metrics file and isolated test database
    artifacts_dir = REPO_ROOT / "artifacts" / "models"
    result = register_models(
        metrics_path=temp_metrics_file,
        artifacts_dir=artifacts_dir,
        db_url=db_url
    )
    assert result == 0

    # Verify database contents
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        registered = session.query(ModelVersion).filter(ModelVersion.version == "credit_xgboost_v1").first()
        assert registered is not None
        assert registered.status == "active"
        assert registered.model_name == "xgboost"

        parsed_metrics = json.loads(registered.metrics_json)
        assert parsed_metrics["roc_auc"] == 0.9142, f"Expected 0.9142, got {parsed_metrics['roc_auc']}"
        assert parsed_metrics["pr_auc"] == 0.8351, f"Expected 0.8351, got {parsed_metrics['pr_auc']}"
        assert parsed_metrics["decision_threshold"] == 0.42, f"Expected 0.42, got {parsed_metrics['decision_threshold']}"
        assert parsed_metrics["risk_band_cutoffs"]["low"] == 0.05
    finally:
        session.close()
        engine.dispose()


def test_register_models_fails_if_artifact_missing(tmp_path):
    """
    Assert that if a required artifact file is missing, register_models
    aborts with an error and commits no rows to the database.
    """
    db_file = tmp_path / "fail_reg_test.db"
    db_url = f"sqlite:///{db_file.as_posix()}"

    engine = create_engine(db_url, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)

    orig_metrics_path = REPO_ROOT / "artifacts" / "evaluation" / "model_comparison.json"
    empty_artifacts_dir = tmp_path / "empty_models"
    empty_artifacts_dir.mkdir(parents=True, exist_ok=True)

    with pytest.raises(FileNotFoundError, match="Model artifact file does not exist"):
        register_models(
            metrics_path=orig_metrics_path,
            artifacts_dir=empty_artifacts_dir,
            db_url=db_url
        )

    # Ensure nothing was written
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        count = session.query(ModelVersion).count()
        assert count == 0
    finally:
        session.close()
        engine.dispose()
