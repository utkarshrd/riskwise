import math
from pathlib import Path

import pandas as pd
import pytest
from backend.app.services.market_risk.engine import Holding, MarketRiskEngine, StressScenario


def test_market_returns_simple_and_log_hand_calculated():
    """
    Hand-calculated return conventions test:
    Day 0: P0 = 100.0
    Day 1: P1 = 105.0 -> Simple R1 = (105 - 100) / 100 = 0.05000000
                         Log r1 = ln(105 / 100) = ln(1.05) = 0.04879016
    Day 2: P2 = 102.0 -> Simple R2 = (102 - 105) / 105 = -3 / 105 = -0.02857143
                         Log r2 = ln(102 / 105) = -0.02898832
    """
    prices = pd.DataFrame({
        "AAPL": [100.0, 105.0, 102.0]
    })
    simple_rets = MarketRiskEngine.calculate_returns(prices, method="simple")
    log_rets = MarketRiskEngine.calculate_returns(prices, method="log")

    # Simple returns verification
    assert abs(simple_rets["AAPL"].iloc[0] - 0.05) < 1e-6
    assert abs(simple_rets["AAPL"].iloc[1] - (-0.02857143)) < 1e-6

    # Log returns verification
    expected_log_1 = math.log(105.0 / 100.0)
    expected_log_2 = math.log(102.0 / 105.0)
    assert abs(log_rets["AAPL"].iloc[0] - expected_log_1) < 1e-6
    assert abs(log_rets["AAPL"].iloc[1] - expected_log_2) < 1e-6


def test_portfolio_analysis_with_snapshot_and_assumptions():
    engine = MarketRiskEngine()
    holdings = [
        Holding(symbol="SPY", weight=0.6),
        Holding(symbol="AAPL", weight=0.4)
    ]
    res = engine.analyze_portfolio(holdings=holdings, lookback_days=250)

    assert res.observations_count > 200
    assert res.annualized_volatility > 0.0
    assert res.annualization_factor == 252
    assert res.historical_var_95 > 0.0
    assert res.historical_var_99 >= res.historical_var_95
    assert res.expected_shortfall_95 >= res.historical_var_95
    assert res.parametric_var_95 > 0.0
    assert res.maximum_drawdown >= 0.0
    assert "SPY" in res.asset_correlations
    assert "AAPL" in res.asset_correlations

    # Verify assumptions are echoed
    assert res.assumptions["annualization_factor"] == 252
    assert res.assumptions["return_convention"] == "simple"
    assert res.assumptions["price_field"] == "adj_close"
    assert res.assumptions["weight_tolerance"] == 1e-4


def test_portfolio_weight_validation_strict():
    engine = MarketRiskEngine()
    # Weights sum to 0.70 instead of 1.0 -> should error (no silent normalization)
    holdings_short = [
        Holding(symbol="SPY", weight=0.4),
        Holding(symbol="AAPL", weight=0.3)
    ]
    with pytest.raises(ValueError, match="Holdings weights must sum to 1.0"):
        engine.analyze_portfolio(holdings=holdings_short)

    # Weights sum to 1.02 -> should error
    holdings_over = [
        Holding(symbol="SPY", weight=0.6),
        Holding(symbol="AAPL", weight=0.42)
    ]
    with pytest.raises(ValueError, match="Holdings weights must sum to 1.0"):
        engine.analyze_portfolio(holdings=holdings_over)


def test_portfolio_rejects_unknown_ticker():
    engine = MarketRiskEngine()
    holdings = [
        Holding(symbol="NONEXISTENT_TICKER", weight=1.0)
    ]
    with pytest.raises(FileNotFoundError, match="not found in"):
        engine.analyze_portfolio(holdings=holdings)


def test_portfolio_rejects_mixed_currencies():
    engine = MarketRiskEngine()
    # AAPL is USD, RELIANCE.NS is INR
    holdings = [
        Holding(symbol="AAPL", weight=0.5),
        Holding(symbol="RELIANCE.NS", weight=0.5)
    ]
    with pytest.raises(ValueError, match="Mixed-currency portfolio detected"):
        engine.analyze_portfolio(holdings=holdings)


def test_portfolio_rejects_non_positive_prices(tmp_path: Path):
    dates = pd.date_range("2024-01-01", periods=35, freq="D")
    df = pd.DataFrame({
        "date": dates.strftime("%Y-%m-%d"),
        "close": [10.0] * 34 + [0.0],  # Zero price on last day
        "adj_close": [10.0] * 34 + [0.0],
        "volume": [1000] * 35
    })
    df.to_csv(tmp_path / "ZERO_PRICE.csv", index=False)

    engine = MarketRiskEngine(snapshots_dir=tmp_path)
    with pytest.raises(ValueError, match="Non-positive price detected"):
        engine.load_price_history(["ZERO_PRICE"])


def test_stress_testing_shocks_and_assumptions():
    engine = MarketRiskEngine()
    holdings = [
        Holding(symbol="SPY", weight=0.5),
        Holding(symbol="AAPL", weight=0.5)
    ]
    scenarios = [
        StressScenario(
            name="Test_Shock",
            description="50% drop on AAPL, 20% drop on SPY",
            shocks={"AAPL": -0.50, "SPY": -0.20}
        )
    ]
    results = engine.run_stress_test(holdings=holdings, scenarios=scenarios)
    assert len(results) == 1
    # Total loss = 0.5 * (-0.20) + 0.5 * (-0.50) = -0.35 (-35%)
    assert abs(results[0].portfolio_loss_pct - (-0.35)) < 1e-4
    assert results[0].assumptions["scenario_derivation"] == "user_specified"


def test_stress_testing_derived_historical_shocks():
    """
    Ensure stress testing without custom scenarios derives shocks
    directly from real snapshot observations (worst 1-day and max drawdown),
    with zero hidden constants.
    """
    engine = MarketRiskEngine()
    holdings = [
        Holding(symbol="SPY", weight=0.6),
        Holding(symbol="AAPL", weight=0.4)
    ]
    results = engine.run_stress_test(holdings=holdings, scenarios=None)
    assert len(results) == 2
    scenario_names = [r.scenario_name for r in results]
    assert "Historical_Worst_Single_Day" in scenario_names
    assert "Historical_Peak_to_Trough_Drawdown" in scenario_names

    for r in results:
        assert r.portfolio_loss_pct < 0.0  # Must be a negative return / loss
        assert r.assumptions["scenario_derivation"] == "historical_snapshot_worst_window"
        assert "SPY" in r.individual_asset_losses
        assert "AAPL" in r.individual_asset_losses
