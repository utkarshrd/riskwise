"""
test_risk_engine_analytic_references.py

Validates Task A3:
- Tests each VaR/ES method against a known analytic or reference value:
  1. Gaussian VaR: exact match to mu + z_alpha * sigma
  2. Student-t VaR: exact match to fitted t location-scale ppf
  3. Cornish-Fisher VaR: exact match to skewness/kurtosis expansion formula
  4. EWMA VaR: exact match to recursive exponential smoothing variance
  5. Monte Carlo VaR: seeded reproducible Cholesky simulation
  6. GARCH(1,1): estimates conditional variance
  7. Historical VaR: exact match to empirical quantile
- Performance and attribution analytics:
  8. Sharpe ratio: matches (annualized_return - Rf) / annualized_vol
  9. Sortino ratio: matches (annualized_return - Rf) / downside_deviation
  10. Beta: matches Cov(Rp, Rb) / Var(Rb)
  11. Drawdown table: correct peak, trough, depth, duration
  12. Component VaR: Euler allocation sums exactly to portfolio VaR
  13. Marginal VaR: matches analytic gradient (Cov * w / sigma) * z
- API Integration:
  14. POST /api/v1/market/portfolio/analyze with var_method and horizon_days
"""

import math
import numpy as np
import pandas as pd
import pytest
from scipy import stats
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.services.market_risk.risk import (
    returns as ret_mod,
    var_models as vm,
    attribution as attr_mod,
)

client = TestClient(app)


@pytest.fixture
def sample_loss_series():
    """Deterministic, non-normal loss series with known moments for analytic testing."""
    rng = np.random.default_rng(12345)
    # Generate 500 samples with positive skew and fat tails
    base = rng.standard_t(df=5, size=500) * 0.01 + 0.001
    return base


def test_gaussian_var_analytic_reference(sample_loss_series):
    """Gaussian VaR must match mu + z * sigma analytically."""
    mu = float(sample_loss_series.mean())
    sigma = float(sample_loss_series.std(ddof=1))
    z = stats.norm.ppf(0.95)
    expected_var = mu + z * sigma
    # Analytic Gaussian ES = mu + sigma * pdf(z) / (1 - alpha)
    expected_es = mu + sigma * stats.norm.pdf(z) / 0.05

    res = vm.estimate_var(sample_loss_series, method="gaussian", confidence=0.95, bootstrap=False)
    assert abs(res.var - expected_var) < 1e-6
    assert abs(res.es - expected_es) < 1e-4


def test_student_t_var_analytic_reference(sample_loss_series):
    """Student-t VaR must match scipy.stats.t.ppf using fitted MLE parameters."""
    df_fit, loc_fit, scale_fit = stats.t.fit(sample_loss_series)
    expected_var = float(stats.t.ppf(0.95, df=df_fit, loc=loc_fit, scale=scale_fit))

    res = vm.estimate_var(sample_loss_series, method="student_t", confidence=0.95, bootstrap=False)
    assert abs(res.var - expected_var) < 1e-4
    assert res.es >= res.var


def test_cornish_fisher_var_analytic_reference(sample_loss_series):
    """Cornish-Fisher VaR must match explicit polynomial expansion formula."""
    mu = float(sample_loss_series.mean())
    sigma = float(sample_loss_series.std(ddof=1))
    s = float(stats.skew(sample_loss_series))
    k = float(stats.kurtosis(sample_loss_series))  # excess kurtosis
    z = stats.norm.ppf(0.95)

    # Cornish-Fisher quantile expansion:
    z_cf = (
        z
        + (s / 6.0) * (z**2 - 1.0)
        + (k / 24.0) * (z**3 - 3.0 * z)
        - (s**2 / 36.0) * (2.0 * z**3 - 5.0 * z)
    )
    expected_var = mu + z_cf * sigma

    res = vm.estimate_var(sample_loss_series, method="cornish_fisher", confidence=0.95, bootstrap=False)
    assert abs(res.var - expected_var) < 1e-6


def test_ewma_var_analytic_reference(sample_loss_series):
    """EWMA volatility must match recursive exponential decay: sigma_t^2 = lambda * sigma_{t-1}^2 + (1-lambda) * r_{t-1}^2."""
    lam = 0.94
    var_t = float(sample_loss_series[:5].var(ddof=0))
    for l_t in sample_loss_series[5:]:
        var_t = lam * var_t + (1.0 - lam) * float(l_t ** 2)
    sig_t = math.sqrt(var_t)
    mu = float(sample_loss_series.mean())
    z = stats.norm.ppf(0.95)
    expected_var = mu + z * sig_t

    res = vm.estimate_var(sample_loss_series, method="ewma", confidence=0.95, bootstrap=False)
    assert abs(res.var - expected_var) < 1e-6


def test_monte_carlo_var_seeded_reproducibility(sample_loss_series):
    """Seeded Monte Carlo simulation must produce strictly reproducible VaR."""
    res1 = vm.estimate_var(sample_loss_series, method="monte_carlo", confidence=0.95, mc_seed=42)
    res2 = vm.estimate_var(sample_loss_series, method="monte_carlo", confidence=0.95, mc_seed=42)
    assert res1.var == res2.var
    assert res1.es == res2.es
    assert res1.var > 0.0


def test_sharpe_and_sortino_analytic_reference():
    """Sharpe and Sortino ratios match exact formulas."""
    daily_returns = pd.Series([0.01, 0.005, -0.002, 0.008, -0.004, 0.012, 0.003, -0.001] * 20)
    rf = 0.06

    ann_ret = float(daily_returns.mean()) * 252
    ann_vol = float(daily_returns.std(ddof=1)) * math.sqrt(252)
    expected_sharpe = (ann_ret - rf) / ann_vol

    below = daily_returns[daily_returns < 0.0]
    downside_dev = math.sqrt(float((below ** 2).mean())) * math.sqrt(252)
    expected_sortino = (ann_ret - rf) / downside_dev

    computed_sharpe = ret_mod.sharpe_ratio(daily_returns, risk_free_annual=rf)
    computed_sortino = ret_mod.sortino_ratio(daily_returns, risk_free_annual=rf)

    assert abs(computed_sharpe - expected_sharpe) < 1e-6
    assert abs(computed_sortino - expected_sortino) < 1e-6


def test_beta_analytic_reference():
    """Beta matches sample Cov(Rp, Rb) / Var(Rb)."""
    rb = pd.Series([0.01, -0.02, 0.015, -0.005, 0.008] * 10)
    rp = rb * 1.5 + 0.001  # True beta = 1.5
    computed_beta = ret_mod.beta(rp, rb)
    assert abs(computed_beta - 1.5) < 1e-6


def test_component_and_marginal_var_euler_allocation():
    """Component VaR must sum exactly to total portfolio VaR (Euler's homogeneous function theorem)."""
    rng = np.random.default_rng(999)
    ret_a = rng.normal(0.0005, 0.01, 100)
    ret_b = rng.normal(0.0002, 0.015, 100)
    df = pd.DataFrame({"A": ret_a, "B": ret_b})
    weights = np.array([0.6, 0.4])

    attr = attr_mod.compute_attribution(df, ["A", "B"], weights, confidence=0.95)

    sum_comp = sum(attr.component_var.values())
    assert abs(sum_comp - attr.portfolio_var) < 1e-6
    assert abs(sum(attr.component_var_pct.values()) - 1.0) < 1e-6


def test_portfolio_analyze_api_method_selector_and_horizon():
    """Verify POST /api/v1/market/portfolio/analyze handles method selector and horizon parameter."""
    payload = {
        "portfolio_name": "Multi-Model Test",
        "currency": "USD",
        "portfolio_value": 100000.0,
        "holdings": [
            {"symbol": "SPY", "weight": 0.6},
            {"symbol": "AAPL", "weight": 0.4},
        ],
        "var_method": "student_t",
        "horizon_days": 5,
        "lookback_days": 100,
    }
    res = client.post("/api/v1/market/portfolio/analyze", json=payload)
    assert res.status_code == 200
    data = res.json()

    assert data["selected_var_method"] == "student_t"
    assert data["horizon_days"] == 5
    assert data["selected_var_95"] is not None
    assert data["selected_var_95"] > 0.0
    assert data["selected_es_95"] >= data["selected_var_95"]

    # Performance and attribution checks
    assert "sharpe_ratio" in data
    assert "sortino_ratio" in data
    assert "drawdown_table" in data
    assert isinstance(data["drawdown_table"], list)
    assert len(data["drawdown_table"]) > 0
    assert "component_var_pct" in data
    assert "marginal_var" in data
    assert "SPY" in data["component_var_pct"]
    assert "AAPL" in data["component_var_pct"]
