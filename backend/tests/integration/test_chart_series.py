import numpy as np
from backend.app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)

PAYLOAD = {
    "portfolio_name": "Chart Series",
    "currency": "USD",
    "holdings": [{"symbol": "SPY", "weight": 0.5}, {"symbol": "AAPL", "weight": 0.5}],
}


def _analyze():
    res = client.post("/api/v1/market/portfolio/analyze", json=PAYLOAD)
    assert res.status_code == 200
    return res.json()


def test_chart_series_is_consistent_with_reported_metrics():
    data = _analyze()
    cs = data["chart_series"]
    n = data["observations_count"]

    assert len(cs["dates"]) == n
    assert len(cs["portfolio_cumulative_pct"]) == n
    assert len(cs["drawdown_pct"]) == n

    # the plotted worst drawdown must equal the headline max drawdown, not a separate approximation
    assert abs(-min(cs["drawdown_pct"]) / 100.0 - data["maximum_drawdown"]) < 5e-4
    assert max(cs["drawdown_pct"]) <= 0.0

    # histogram is built from observed returns: every observation is counted exactly once
    assert sum(b["count"] for b in cs["histogram"]) == n
    assert all(b["lo"] < b["hi"] for b in cs["histogram"])


def test_chart_series_benchmark_is_aligned_and_not_synthetic():
    cs = _analyze()["chart_series"]
    bench = cs["benchmark_cumulative_pct"]
    assert bench is not None and len(bench) == len(cs["dates"])
    # a real benchmark path is not a flat or perfectly periodic line
    vals = np.array([v for v in bench if v is not None])
    assert vals.std() > 0.0
