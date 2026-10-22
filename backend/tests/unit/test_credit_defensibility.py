import json

import pandas as pd
import pytest
from backend.app.core.config import settings
from backend.app.main import app
from fastapi.testclient import TestClient
from ml.preprocessing import (
    ENGINEERED_COLUMNS_NO_PROTECTED,
    engineer_features,
)


@pytest.fixture
def client():
    return TestClient(app)


def test_feature_engineering_currency_free_and_guards():
    """Verify currency-free feature engineering and zero-division guards."""
    data = {
        "LIMIT_BAL": [100000.0, 50000.0],
        "SEX": [1, 2],
        "EDUCATION": [1, 2],
        "MARRIAGE": [1, 2],
        "AGE": [25, 45],
        "PAY_0": [0, 2],
        "PAY_2": [0, 1],
        "PAY_3": [0, 0],
        "PAY_4": [0, 0],
        "PAY_5": [0, 0],
        "PAY_6": [0, 0],
        "BILL_AMT1": [10000.0, 0.0],
        "BILL_AMT2": [8000.0, -500.0],
        "BILL_AMT3": [6000.0, 0.0],
        "BILL_AMT4": [4000.0, 0.0],
        "BILL_AMT5": [2000.0, 0.0],
        "BILL_AMT6": [1000.0, 0.0],
        "PAY_AMT1": [1000.0, 0.0],
        "PAY_AMT2": [1000.0, 0.0],
        "PAY_AMT3": [1000.0, 0.0],
        "PAY_AMT4": [1000.0, 0.0],
        "PAY_AMT5": [1000.0, 0.0],
        "PAY_AMT6": [1000.0, 0.0],
    }
    df = pd.DataFrame(data)
    eng_df = engineer_features(df, include_protected=False)

    assert set(eng_df.columns) == set(ENGINEERED_COLUMNS_NO_PROTECTED)
    assert "SEX" not in eng_df.columns
    assert "AGE" not in eng_df.columns

    # Check utilisation
    assert eng_df.loc[0, "util_1"] == pytest.approx(0.1)
    # Check pay ratio guarded against 0 bill (row 1, BILL_AMT1 is 0.0 -> guard gives 1.0)
    assert eng_df.loc[1, "pay_ratio_1"] == 1.0
    # Check months late count and worst delay
    assert eng_df.loc[0, "months_late_count"] == 0
    assert eng_df.loc[1, "months_late_count"] == 2
    assert eng_df.loc[1, "worst_delay"] == 2
    # Check util trend
    assert eng_df.loc[0, "util_trend"] == pytest.approx(0.1 - 0.01)


@pytest.mark.requires_trained_model
def test_profile_score_endpoint(client):
    """Test POST /api/v1/credit/profile-score with plain inputs."""
    payload = {
        "credit_limit": 100000.0,
        "bill_amounts": [15000.0, 14000.0, 13000.0, 12000.0, 11000.0, 10000.0],
        "payment_amounts": [3000.0, 3000.0, 3000.0, 3000.0, 3000.0, 3000.0],
        "months_late": [0, 0, 0, 0, 0, 0],
        "age": 28
    }
    res = client.post("/api/v1/credit/profile-score", json=payload)
    assert res.status_code == 200, res.text
    data = res.json()
    assert "probability_of_default" in data
    assert 0.0 <= data["probability_of_default"] <= 1.0
    assert data["relative_risk_band"] in ["LOW_RISK", "MODERATE_RISK", "ELEVATED_RISK", "HIGH_RISK"]
    assert "model_version" in data


def test_profile_score_validation_error(client):
    """Test validation errors for invalid profile score requests."""
    # Invalid credit limit (<= 0)
    res = client.post("/api/v1/credit/profile-score", json={
        "credit_limit": -500.0,
        "bill_amounts": [1000.0] * 6,
        "payment_amounts": [500.0] * 6,
        "months_late": [0] * 6
    })
    assert res.status_code == 422

    # Wrong number of bill amounts (only 4)
    res = client.post("/api/v1/credit/profile-score", json={
        "credit_limit": 50000.0,
        "bill_amounts": [1000.0, 1000.0, 1000.0, 1000.0],
        "payment_amounts": [500.0] * 6,
        "months_late": [0] * 6
    })
    assert res.status_code == 422


@pytest.mark.requires_trained_model
def test_what_if_actionable_mode_rejection_and_ranking(client):
    """Test that what-if actionable mode rejects protected attributes and ranks controllable changes."""
    baseline = {
        "LIMIT_BAL": 100000.0,
        "SEX": 1,
        "EDUCATION": 2,
        "MARRIAGE": 1,
        "AGE": 30,
        "PAY_0": 2,
        "PAY_2": 1,
        "PAY_3": 0,
        "PAY_4": 0,
        "PAY_5": 0,
        "PAY_6": 0,
        "BILL_AMT1": 50000.0,
        "BILL_AMT2": 45000.0,
        "BILL_AMT3": 40000.0,
        "BILL_AMT4": 35000.0,
        "BILL_AMT5": 30000.0,
        "BILL_AMT6": 25000.0,
        "PAY_AMT1": 2000.0,
        "PAY_AMT2": 2000.0,
        "PAY_AMT3": 2000.0,
        "PAY_AMT4": 2000.0,
        "PAY_AMT5": 2000.0,
        "PAY_AMT6": 2000.0,
    }

    # 1. Reject modification of protected attribute AGE in actionable mode
    rej_res = client.post(
        "/api/v1/credit/what-if",
        json={
            "baseline_features": baseline,
            "modifications": {"AGE": 40},
            "actionable_only": True
        }
    )
    assert rej_res.status_code == 422
    assert "protected" in rej_res.json()["detail"].lower()

    # 2. Reject SEX modification in actionable mode via query parameter
    rej_sex = client.post(
        "/api/v1/credit/what-if?actionable=true",
        json={
            "baseline_features": baseline,
            "modifications": {"SEX": 2}
        }
    )
    assert rej_sex.status_code == 422
    assert "protected" in rej_sex.json()["detail"].lower()

    # 3. Allow valid controllable modifications and verify ranked changes
    valid_res = client.post(
        "/api/v1/credit/what-if",
        json={
            "baseline_features": baseline,
            "modifications": {
                "PAY_0": 0.0,
                "PAY_AMT1": 15000.0
            },
            "actionable_only": True
        }
    )
    assert valid_res.status_code == 200
    res_data = valid_res.json()
    assert res_data["actionable_mode"] is True
    assert len(res_data["ranked_changes"]) == 2
    # Ranked changes must be sorted by risk_delta ascending
    ranked = res_data["ranked_changes"]
    assert ranked[0]["risk_delta"] <= ranked[1]["risk_delta"]
    assert all("impact_description" in c for c in ranked)


def test_fairness_audit_artifact_exists_and_compliant():
    """Verify that artifacts/evaluation/fairness_audit.json exists and passes four-fifths rule."""
    audit_file = settings.REPO_ROOT / "artifacts" / "evaluation" / "fairness_audit.json"
    assert audit_file.exists()
    with open(audit_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data["model_version"] == "credit_xgboost_v1"
    dir_metrics = data["disparate_impact_ratios"]
    assert dir_metrics["four_fifths_rule_compliant"] is True
    for key, val in dir_metrics.items():
        if isinstance(val, (int, float)) and key != "four_fifths_rule_threshold":
            assert val >= 0.80, f"Disparate impact ratio {key}={val} violated 80% rule!"
