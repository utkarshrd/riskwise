#!/usr/bin/env python3
"""
scripts/register_models.py

Registers machine learning models into RiskWise's model_versions table.
Reads artifacts/evaluation/model_comparison.json and model artifact files,
computes real SHA-256 checksums, and atomically writes model_versions rows.
Enforces strict provenance: if an artifact or required metric is missing,
it fails immediately with a clear error and writes nothing.
"""

import argparse
import hashlib
import json
import os
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app.core.config import settings
from backend.app.db.models import AuditEvent, ModelVersion


def compute_sha256(filepath: Path) -> str:
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def register_models(
    metrics_path: Path | None = None,
    artifacts_dir: Path | None = None,
    db_url: str | None = None
) -> int:
    metrics_file = metrics_path or (REPO_ROOT / "artifacts" / "evaluation" / "model_comparison.json")
    models_dir = artifacts_dir or (REPO_ROOT / "artifacts" / "models")
    target_db_url = db_url or settings.DATABASE_URL

    if not metrics_file.exists():
        raise FileNotFoundError(f"Model comparison metrics file not found: {metrics_file}")

    with open(metrics_file, "r", encoding="utf-8") as f:
        comparison_results = json.load(f)

    if not comparison_results or not isinstance(comparison_results, dict):
        raise ValueError(f"Invalid or empty comparison results in {metrics_file}")

    # Determine champion deployable model (excluding leakage study experiments)
    deployable = {
        k: v for k, v in comparison_results.items()
        if not k.endswith("_with_credit_score") and isinstance(v, dict) and "roc_auc" in v
    }
    best_model_name = max(deployable, key=lambda k: deployable[k].get("roc_auc", 0.0))
    champion_metrics = deployable[best_model_name]

    # Required metrics verification
    required_keys = ["roc_auc", "decision_threshold", "risk_band_cutoffs"]
    for key in required_keys:
        if key not in champion_metrics:
            raise ValueError(f"Missing required metric '{key}' for model '{best_model_name}' in {metrics_file}")

    version_tag = f"credit_{best_model_name}_v1"
    model_artifact = models_dir / f"{version_tag}.joblib"
    prep_artifact = models_dir / f"{version_tag}_preprocessor.joblib"

    if not model_artifact.exists():
        raise FileNotFoundError(f"Model artifact file does not exist: {model_artifact}")
    if not prep_artifact.exists():
        raise FileNotFoundError(f"Preprocessor artifact file does not exist: {prep_artifact}")

    model_checksum = compute_sha256(model_artifact)

    # Relative paths for portable DB storage
    rel_model_path = os.path.relpath(model_artifact, REPO_ROOT).replace("\\", "/")
    rel_prep_path = os.path.relpath(prep_artifact, REPO_ROOT).replace("\\", "/")

    connect_args = {"check_same_thread": False} if target_db_url.startswith("sqlite") else {}
    engine = create_engine(target_db_url, connect_args=connect_args)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        now_dt = datetime.now(UTC)

        # Deactivate previous active models
        session.query(ModelVersion).filter(ModelVersion.status == "active").update({"status": "archived"})

        existing = session.query(ModelVersion).filter(ModelVersion.version == version_tag).first()
        if existing:
            existing.metrics_json = json.dumps(champion_metrics)
            existing.status = "active"
            existing.checksum = model_checksum
            existing.preprocessing_artifact = rel_prep_path
            existing.model_artifact = rel_model_path
            existing.trained_at = now_dt
            model_id = existing.id
            print(f"Updated active champion ModelVersion '{version_tag}' (ID: {model_id})")
        else:
            model_id = str(uuid.uuid4())
            db_model = ModelVersion(
                id=model_id,
                model_name=best_model_name,
                version=version_tag,
                dataset_id="Indian_Banking_CIBIL_Merged_2026",
                feature_schema_version="v2.0_indian_credit",
                preprocessing_artifact=rel_prep_path,
                model_artifact=rel_model_path,
                metrics_json=json.dumps(champion_metrics),
                status="active",
                checksum=model_checksum,
                trained_at=now_dt
            )
            session.add(db_model)
            print(f"Registered new active champion ModelVersion '{version_tag}' (ID: {model_id})")

        # Record audit event
        audit = AuditEvent(
            id=str(uuid.uuid4()),
            actor_type="script",
            action="MODEL_REGISTRATION",
            target_type="model_version",
            target_id=model_id,
            details_json=json.dumps({
                "model_name": best_model_name,
                "version": version_tag,
                "roc_auc": champion_metrics.get("roc_auc"),
                "decision_threshold": champion_metrics.get("decision_threshold"),
                "checksum": model_checksum
            }),
            created_at=now_dt
        )
        session.add(audit)
        session.commit()
        print(f"Successfully committed model registration for '{version_tag}' (SHA-256: {model_checksum[:12]}...).")
        return 0
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
        engine.dispose()


def main():
    parser = argparse.ArgumentParser(description="Register verified ML models into RiskWise database")
    parser.add_argument("--metrics", type=Path, default=None, help="Path to model_comparison.json")
    parser.add_argument("--artifacts", type=Path, default=None, help="Directory containing model joblib artifacts")
    parser.add_argument("--db-url", type=str, default=None, help="Database connection URL")
    args = parser.parse_args()

    try:
        sys.exit(register_models(args.metrics, args.artifacts, args.db_url))
    except Exception as e:
        print(f"ERROR: Model registration failed: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
