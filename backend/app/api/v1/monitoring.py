import json
from datetime import UTC, datetime

import pandas as pd
from backend.app.core.config import settings
from backend.app.db.models import AuditEvent, DriftRun, ModelVersion, MonitoringAlert
from backend.app.db.session import get_db
from backend.app.schemas.monitoring import (
    ChallengerEvaluateRequest,
    ChallengerEvaluateResponse,
    ChallengerPromoteRequest,
    ChallengerPromoteResponse,
    DriftRunRequest,
    DriftRunResponse,
    FeaturePSISchema,
    ModelRegistryItem,
)
from backend.app.services.monitoring.engine import MonitoringEngine
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

router = APIRouter(prefix="/monitoring", tags=["ML Monitoring & Model Registry"])


@router.get("/models", response_model=list[ModelRegistryItem])
def list_registry_models(db: Session = Depends(get_db)):
    """List all registered models, artifact paths, training metadata, and active status."""
    models = db.query(ModelVersion).order_by(ModelVersion.trained_at.desc()).all()
    results = []
    for m in models:
        metrics = json.loads(m.metrics_json) if m.metrics_json else {}
        results.append(ModelRegistryItem(
            id=m.id,
            model_name=m.model_name,
            version=m.version,
            dataset_id=m.dataset_id,
            status=m.status,
            trained_at=m.trained_at.isoformat(),
            checksum=m.checksum,
            metrics=metrics
        ))
    return results


@router.post("/drift/run", response_model=DriftRunResponse)
def run_drift_monitoring(request: DriftRunRequest, db: Session = Depends(get_db)):
    """Compute Population Stability Index (PSI) drift across features against baseline."""
    # Find active model version
    if request.model_version_id:
        model_rec = db.query(ModelVersion).filter(ModelVersion.id == request.model_version_id).first()
    else:
        model_rec = db.query(ModelVersion).filter(ModelVersion.status == "active").first()

    if not model_rec:
        raise HTTPException(status_code=404, detail="No model version found for drift analysis.")

    # Load baseline dataset
    data_file = settings.DATA_DIR / "processed" / "credit_indian_cleaned.csv"
    if not data_file.exists():
        data_file = settings.DATA_DIR / "processed" / "credit_default_cleaned.csv"

    if not data_file.exists():
        raise HTTPException(status_code=503, detail="Processed baseline benchmark dataset not found.")

    df = pd.read_csv(data_file)
    # Split into reference and simulated current partition for drift testing
    split_point = min(15000, len(df) // 2)
    ref_df = df.iloc[:split_point].copy()
    cur_df = df.iloc[split_point:].copy()

    drift_res = MonitoringEngine.evaluate_batch_drift(
        model_version_id=model_rec.id,
        reference_df=ref_df,
        current_df=cur_df,
        reference_batch_id=request.reference_batch_id,
        current_batch_id=request.current_batch_id,
        warning_threshold=request.warning_threshold,
        critical_threshold=request.critical_threshold
    )

    # Persist DriftRun
    db_drift = DriftRun(
        model_version_id=model_rec.id,
        reference_batch_id=request.reference_batch_id,
        current_batch_id=request.current_batch_id,
        psi_by_feature_json=json.dumps([f.model_dump() for f in drift_res.features]),
        threshold_config_json=json.dumps({
            "warning": request.warning_threshold,
            "critical": request.critical_threshold
        }),
        status=drift_res.overall_status
    )
    db.add(db_drift)

    # If critical drift, raise alert record
    if drift_res.overall_status in ["CRITICAL_DRIFT", "WARNING_DRIFT"]:
        alert = MonitoringAlert(
            model_version_id=model_rec.id,
            drift_run_id=db_drift.id,
            severity="critical" if drift_res.overall_status == "CRITICAL_DRIFT" else "warning",
            message=f"Detected {drift_res.overall_status} (Overall PSI: {drift_res.overall_psi}) across evaluated features."
        )
        db.add(alert)

    db.commit()

    return DriftRunResponse(
        id=db_drift.id,
        model_version_id=drift_res.model_version_id,
        reference_batch_id=drift_res.reference_batch_id,
        current_batch_id=drift_res.current_batch_id,
        overall_psi=drift_res.overall_psi,
        overall_status=drift_res.overall_status,
        drift_source=drift_res.drift_source,
        features=[FeaturePSISchema(**f.model_dump()) for f in drift_res.features],
        run_timestamp=drift_res.run_timestamp
    )


@router.post("/challenger/evaluate", response_model=ChallengerEvaluateResponse)
def evaluate_challenger_model(request: ChallengerEvaluateRequest, db: Session = Depends(get_db)):
    """Evaluate a candidate challenger model against the current champion."""
    champion = db.query(ModelVersion).filter(ModelVersion.status == "active").first()
    if not champion:
        raise HTTPException(status_code=404, detail="No active champion model registered.")

    challenger = db.query(ModelVersion).filter(ModelVersion.id == request.challenger_model_id).first()
    if not challenger:
        raise HTTPException(status_code=404, detail=f"Challenger model '{request.challenger_model_id}' not found.")

    res = MonitoringEngine.evaluate_challenger(champion, challenger)
    return ChallengerEvaluateResponse(**res.model_dump())


@router.get("/drift/latest")
def get_latest_drift_status(db: Session = Depends(get_db)):
    """
    Returns latest drift run. If no drift run exists, returns explicit 'NO_DATA' status.
    Never fabricates a default 'HEALTHY' or 'PASSED' state.
    """
    latest = db.query(DriftRun).order_by(DriftRun.created_at.desc()).first()
    if not latest:
        return {
            "status": "NO_DATA",
            "message": "No drift monitoring run has been executed yet. Real drift calculation required.",
            "overall_psi": None,
            "drift_source": None,
            "latest_run_id": None
        }
    return {
        "status": latest.status,
        "latest_run_id": latest.id,
        "model_version_id": latest.model_version_id,
        "run_timestamp": latest.created_at.isoformat(),
        "threshold_config": json.loads(latest.threshold_config_json) if latest.threshold_config_json else {}
    }


@router.post("/challenger/promote", response_model=ChallengerPromoteResponse)
def promote_challenger_model(request: ChallengerPromoteRequest, db: Session = Depends(get_db)):
    """
    Explicitly promote a verified challenger model and record full audit log.
    Refuses promotion if challenger does not meet PRD improvement criteria.
    """
    challenger = db.query(ModelVersion).filter(ModelVersion.id == request.challenger_model_id).first()
    if not challenger:
        raise HTTPException(status_code=404, detail=f"Challenger model '{request.challenger_model_id}' not found.")

    champion = db.query(ModelVersion).filter(ModelVersion.status == "active").first()
    now_iso = datetime.now(UTC).isoformat()
    metrics_log = {}

    if champion:
        eval_res = MonitoringEngine.evaluate_challenger(champion, challenger)
        metrics_log = eval_res.model_dump()
        if not eval_res.promotion_eligible:
            # Audit the refused promotion attempt
            refusal_audit = AuditEvent(
                actor_type="user",
                action="CHALLENGER_PROMOTION_REFUSED",
                target_type="model_version",
                target_id=challenger.id,
                details_json=json.dumps({
                    "who": request.promoted_by,
                    "when": now_iso,
                    "why": request.justification,
                    "metrics": metrics_log,
                    "refusal_reason": eval_res.recommendation
                })
            )
            db.add(refusal_audit)
            db.commit()
            raise HTTPException(
                status_code=400,
                detail=f"Promotion refused: Challenger does not satisfy PRD improvement criteria. {eval_res.recommendation}"
            )

    # Archive previous active champion
    if champion:
        champion.status = "archived"

    # Promote challenger
    challenger.status = "active"

    # Persist audit row with who, when, why, and metrics
    audit = AuditEvent(
        actor_type="user",
        action="CHALLENGER_PROMOTION",
        target_type="model_version",
        target_id=challenger.id,
        details_json=json.dumps({
            "who": request.promoted_by,
            "when": now_iso,
            "why": request.justification,
            "metrics": metrics_log,
            "version": challenger.version
        })
    )
    db.add(audit)
    db.commit()

    return ChallengerPromoteResponse(
        status="PROMOTED",
        promoted_model_id=challenger.id,
        version=challenger.version,
        audit_event_id=audit.id,
        timestamp=now_iso
    )
