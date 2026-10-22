"""fx_mode: strict by default, explicit opt-in conversion with a stated FX series and date range."""

import numpy as np
import pandas as pd
import pytest
from backend.app.core.config import settings
from backend.app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)

ANALYZE = "/api/v1/market/portfolio/analyze"
SNAPSHOTS = settings.DATA_DIR / "market_snapshots"


def _mixed(**extra):
    return {
        "portfolio_name": "Mixed",
        "currency": "INR",
        "holdings": [{"symbol": "SPY", "weight": 0.5}, {"symbol": "RELIANCE.NS", "weight": 0.5}],
        **extra,
    }


def _prices(stem: str) -> pd.Series:
    df = pd.read_csv(SNAPSHOTS / f"{stem}.csv", parse_dates=["date"]).set_index("date")
    return df["adj_close"]


# ── strict (default) ────────────────────────────────────────────────────────────


def test_default_mode_rejects_mixed_currencies_and_names_the_opt_in():
    res = client.post(ANALYZE, json=_mixed())
    assert res.status_code == 400
    assert "fx_mode='convert_to_base'" in res.json()["detail"]["message"]


def test_strict_response_states_mode_and_no_conversion():
    res = client.post(
        ANALYZE,
        json={"currency": "USD", "holdings": [{"symbol": "SPY", "weight": 0.5}, {"symbol": "AAPL", "weight": 0.5}]},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["fx_converted"] is False
    assert body["fx"]["mode"] == "strict"
    assert body["assumptions"]["fx_mode"] == "strict"


def test_strict_still_rejects_wrong_base_currency():
    res = client.post(ANALYZE, json={"currency": "INR", "holdings": [{"symbol": "SPY", "weight": 1.0}]})
    assert res.status_code == 400


def test_unknown_fx_mode_is_rejected_by_validation():
    res = client.post(ANALYZE, json=_mixed(fx_mode="auto"))
    assert res.status_code == 422


# ── convert_to_base ─────────────────────────────────────────────────────────────


def test_convert_to_inr_states_fx_series_and_date_range():
    res = client.post(ANALYZE, json=_mixed(fx_mode="convert_to_base"))
    assert res.status_code == 200
    body = res.json()
    fx = body["fx"]

    assert body["fx_converted"] is True
    assert fx["mode"] == "convert_to_base"
    assert fx["base_currency"] == "INR"
    assert fx["fx_pair"] == "USDINR=X"
    assert fx["converted_symbols"] == ["SPY"]
    assert fx["conversion_directions"] == {"SPY": "USD->INR"}
    # the FX slice reported is exactly the window the analysis used
    assert fx["series_start"] == body["start_date"]
    assert fx["series_end"] == body["end_date"]
    assert fx["observations"] == body["observations_count"] + 1  # N prices give N-1 returns
    assert fx["rate_start"] > 0 and fx["rate_end"] > 0


def test_converted_volatility_matches_independent_calculation():
    """Rebuild the portfolio from the raw CSVs: SPY * USDINR, 50/50 with RELIANCE.NS, daily rebalanced."""
    body = client.post(ANALYZE, json=_mixed(fx_mode="convert_to_base")).json()

    spy_inr = _prices("SPY") * _prices("USDINR=X").reindex(_prices("SPY").index)
    prices = pd.concat([spy_inr.rename("SPY"), _prices("RELIANCE.NS").rename("R")], axis=1, join="inner").dropna()
    prices = prices.loc[body["start_date"] : body["end_date"]]
    returns = prices.pct_change().dropna()
    port = returns.dot(np.array([0.5, 0.5]))
    expected_vol = float(port.std(ddof=1) * np.sqrt(252))

    assert len(returns) == body["observations_count"]
    assert body["annualized_volatility"] == pytest.approx(expected_vol, abs=6e-5)


def test_conversion_changes_the_result_versus_unconverted_prices():
    """Converting USD prices into INR adds FX movement, so volatility differs from a naive local-price mix."""
    converted = client.post(ANALYZE, json=_mixed(fx_mode="convert_to_base")).json()
    spy = _prices("SPY")
    rel = _prices("RELIANCE.NS")
    naive = pd.concat([spy.rename("a"), rel.rename("b")], axis=1, join="inner").dropna().pct_change().dropna()
    naive_vol = float(naive.dot(np.array([0.5, 0.5])).std(ddof=1) * np.sqrt(252))
    assert abs(converted["annualized_volatility"] - naive_vol) > 1e-4


def test_convert_to_usd_divides_inr_assets_by_the_rate():
    body = client.post(
        ANALYZE,
        json={
            "currency": "USD",
            "fx_mode": "convert_to_base",
            "holdings": [{"symbol": "SPY", "weight": 0.5}, {"symbol": "RELIANCE.NS", "weight": 0.5}],
        },
    ).json()
    assert body["fx"]["base_currency"] == "USD"
    assert body["fx"]["converted_symbols"] == ["RELIANCE.NS"]
    assert body["fx"]["conversion_directions"] == {"RELIANCE.NS": "INR->USD"}


def test_convert_mode_with_single_currency_matching_base_does_not_convert():
    res = client.post(
        ANALYZE,
        json={
            "currency": "USD",
            "fx_mode": "convert_to_base",
            "holdings": [{"symbol": "SPY", "weight": 0.5}, {"symbol": "AAPL", "weight": 0.5}],
        },
    )
    assert res.status_code == 200
    assert res.json()["fx_converted"] is False


def test_legacy_fx_conversion_flag_behaves_like_convert_to_base():
    body = client.post(ANALYZE, json=_mixed(fx_conversion=True)).json()
    assert body["fx_converted"] is True
    assert body["fx"]["mode"] == "convert_to_base"


def test_convert_mode_requires_a_supported_base_currency():
    res = client.post(ANALYZE, json=_mixed(fx_mode="convert_to_base", currency="EUR"))
    assert res.status_code == 400


# ── other endpoints share the same policy ───────────────────────────────────────


def test_stress_test_is_strict_by_default_and_converts_on_opt_in():
    holdings = [{"symbol": "SPY", "weight": 0.5}, {"symbol": "RELIANCE.NS", "weight": 0.5}]
    strict = client.post("/api/v1/market/portfolio/stress-test", json={"holdings": holdings})
    assert strict.status_code == 400

    ok = client.post(
        "/api/v1/market/portfolio/stress-test",
        json={"holdings": holdings, "currency": "INR", "fx_mode": "convert_to_base"},
    )
    assert ok.status_code == 200
    assert ok.json()[0]["assumptions"]["fx_mode"] == "convert_to_base"


def test_var_validate_reports_fx_when_converting():
    payload = {
        "currency": "INR",
        "holdings": [{"symbol": "SPY", "weight": 0.5}, {"symbol": "RELIANCE.NS", "weight": 0.5}],
        "method": "historical",
        "confidence_level": 0.95,
        "lookback_window": 100,
    }
    assert client.post("/api/v1/market/var/validate", json=payload).status_code == 400

    ok = client.post("/api/v1/market/var/validate", json={**payload, "fx_mode": "convert_to_base"})
    assert ok.status_code == 200
    assert ok.json()["fx"]["fx_pair"] == "USDINR=X"
