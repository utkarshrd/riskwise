from backend.app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)


def test_system_status_reflects_trained_artifacts():
    """Verify system status accurately detects loaded model and market snapshots."""
    response = client.get("/api/v1/system/status")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "operational"
    assert data["offline_mode"] is True
    assert data["credit_model_loaded"] is True
    assert data["active_model_version"] is not None
    assert data["market_snapshot_loaded"] is True
    assert len(data["market_tickers_available"]) >= 4
    assert data["rag_corpus_loaded"] is True


def test_credit_api_workflow():
    # 1. List models
    models_res = client.get("/api/v1/credit/models")
    assert models_res.status_code == 200
    models = models_res.json()
    assert len(models) >= 1
    assert "roc_auc" in models[0]["metrics"]

    # 2. Score profile
    borrower_profile = {
        "LIMIT_BAL": 200000.0,
        "SEX": 1,
        "EDUCATION": 2,
        "MARRIAGE": 1,
        "AGE": 35,
        "PAY_0": 0,
        "PAY_2": 0,
        "PAY_3": 0,
        "PAY_4": 0,
        "PAY_5": 0,
        "PAY_6": 0,
        "BILL_AMT1": 25000.0,
        "BILL_AMT2": 24000.0,
        "BILL_AMT3": 23000.0,
        "BILL_AMT4": 20000.0,
        "BILL_AMT5": 19000.0,
        "BILL_AMT6": 18000.0,
        "PAY_AMT1": 2000.0,
        "PAY_AMT2": 2000.0,
        "PAY_AMT3": 2000.0,
        "PAY_AMT4": 2000.0,
        "PAY_AMT5": 2000.0,
        "PAY_AMT6": 2000.0
    }
    score_res = client.post("/api/v1/credit/score", json={"features": borrower_profile})
    assert score_res.status_code == 200
    score_data = score_res.json()
    assert 0.0 <= score_data["probability_of_default"] <= 1.0
    assert score_data["relative_risk_band"] in ["LOW_RISK", "MODERATE_RISK", "ELEVATED_RISK", "HIGH_RISK"]
    assert "Indian" in score_data["methodology_disclosure"]
    assert "predicted_category" in score_data
    assert score_data["predicted_category"] in ["P1", "P2", "P3", "P4"]

    # 3. Explain profile (SHAP)
    explain_res = client.post("/api/v1/credit/explain", json={"features": borrower_profile, "top_n": 5})
    assert explain_res.status_code == 200
    explain_data = explain_res.json()
    assert len(explain_data["top_contributions"]) == 5
    assert len(explain_data["all_contributions"]) >= 42

    # 4. What-if counterfactual analysis (increase payment delay PAY_0 to 2)
    what_if_res = client.post("/api/v1/credit/what-if", json={
        "baseline_features": borrower_profile,
        "modifications": {"PAY_0": 2.0}
    })
    assert what_if_res.status_code == 200
    what_if_data = what_if_res.json()
    assert what_if_data["direction_of_change"] in ["RISK_INCREASED", "RISK_REDUCED", "UNCHANGED", "CATEGORY_UPGRADED", "CATEGORY_DOWNGRADED"]
    assert "PAY_0" in what_if_data["modified_features"]


def test_finance_api_workflow():
    # 1. EMI
    emi_res = client.post("/api/v1/finance/emi", json={
        "principal": 500000.0,
        "annual_interest_rate": 0.105,
        "tenure_months": 36,
        "include_schedule": True
    })
    assert emi_res.status_code == 200
    emi_data = emi_res.json()
    assert emi_data["monthly_emi"] > 0.0
    assert len(emi_data["amortization_schedule"]) == 36

    # 2. Stress test
    stress_res = client.post("/api/v1/finance/stress-test", json={
        "monthly_income": 80000.0,
        "essential_expenses": 35000.0,
        "discretionary_expenses": 15000.0,
        "existing_emis": 12000.0,
        "liquid_savings": 150000.0,
        "scenario": {
            "income_reduction_pct": 20.0,
            "essential_expense_surge_pct": 10.0
        }
    })
    assert stress_res.status_code == 200
    stress_data = stress_res.json()
    assert stress_data["baseline_surplus"] == 18000.0
    assert stress_data["stressed_surplus"] < stress_data["baseline_surplus"]


def test_market_api_workflow():
    # 1. Universe
    univ_res = client.get("/api/v1/market/universe")
    assert univ_res.status_code == 200
    univ = univ_res.json()
    assert "SPY" in univ["supported_symbols"]

    # 2. Portfolio analyze
    port_res = client.post("/api/v1/market/portfolio/analyze", json={
        "portfolio_name": "Test Port",
        "currency": "USD",
        "holdings": [
            {"symbol": "SPY", "weight": 0.5},
            {"symbol": "AAPL", "weight": 0.5}
        ]
    })
    assert port_res.status_code == 200
    port_data = port_res.json()
    assert port_data["annualized_volatility"] > 0.0
    assert port_data["historical_var_95"] > 0.0
    assert port_data["expected_shortfall_95"] >= port_data["historical_var_95"]

    # 3. Market stress test
    stress_res = client.post("/api/v1/market/portfolio/stress-test", json={
        "holdings": [{"symbol": "SPY", "weight": 1.0}]
    })
    assert stress_res.status_code == 200
    stress_list = stress_res.json()
    assert len(stress_list) >= 2

    # 4. VaR validation
    var_val_res = client.post("/api/v1/market/var/validate", json={
        "holdings": [{"symbol": "SPY", "weight": 1.0}],
        "method": "historical",
        "confidence_level": 0.95,
        "lookback_window": 100
    })
    assert var_val_res.status_code == 200
    var_val_data = var_val_res.json()
    assert var_val_data["forecast_count"] > 100
    assert "kupiec_test_passed" in var_val_data
    # conditional coverage must reach the API response, not just the engine
    assert var_val_data["christoffersen_cc_stat"] is not None
    assert 0.0 <= var_val_data["christoffersen_cc_p_value"] <= 1.0
    assert isinstance(var_val_data["christoffersen_cc_test_passed"], bool)


def test_copilot_api_routing():
    # 1. EMI calculation routing
    c_emi = client.post("/api/v1/copilot/message", json={"message": "What is the EMI for 300000 at 12% for 24 months?"})
    assert c_emi.status_code == 200
    d_emi = c_emi.json()
    assert d_emi["intent"] == "CALCULATE_EMI"
    assert len(d_emi["tool_trace"]) == 1

    # 2. Portfolio risk routing
    c_port = client.post("/api/v1/copilot/message", json={"message": "Analyze portfolio VaR and volatility"})
    assert c_port.status_code == 200
    d_port = c_port.json()
    assert d_port["intent"] == "ANALYZE_PORTFOLIO_RISK"

    # 3. Conceptual RAG search routing with citations
    c_rag = client.post("/api/v1/copilot/message", json={"message": "What is Basel II Probability of Default (PD)?"})
    assert c_rag.status_code == 200
    d_rag = c_rag.json()
    assert d_rag["intent"] in ["FINANCIAL_EDUCATION_RAG", "CONCEPTUAL_RAG_SEARCH"]
    assert len(d_rag["citations"]) > 0

    # 4. Safety rejection of trading strategy signals
    c_rej = client.post("/api/v1/copilot/message", json={"message": "Give me a profitable buy signal with RSI strategy"})
    assert c_rej.status_code == 200
    d_rej = c_rej.json()
    assert d_rej["intent"] == "REJECTED_TRADING_STRATEGY"
    assert len(d_rej["tool_trace"]) == 0


def test_monitoring_api_workflow():
    # 1. Models list
    models_res = client.get("/api/v1/monitoring/models")
    assert models_res.status_code == 200
    models = models_res.json()
    assert len(models) >= 1

    # 2. Run drift
    drift_res = client.post("/api/v1/monitoring/drift/run", json={
        "reference_batch_id": "test_ref",
        "current_batch_id": "test_cur"
    })
    assert drift_res.status_code == 200
    drift_data = drift_res.json()
    assert "overall_psi" in drift_data
    assert len(drift_data["features"]) > 0


def test_methodology_api():
    res = client.get("/api/v1/methodology")
    assert res.status_code == 200
    data = res.json()
    assert data["version"] == "3.0.0"
    assert len(data["disclaimers"]) >= 4
