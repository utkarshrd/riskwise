import json

import pytest
from backend.app.db.models import ModelVersion
from backend.app.db.session import SessionLocal
from backend.app.main import app
from backend.app.services.credit.service import CreditService
from fastapi.testclient import TestClient


def test_credit_score_rejects_incomplete_metadata():
    """
    Assert that if model metadata lacks 'decision_threshold' or 'risk_band_cutoffs',
    CreditService.score() raises RuntimeError('model metadata incomplete'),
    and the API returns HTTP 503 'model metadata incomplete'.
    """
    db = SessionLocal()
    try:
        # Save previous active model ID to restore after test
        prev_active = db.query(ModelVersion).filter(ModelVersion.status == "active").first()
        prev_id = prev_active.id if prev_active else None

        # Archive active models and insert model version with incomplete metadata
        db.query(ModelVersion).filter(ModelVersion.status == "active").update({"status": "archived"})
        
        incomplete_model = ModelVersion(
            id="test-incomplete-meta-model",
            model_name="xgboost",
            version="credit_incomplete_v1",
            dataset_id="Indian_Banking_CIBIL_Merged_2026",
            feature_schema_version="v1.0",
            preprocessing_artifact=prev_active.preprocessing_artifact if prev_active else "dummy",
            model_artifact=prev_active.model_artifact if prev_active else "dummy",
            checksum=prev_active.checksum if prev_active else "dummy_checksum",
            metrics_json=json.dumps({"roc_auc": 0.78}),  # Lacks decision_threshold and risk_band_cutoffs
            status="active"
        )
        db.add(incomplete_model)
        db.commit()

        service = CreditService(db)
        # Mock loaded model and preprocessor so execution reaches the metadata check
        class DummyModel:
            def predict_proba(self, X):
                import numpy as np
                return np.array([[0.7, 0.3]])

        class DummyPrep:
            def transform(self, df):
                import numpy as np
                return np.zeros((1, 23))

        service.model = DummyModel()
        service.preprocessor = DummyPrep()

        # Direct service call must fail explicitly with 'model metadata incomplete'
        with pytest.raises(RuntimeError, match="model metadata incomplete"):
            service.score({"LIMIT_BAL": 50000, "AGE": 30})

        # Test via API client
        client = TestClient(app)
        resp = client.post("/api/v1/credit/score", json={"features": {"LIMIT_BAL": 50000, "AGE": 30}})
        assert resp.status_code == 503
        assert "model metadata incomplete" in resp.json()["detail"].lower()

        # System status must show model as NOT ready
        status_resp = client.get("/api/v1/system/status")
        assert status_resp.status_code == 200
        assert status_resp.json()["credit_model_ready"] is False

    finally:
        # Cleanup: remove test model and restore original active model
        db.query(ModelVersion).filter(ModelVersion.id == "test-incomplete-meta-model").delete()
        if prev_id:
            db.query(ModelVersion).filter(ModelVersion.id == prev_id).update({"status": "active"})
        db.commit()
        db.close()
