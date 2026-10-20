
import pytest
from backend.app.services.market_risk.engine import Holding, MarketRiskEngine
from backend.app.services.var_validation.engine import VaRValidationEngine
from fastapi.testclient import TestClient


def test_market_position_values_and_currency_loss_calculation():
    """
    Verifies that when monetary position values are provided:
    1. Effective portfolio value is calculated from position values.
    2. Weights are properly normalized.
    3. Currency loss amounts (historical_var_95_amount, etc.) are computed accurately.
    """
    engine = MarketRiskEngine()
    holdings = [
        Holding(symbol="SPY", position_value=60000.0),
        Holding(symbol="AAPL", position_value=40000.0),
    ]
    res = engine.analyze_portfolio(holdings=holdings, lookback_days=250)

    assert res.portfolio_value == 100000.0
    assert res.weights == [0.6, 0.4]
    assert res.position_values == {"SPY": 60000.0, "AAPL": 40000.0}

    # Verify currency amounts match percentage * portfolio_value
    assert res.historical_var_95_amount is not None
    expected_95_amt = round(res.historical_var_95 * 100000.0, 2)
    assert abs(res.historical_var_95_amount - expected_95_amt) < 0.05

    assert res.expected_shortfall_95_amount is not None
    expected_es_amt = round(res.expected_shortfall_95 * 100000.0, 2)
    assert abs(res.expected_shortfall_95_amount - expected_es_amt) < 0.05


def test_portfolio_rejects_duplicate_symbols():
    """
    Verifies that duplicate symbols in holdings are explicitly rejected.
    """
    engine = MarketRiskEngine()
    holdings = [
        Holding(symbol="SPY", weight=0.5),
        Holding(symbol="SPY", weight=0.5),
    ]
    with pytest.raises(ValueError, match="Duplicate holding symbol detected"):
        engine.analyze_portfolio(holdings=holdings)


def test_portfolio_rejects_non_finite_weights():
    """
    Verifies that NaN and Inf weights are rejected.
    """
    engine = MarketRiskEngine()
    holdings = [
        Holding(symbol="SPY", weight=float("nan")),
        Holding(symbol="AAPL", weight=0.5),
    ]
    with pytest.raises(ValueError, match="non-finite numbers"):
        engine.analyze_portfolio(holdings=holdings)


def test_var_validation_rejects_duplicate_symbols():
    """
    Verifies that rolling VaR validation rejects duplicate symbols.
    """
    val_engine = VaRValidationEngine()
    holdings = [
        Holding(symbol="SPY", weight=0.5),
        Holding(symbol="SPY", weight=0.5),
    ]
    with pytest.raises(ValueError, match="Duplicate holding symbol detected"):
        val_engine.run_rolling_backtest(holdings=holdings)


def test_var_validation_history_api_endpoint():
    """
    Verifies that POST /api/v1/market/var/validate persists the run and
    GET /api/v1/market/var/history retrieves it with Kupiec and Basel stats.
    """
    from backend.app.main import app

    client = TestClient(app)

    val_req = {
        "portfolio_name": "Test History Portfolio",
        "currency": "USD",
        "holdings": [
            {"symbol": "SPY", "weight": 0.6},
            {"symbol": "MSFT", "weight": 0.4},
        ],
        "method": "historical",
        "confidence_level": 0.95,
        "lookback_window": 100,
    }

    # Run validation
    post_res = client.post("/api/v1/market/var/validate", json=val_req)
    assert post_res.status_code == 200
    data = post_res.json()
    assert data["forecast_count"] > 0
    assert data["kupiec_p_value"] is not None

    # Retrieve history
    hist_res = client.get("/api/v1/market/var/history?limit=5")
    assert hist_res.status_code == 200
    history = hist_res.json()
    assert len(history) > 0

    latest = history[0]
    assert latest["portfolio_name"] == "Test History Portfolio"
    assert latest["currency"] == "USD"
    assert "SPY" in latest["symbols"]
    assert latest["kupiec_p_value"] is not None
    assert latest["basel_zone"] in ["GREEN", "YELLOW", "RED"]


def test_market_refresh_endpoint_offline_and_audit():
    """
    Verifies that POST /api/v1/market/refresh audits local snapshots
    and returns verified status with file details.
    """
    from backend.app.main import app

    client = TestClient(app)

    refresh_res = client.post("/api/v1/market/refresh", json={"fetch_live": False})
    assert refresh_res.status_code == 200
    data = refresh_res.json()
    assert data["status"] in ["ok", "fallback_to_snapshot"]
    assert data["data_source_mode"] == "offline_snapshot"
    assert len(data["supported_symbols"]) > 0
    assert data["manifest_present"] is True


def test_market_portfolio_analyze_api_with_monetary_amount():
    """
    Verifies that POST /api/v1/market/portfolio/analyze returns monetary
    VaR/CVaR amounts when portfolio_value is supplied.
    """
    from backend.app.main import app

    client = TestClient(app)

    req = {
        "portfolio_name": "Tech Benchmark",
        "currency": "USD",
        "portfolio_value": 50000.0,
        "holdings": [
            {"symbol": "AAPL", "weight": 0.5},
            {"symbol": "MSFT", "weight": 0.5},
        ],
        "lookback_days": 100,
        "return_method": "simple",
    }

    res = client.post("/api/v1/market/portfolio/analyze", json=req)
    assert res.status_code == 200
    res_data = res.json()

    assert res_data["portfolio_value"] == 50000.0
    assert res_data["historical_var_95_amount"] is not None
    assert abs(res_data["historical_var_95_amount"] - round(res_data["historical_var_95"] * 50000.0, 2)) < 0.05
    assert res_data["parametric_var_95_amount"] is not None
