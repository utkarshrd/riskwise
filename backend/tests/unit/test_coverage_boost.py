from backend.app.agents.copilot import (
    RiskCopilotService,
    extract_portfolio_holdings,
    parse_stress_parameters,
    sanitize_input_text,
)
from backend.app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)


def test_copilot_entity_extraction_and_helpers():
    # Unsupported asset
    h, _curr, err = extract_portfolio_holdings("portfolio with 50% BTC and 50% ETH")
    assert h is None
    assert "not in RiskWise's supported offline market universe" in err

    # Valid multi-asset portfolio
    h2, curr2, err2 = extract_portfolio_holdings("60% SPY and 40% AAPL")
    assert err2 is None
    assert curr2 == "USD"
    assert len(h2) == 2

    # Equal weight portfolio
    h3, curr3, err3 = extract_portfolio_holdings("equal weight TCS and INFY")
    assert err3 is None
    assert curr3 == "INR"
    assert len(h3) == 2
    assert abs(sum(x.weight for x in h3) - 1.0) < 1e-4

    # Sanitize input
    cleaned = sanitize_input_text("Hello World -- drop table comment")
    assert "drop table comment" not in cleaned


def test_copilot_stress_parameter_parsing():
    params, missing = parse_stress_parameters("income 1.5 lakh, expenses 60k, savings 3 lakh")
    assert params.get("monthly_income") == 150000.0
    assert params.get("essential_expenses") == 60000.0
    assert params.get("liquid_savings") == 300000.0
    assert len(missing) == 0

    # Follow-up session reuse
    params2, _missing2 = parse_stress_parameters("what if savings are 5 lakh?", session_params=params)
    assert params2.get("monthly_income") == 150000.0
    assert params2.get("liquid_savings") == 500000.0


def test_copilot_service_branches():
    svc = RiskCopilotService()
    # Personal stress test routing
    r_stress = svc.route_and_execute("Stress test my finances: income 1.5 lakh, expenses 60k, savings 3 lakh")
    assert "surplus" in r_stress.answer.lower() or "runway" in r_stress.answer.lower()

    # Advisory refusal
    r_adv = svc.route_and_execute("Which crypto coin or stock should I buy for 10x returns?")
    assert "trading-strategy" in r_adv.answer.lower() or "excluded" in r_adv.answer.lower() or "statistical" in r_adv.answer.lower()

    # Credit explanation routing
    r_cred = svc.route_and_execute("Why was my credit score low? Explain borrower default risk with SHAP and top credit features")
    assert "shap" in r_cred.answer.lower() or "credit" in r_cred.answer.lower() or "feature" in r_cred.answer.lower() or "default" in r_cred.answer.lower()

    # General conversation
    r_gen = svc.route_and_execute("Hello, what are your capabilities?")
    assert "riskwise" in r_gen.answer.lower()


def test_api_credit_error_branches():
    # Invalid features payload triggering 422 schema validation error
    res_err = client.post("/api/v1/credit/score", json={"features": "invalid_not_a_dict"})
    assert res_err.status_code == 422

    res_exp_err = client.post("/api/v1/credit/explain", json={"features": "invalid_not_a_dict"})
    assert res_exp_err.status_code == 422

    res_wi_err = client.post("/api/v1/credit/what-if", json={"baseline_features": "invalid_not_a_dict", "modifications": {}})
    assert res_wi_err.status_code == 422


def test_credit_api_value_error_handling(monkeypatch):
    from backend.app.services.credit.service import CreditService
    def mock_err(self, *args, **kwargs):
        raise ValueError("Simulated validation error")
    monkeypatch.setattr(CreditService, "score", mock_err)
    monkeypatch.setattr(CreditService, "explain", mock_err)
    monkeypatch.setattr(CreditService, "what_if", mock_err)

    r1 = client.post("/api/v1/credit/score", json={"features": {"LIMIT_BAL": 1000.0}})
    assert r1.status_code == 422
    r2 = client.post("/api/v1/credit/explain", json={"features": {"LIMIT_BAL": 1000.0}})
    assert r2.status_code == 422
    r3 = client.post("/api/v1/credit/what-if", json={"baseline_features": {"LIMIT_BAL": 1000.0}, "modifications": {"PAY_0": 1.0}})
    assert r3.status_code == 422


def test_api_market_error_branches():
    # Portfolio analyze with invalid symbol
    res = client.post("/api/v1/market/portfolio/analyze", json={
        "portfolio_name": "Err Test",
        "currency": "USD",
        "holdings": [{"symbol": "NONEXISTENT_TICKER", "weight": 1.0}]
    })
    assert res.status_code == 400

    # Weights not summing to 1.0
    res_w = client.post("/api/v1/market/portfolio/analyze", json={
        "portfolio_name": "Err Test",
        "currency": "USD",
        "holdings": [{"symbol": "SPY", "weight": 0.5}]
    })
    assert res_w.status_code == 400

    # Stress test invalid symbol
    res_st = client.post("/api/v1/market/portfolio/stress-test", json={
        "holdings": [{"symbol": "NONEXISTENT_TICKER", "weight": 1.0}]
    })
    assert res_st.status_code == 400


def test_api_monitoring_branches():
    # Non-existent model version
    res_m = client.get("/api/v1/monitoring/models/non_existent_version_xyz")
    assert res_m.status_code == 404

    # Latest drift status
    res_d = client.get("/api/v1/monitoring/drift/latest")
    assert res_d.status_code == 200

    # Evaluate non-existent challenger
    res_ev = client.post("/api/v1/monitoring/challenger/evaluate", json={
        "challenger_model_id": "non_existent_id"
    })
    assert res_ev.status_code == 404

    # Promote non-existent challenger with valid schema payload
    res_pr = client.post("/api/v1/monitoring/challenger/promote", json={
        "challenger_model_id": "00000000-0000-0000-0000-000000000000",
        "promoted_by": "test_user",
        "justification": "Automated verification unit test"
    })
    assert res_pr.status_code == 404
