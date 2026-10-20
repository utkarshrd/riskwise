import json
import uuid

from backend.app.db.models import (
    AssessmentRun,
    AuditEvent,
    CopilotSession,
    DriftRun,
    MarketRiskRun,
    ModelVersion,
    VaRValidationRun,
)
from backend.app.db.session import SessionLocal
from backend.app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)


def test_persistence_credit_score_roundtrip():
    payload = {
        "features": {
            "LIMIT_BAL": 150000.0,
            "SEX": 1,
            "EDUCATION": 2,
            "MARRIAGE": 1,
            "AGE": 32,
            "PAY_0": 0,
            "PAY_2": 0,
            "PAY_3": 0,
            "PAY_4": 0,
            "PAY_5": 0,
            "PAY_6": 0,
            "BILL_AMT1": 25000.0,
            "BILL_AMT2": 24000.0,
            "BILL_AMT3": 23000.0,
            "BILL_AMT4": 22000.0,
            "BILL_AMT5": 21000.0,
            "BILL_AMT6": 20000.0,
            "PAY_AMT1": 3000.0,
            "PAY_AMT2": 3000.0,
            "PAY_AMT3": 3000.0,
            "PAY_AMT4": 3000.0,
            "PAY_AMT5": 3000.0,
            "PAY_AMT6": 3000.0
        }
    }
    res = client.post("/api/v1/credit/score", json=payload)
    assert res.status_code == 200
    data = res.json()

    db = SessionLocal()
    try:
        rec = db.query(AssessmentRun).order_by(AssessmentRun.created_at.desc()).first()
        assert rec is not None
        assert abs(rec.score - data["probability_of_default"]) < 1e-4
        assert rec.risk_band == data["relative_risk_band"]
        snapshot = json.loads(rec.input_snapshot_json)
        assert snapshot["LIMIT_BAL"] == 150000.0
    finally:
        db.close()


def test_persistence_market_risk_roundtrip():
    payload = {
        "portfolio_name": "Persistence Test Portfolio",
        "currency": "USD",
        "lookback_days": 250,
        "holdings": [
            {"symbol": "SPY", "weight": 0.6},
            {"symbol": "AAPL", "weight": 0.4}
        ]
    }
    res = client.post("/api/v1/market/portfolio/analyze", json=payload)
    assert res.status_code == 200
    data = res.json()

    db = SessionLocal()
    try:
        rec = db.query(MarketRiskRun).order_by(MarketRiskRun.created_at.desc()).first()
        assert rec is not None
        metrics = json.loads(rec.metrics_json)
        assert abs(metrics["annualized_volatility"] - data["annualized_volatility"]) < 1e-4
        assert rec.lookback == 249 or rec.lookback == 250
    finally:
        db.close()


def test_persistence_var_validation_roundtrip():
    payload = {
        "holdings": [{"symbol": "SPY", "weight": 1.0}],
        "lookback_window": 100,
        "confidence_level": 0.95
    }
    res = client.post("/api/v1/market/var/validate", json=payload)
    assert res.status_code == 200
    data = res.json()

    db = SessionLocal()
    try:
        rec = db.query(VaRValidationRun).order_by(VaRValidationRun.created_at.desc()).first()
        assert rec is not None
        assert rec.forecast_count == data["forecast_count"]
        assert rec.exception_count == data["exception_count"]
    finally:
        db.close()


def test_persistence_drift_run_roundtrip():
    payload = {
        "reference_batch_id": "ref_baseline_val",
        "current_batch_id": "test_drift_current_batch"
    }
    res = client.post("/api/v1/monitoring/drift/run", json=payload)
    assert res.status_code == 200
    data = res.json()

    db = SessionLocal()
    try:
        rec = db.query(DriftRun).filter(DriftRun.id == data["id"]).first()
        assert rec is not None
        assert rec.reference_batch_id == "ref_baseline_val"
        psi_dict = json.loads(rec.psi_by_feature_json)
        assert len(psi_dict) > 0
    finally:
        db.close()


def test_persistence_copilot_session_roundtrip():
    sess_id = f"test_persist_{uuid.uuid4().hex[:8]}"
    msg1 = "Calculate EMI for 25 lakh at 10% for 5 years"
    res1 = client.post("/api/v1/copilot/message", json={"message": msg1, "session_id": sess_id})
    assert res1.status_code == 200

    db = SessionLocal()
    try:
        sess = db.query(CopilotSession).filter(CopilotSession.id == sess_id).first()
        assert sess is not None
        params = json.loads(sess.parameters_json)
        assert params.get("principal") == 2500000.0
        assert params.get("annual_interest_rate") == 0.10
        hist = json.loads(sess.history_json)
        assert len(hist) == 1
        assert hist[0]["intent"] == "CALCULATE_EMI"
    finally:
        db.close()


def test_persistence_registry_and_promotion_audit():
    db = SessionLocal()
    test_challenger_id = str(uuid.uuid4())
    try:
        # Create a candidate model in database with AUC exceeding champion by >0.005
        candidate = ModelVersion(
            id=test_challenger_id,
            model_name="challenger_rf",
            version=f"rf_v_{test_challenger_id[:6]}",
            dataset_id="taiwan_credit_2005",
            feature_schema_version="v1",
            preprocessing_artifact="artifacts/models/credit_preprocessor.joblib",
            model_artifact="artifacts/models/credit_xgboost_model.joblib",
            metrics_json=json.dumps({"roc_auc": 0.945, "f1_score": 0.72, "decision_threshold": 0.5, "risk_band_cutoffs": {"low": 0.15, "moderate": 0.35, "elevated": 0.60}}),
            status="candidate",
            checksum="test_candidate_checksum_12345"
        )
        db.add(candidate)
        db.commit()

        # Promote challenger
        res = client.post("/api/v1/monitoring/challenger/promote", json={
            "challenger_version_id": test_challenger_id,
            "promotion_reason": "Automated verification test promotion audit check"
        })
        assert res.status_code == 200

        # Verify AuditEvent written
        audit = db.query(AuditEvent).filter(
            AuditEvent.target_id == test_challenger_id,
            AuditEvent.action == "CHALLENGER_PROMOTION"
        ).first()
        assert audit is not None
        details = json.loads(audit.details_json)
        assert "Automated verification" in details.get("why", "")

        # Verify candidate became active
        updated = db.query(ModelVersion).filter(ModelVersion.id == test_challenger_id).first()
        assert updated.status == "active"
    finally:
        # Clean up test model and restore original active champion
        db.query(AuditEvent).filter(AuditEvent.target_id == test_challenger_id).delete()
        db.query(ModelVersion).filter(ModelVersion.id == test_challenger_id).delete()
        champ = db.query(ModelVersion).filter(ModelVersion.version == "credit_xgboost_v1").first()
        if champ:
            champ.status = "active"
        db.commit()
        db.close()
