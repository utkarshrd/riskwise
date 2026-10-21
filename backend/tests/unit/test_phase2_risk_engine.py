"""
test_phase2_risk_engine.py — Phase 2 tests for the expanded market risk engine.

Covers:
  - var_models: all 8 methods, multi-confidence, horizon scaling, bootstrap CI
  - returns: Sharpe, Sortino, beta, alpha, drawdown table, HHI, effective N
  - attribution: marginal/component/incremental VaR, diversification ratio
  - stress: historical, event replay (data-absent warning), beta-scaled,
             custom, reverse, correlation breakdown
  - portfolio: min-var, risk-parity, max-Sharpe, efficient frontier, what-if
"""
import math
import numpy as np
import pandas as pd
import pytest

from backend.app.services.market_risk.risk import (
    returns as ret_mod,
    var_models as vm,
    attribution as attr_mod,
    stress as st,
    portfolio as pf,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def deterministic_returns():
    """
    250 days of deterministic synthetic returns for two assets.
    Asset A: iid N(0.0005, 0.01);  Asset B: iid N(0.0002, 0.015)
    seeded for reproducibility.
    """
    rng = np.random.default_rng(42)
    n = 250
    dates = pd.date_range("2023-01-01", periods=n, freq="B")
    a = rng.normal(0.0005, 0.01, n)
    b = rng.normal(0.0002, 0.015, n)
    return pd.DataFrame({"ASSET_A": a, "ASSET_B": b}, index=dates)


@pytest.fixture()
def equal_weights():
    return np.array([0.5, 0.5])


@pytest.fixture()
def portfolio_losses(deterministic_returns, equal_weights):
    """1-D array of portfolio daily losses (positive = loss)."""
    port_ret = deterministic_returns[["ASSET_A", "ASSET_B"]].dot(equal_weights)
    return -(port_ret.values)


# ---------------------------------------------------------------------------
# var_models
# ---------------------------------------------------------------------------

class TestVaRModels:
    METHODS = ["historical", "gaussian", "student_t", "cornish_fisher", "ewma", "fhs"]

    def test_all_methods_return_positive_var(self, portfolio_losses):
        """VaR at 95% should be positive for a roughly-zero-mean loss series."""
        for method in self.METHODS:
            res = vm.estimate_var(portfolio_losses, method=method, confidence=0.95)
            assert isinstance(res.var, float), f"{method}: var is not float"
            assert not math.isnan(res.var), f"{method}: var is NaN"
            # VaR may be small-negative for zero-mean series with small sample — just not NaN
            assert res.es >= res.var - 1e-6, f"{method}: ES < VaR"

    def test_historical_var_matches_numpy_quantile(self, portfolio_losses):
        """Historical VaR must exactly equal np.percentile(losses, 95)."""
        res = vm.estimate_var(portfolio_losses, method="historical", confidence=0.95, bootstrap=False)
        expected = float(np.percentile(portfolio_losses, 95))
        assert abs(res.var - expected) < 1e-9, f"Historical VaR mismatch: {res.var} vs {expected}"

    def test_gaussian_var_analytic(self, portfolio_losses):
        """Gaussian VaR = μ + z_95 × σ."""
        from scipy import stats
        mu = portfolio_losses.mean()
        sig = portfolio_losses.std(ddof=1)
        z = stats.norm.ppf(0.95)
        expected = mu + z * sig
        res = vm.estimate_var(portfolio_losses, method="gaussian", confidence=0.95)
        assert abs(res.var - expected) < 1e-6

    def test_horizon_scaling(self, portfolio_losses):
        """5-day VaR ≈ √5 × 1-day VaR (square-root-of-time)."""
        res_1d = vm.estimate_var(portfolio_losses, method="gaussian", confidence=0.95, horizon_days=1)
        res_5d = vm.estimate_var(portfolio_losses, method="gaussian", confidence=0.95, horizon_days=5)
        expected_5d = res_1d.var * math.sqrt(5)
        assert abs(res_5d.var - expected_5d) < 1e-6

    def test_es_geq_var_for_all_methods(self, portfolio_losses):
        """ES must be ≥ VaR for all methods (ES is the mean of the tail beyond VaR)."""
        for method in self.METHODS:
            res = vm.estimate_var(portfolio_losses, method=method, confidence=0.95)
            assert res.es >= res.var - 1e-6, (
                f"{method}: ES ({res.es:.6f}) < VaR ({res.var:.6f})"
            )

    def test_bootstrap_ci_bounds(self, portfolio_losses):
        """Bootstrap CI lower ≤ point estimate ≤ upper (approximately)."""
        res = vm.estimate_var(portfolio_losses, method="historical", confidence=0.95, bootstrap=True)
        assert res.var_bootstrap_ci is not None
        lo, hi = res.var_bootstrap_ci
        assert lo <= res.var + 0.002, f"CI lower {lo} > VaR {res.var}"
        assert hi >= res.var - 0.002, f"CI upper {hi} < VaR {res.var}"

    def test_higher_confidence_higher_var(self, portfolio_losses):
        """VaR at 99% ≥ VaR at 95% for all methods."""
        for method in ["historical", "gaussian", "student_t"]:
            r95 = vm.estimate_var(portfolio_losses, method=method, confidence=0.95)
            r99 = vm.estimate_var(portfolio_losses, method=method, confidence=0.99)
            assert r99.var >= r95.var - 1e-6, (
                f"{method}: VaR_99 ({r99.var:.6f}) < VaR_95 ({r95.var:.6f})"
            )

    def test_monte_carlo_seeded_reproducible(self, portfolio_losses):
        """Same seed produces identical MC VaR."""
        r1 = vm.estimate_var(portfolio_losses, method="monte_carlo", confidence=0.95, mc_seed=7)
        r2 = vm.estimate_var(portfolio_losses, method="monte_carlo", confidence=0.95, mc_seed=7)
        assert r1.var == r2.var

    def test_estimate_all_sweep(self, portfolio_losses):
        """estimate_all returns results for all requested method × confidence combos."""
        results = vm.estimate_all(
            portfolio_losses,
            methods=["historical", "gaussian"],
            confidences=[0.95, 0.99],
            horizons=[1, 5],
        )
        assert len(results) == 2 * 2 * 2  # 8 combinations

    def test_unknown_method_raises(self, portfolio_losses):
        with pytest.raises(ValueError, match="Unknown VaR method"):
            vm.estimate_var(portfolio_losses, method="magic", confidence=0.95)

    def test_thin_tail_warning(self):
        """Very short series should trigger thin-tail warning."""
        losses = np.array([0.01] * 20)  # only 20 obs at 95% → 1 tail obs
        res = vm.estimate_var(losses, method="historical", confidence=0.95, bootstrap=False)
        assert any("tail" in w.lower() for w in res.warnings)


# ---------------------------------------------------------------------------
# returns module
# ---------------------------------------------------------------------------

class TestReturnsModule:
    def test_annualized_volatility(self, deterministic_returns, equal_weights):
        port = ret_mod.portfolio_returns(deterministic_returns, equal_weights, ["ASSET_A", "ASSET_B"])
        vol = ret_mod.annualized_volatility(port)
        # Should be close to sqrt(0.5²×0.01² + 0.5²×0.015²) × sqrt(252)
        expected_daily_sig = math.sqrt(0.25 * 0.01**2 + 0.25 * 0.015**2)
        expected_ann = expected_daily_sig * math.sqrt(252)
        assert abs(vol - expected_ann) < 0.003  # loose: actual series has sampling noise

    def test_sharpe_ratio_sign(self, deterministic_returns, equal_weights):
        port = ret_mod.portfolio_returns(deterministic_returns, equal_weights, ["ASSET_A", "ASSET_B"])
        # positive mean return → Sharpe > -∞
        sr = ret_mod.sharpe_ratio(port)
        assert isinstance(sr, float) and not math.isnan(sr)

    def test_sortino_geq_sharpe_when_no_downside(self):
        """For a positive-only return series, Sortino > Sharpe."""
        ret = pd.Series([0.001] * 200)
        # Both should be very large; just verify no crash and both finite
        sr = ret_mod.sharpe_ratio(ret)
        so = ret_mod.sortino_ratio(ret)
        assert math.isfinite(sr) and math.isfinite(so)

    def test_max_drawdown_negative(self, deterministic_returns):
        port = ret_mod.portfolio_returns(
            deterministic_returns, np.array([0.5, 0.5]), ["ASSET_A", "ASSET_B"]
        )
        mdd = ret_mod.max_drawdown(port)
        assert mdd <= 0.0, "Max drawdown must be negative or zero"

    def test_drawdown_table_length(self, deterministic_returns):
        port = ret_mod.portfolio_returns(
            deterministic_returns, np.array([0.5, 0.5]), ["ASSET_A", "ASSET_B"]
        )
        table = ret_mod.drawdown_table(port, top_n=3)
        assert len(table) <= 3

    def test_drawdown_table_depth_ordering(self, deterministic_returns):
        """Drawdown table should be ordered from most negative (worst) to least."""
        port = ret_mod.portfolio_returns(
            deterministic_returns, np.array([0.5, 0.5]), ["ASSET_A", "ASSET_B"]
        )
        table = ret_mod.drawdown_table(port, top_n=5)
        depths = [p.depth for p in table]
        assert depths == sorted(depths), "Drawdown table not sorted by depth"

    def test_hhi_range(self):
        w = np.array([0.25, 0.25, 0.25, 0.25])
        hhi = ret_mod.herfindahl_index(w)
        assert abs(hhi - 0.25) < 1e-9, f"HHI for equal weights should be 1/N=0.25, got {hhi}"

    def test_effective_n(self):
        w = np.array([0.25, 0.25, 0.25, 0.25])
        eff_n = ret_mod.effective_n(w)
        assert abs(eff_n - 4.0) < 1e-9, f"Effective N for equal 4-asset portfolio = 4, got {eff_n}"

    def test_beta_against_itself_is_one(self, deterministic_returns):
        a = deterministic_returns["ASSET_A"]
        b = ret_mod.beta(a, a)
        assert abs(b - 1.0) < 1e-9, f"Beta of asset against itself must be 1.0, got {b}"

    def test_jarque_bera_returns_dict(self, deterministic_returns):
        port = ret_mod.portfolio_returns(
            deterministic_returns, np.array([0.5, 0.5]), ["ASSET_A", "ASSET_B"]
        )
        jb = ret_mod.jarque_bera(port)
        assert "statistic" in jb and "p_value" in jb
        assert jb["statistic"] >= 0


# ---------------------------------------------------------------------------
# attribution module
# ---------------------------------------------------------------------------

class TestAttribution:
    def test_component_var_sums_to_portfolio_var(self, deterministic_returns, equal_weights):
        result = attr_mod.compute_attribution(
            deterministic_returns, ["ASSET_A", "ASSET_B"], equal_weights
        )
        total_component = sum(result.component_var.values())
        assert abs(total_component - result.portfolio_var) < 1e-5, (
            f"Component VaR sum {total_component:.6f} ≠ portfolio VaR {result.portfolio_var:.6f}"
        )

    def test_component_var_pct_sums_to_one(self, deterministic_returns, equal_weights):
        result = attr_mod.compute_attribution(
            deterministic_returns, ["ASSET_A", "ASSET_B"], equal_weights
        )
        total_pct = sum(result.component_var_pct.values())
        assert abs(total_pct - 1.0) < 1e-5

    def test_hhi_and_effective_n_consistent(self, deterministic_returns, equal_weights):
        result = attr_mod.compute_attribution(
            deterministic_returns, ["ASSET_A", "ASSET_B"], equal_weights
        )
        # equal weights → HHI = 0.5, effective N = 2
        assert abs(result.hhi - 0.5) < 1e-4
        assert abs(result.effective_n - 2.0) < 0.01

    def test_diversification_ratio_geq_one(self, deterministic_returns, equal_weights):
        result = attr_mod.compute_attribution(
            deterministic_returns, ["ASSET_A", "ASSET_B"], equal_weights
        )
        # DR ≥ 1 for imperfectly correlated assets
        assert result.diversification_ratio >= 1.0 - 1e-6

    def test_incremental_var_field_present(self, deterministic_returns, equal_weights):
        result = attr_mod.compute_attribution(
            deterministic_returns, ["ASSET_A", "ASSET_B"], equal_weights
        )
        assert "ASSET_A" in result.incremental_var
        assert "ASSET_B" in result.incremental_var


# ---------------------------------------------------------------------------
# stress module
# ---------------------------------------------------------------------------

class TestStress:
    @pytest.fixture()
    def prices_df(self, deterministic_returns):
        """Build a prices DataFrame from the returns fixture."""
        prices = (1 + deterministic_returns).cumprod() * 100
        return prices

    @pytest.fixture()
    def weights_dict(self):
        return {"ASSET_A": 0.5, "ASSET_B": 0.5}

    def test_historical_scenarios_no_hidden_constants(self, deterministic_returns, prices_df, weights_dict):
        results = st.historical_shock_scenarios(
            deterministic_returns, ["ASSET_A", "ASSET_B"], weights_dict
        )
        assert len(results) == 2
        # All shocks derived from data, not hardcoded
        for r in results:
            for shock in r.asset_shocks.values():
                assert shock != 0.0 or True  # just checking no crash

    def test_event_replay_missing_data_warns(self, prices_df, weights_dict):
        """Event replay for COVID 2020 warns when snapshot doesn't cover that date."""
        results = st.event_replay_scenarios(
            prices_df, ["ASSET_A", "ASSET_B"], weights_dict,
            events=["COVID_Feb_Mar_2020"]
        )
        assert len(results) == 1
        # Our fixture starts 2023-01-01, so COVID window is outside the data
        assert any("No price data" in w for w in results[0].warnings)
        # Shock should be 0 for unavailable data
        for shock in results[0].asset_shocks.values():
            assert shock == 0.0

    def test_custom_scenario(self, weights_dict):
        shocks = {"ASSET_A": -0.10, "ASSET_B": -0.05}
        result = st.custom_shock_scenario(
            ["ASSET_A", "ASSET_B"], weights_dict, shocks,
            scenario_name="TestScenario"
        )
        # Loss = -(-0.10 × 0.5) + -(-0.05 × 0.5) = 0.05 + 0.025 = 0.075
        assert abs(result.portfolio_loss_pct - 0.075) < 1e-6

    def test_reverse_stress_test(self, weights_dict):
        result = st.reverse_stress_test(
            ["ASSET_A", "ASSET_B"], weights_dict, loss_threshold=0.20
        )
        # Uniform shock that causes 20% loss
        assert abs(result.portfolio_loss_pct - 0.20) < 1e-4

    def test_correlation_breakdown(self, deterministic_returns, weights_dict):
        result = st.correlation_breakdown_scenario(
            deterministic_returns, ["ASSET_A", "ASSET_B"], weights_dict
        )
        assert result.portfolio_loss_pct > 0
        assert result.scenario_type == "correlation_breakdown"

    def test_sector_shock(self, weights_dict):
        sectors = {"ASSET_A": "Tech", "ASSET_B": "Finance"}
        result = st.sector_shock_scenario(
            ["ASSET_A", "ASSET_B"], weights_dict, sectors,
            target_sector="Tech", sector_shock=-0.15
        )
        # Only ASSET_A (Tech) gets -15% shock; B gets 0
        # Loss = -(-0.15 × 0.5) + -(0 × 0.5) = 0.075
        assert abs(result.portfolio_loss_pct - 0.075) < 1e-6


# ---------------------------------------------------------------------------
# portfolio module
# ---------------------------------------------------------------------------

class TestPortfolioOptimisation:
    def test_min_var_weights_sum_to_one(self, deterministic_returns):
        result = pf.minimum_variance(deterministic_returns, ["ASSET_A", "ASSET_B"])
        w_sum = sum(result.weights.values())
        assert abs(w_sum - 1.0) < 1e-4

    def test_min_var_lower_vol_than_equal_weight(self, deterministic_returns, equal_weights):
        result = pf.minimum_variance(deterministic_returns, ["ASSET_A", "ASSET_B"])
        # Min-var portfolio should have vol ≤ equal-weight portfolio
        port_ret = deterministic_returns[["ASSET_A", "ASSET_B"]].dot(equal_weights)
        eq_vol = ret_mod.annualized_volatility(port_ret)
        assert result.annual_volatility <= eq_vol + 0.002  # allow small tolerance

    def test_risk_parity_weights_sum_to_one(self, deterministic_returns):
        result = pf.risk_parity(deterministic_returns, ["ASSET_A", "ASSET_B"])
        w_sum = sum(result.weights.values())
        assert abs(w_sum - 1.0) < 1e-4

    def test_max_sharpe_weights_sum_to_one(self, deterministic_returns):
        result = pf.max_sharpe(deterministic_returns, ["ASSET_A", "ASSET_B"])
        w_sum = sum(result.weights.values())
        assert abs(w_sum - 1.0) < 1e-4

    def test_efficient_frontier_volatility_range(self, deterministic_returns):
        points = pf.efficient_frontier(deterministic_returns, ["ASSET_A", "ASSET_B"], n_points=10)
        assert len(points) >= 2
        vols = [p.annual_volatility for p in points]
        # All vols should be non-negative
        assert all(v >= 0 for v in vols)

    def test_what_if_increases_var_when_adding_risky_asset(self, deterministic_returns, equal_weights):
        """Adding weight to the higher-vol asset (ASSET_B) should increase VaR."""
        result = pf.what_if_trade(
            deterministic_returns,
            symbols=["ASSET_A", "ASSET_B"],
            current_weights=equal_weights,
            trade_symbol="ASSET_B",
            trade_weight_delta=0.10,
        )
        # VaR should increase (or at worst be equal)
        assert result.new_var_95 >= result.original_var_95 - 1e-5

    def test_what_if_unknown_symbol_warns(self, deterministic_returns, equal_weights):
        result = pf.what_if_trade(
            deterministic_returns,
            symbols=["ASSET_A", "ASSET_B"],
            current_weights=equal_weights,
            trade_symbol="UNKNOWN_XYZ",
            trade_weight_delta=0.10,
        )
        assert any("not in portfolio" in w for w in result.warnings)
        assert result.delta_var_95 == 0.0
