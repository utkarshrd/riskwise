"""
backend/tests/unit/test_market_adj_close.py

Unit test proving that MarketRiskEngine strictly reads dividend/split adjusted
prices ('adj_close') rather than raw 'close', preventing artificial volatility
or return spikes from corporate actions.
"""

from pathlib import Path

import pandas as pd
import pytest
from backend.app.services.market_risk.engine import MarketRiskEngine


def test_market_engine_strictly_uses_adj_close(tmp_path: Path):
    """
    Construct a price history where 'close' has a 2-for-1 stock split drop (-50%),
    while 'adj_close' is correctly backward-adjusted (0% change).
    Assert that the engine consumes 'adj_close' and computes zero return.
    """
    # Create 35 days of dummy prices (to exceed minimum 30 observations requirement)
    dates = pd.date_range("2024-01-01", periods=35, freq="D")
    
    # Raw close has a 50% drop on day 15 (unadjusted split: 100 -> 50)
    close_prices = [100.0] * 15 + [50.0] * 20
    # Adjusted close is constant at 50.0 across all 35 days (split-adjusted)
    adj_close_prices = [50.0] * 35

    df = pd.DataFrame({
        "date": dates.strftime("%Y-%m-%d"),
        "close": close_prices,
        "adj_close": adj_close_prices,
        "volume": [1000000] * 35
    })

    test_file = tmp_path / "SPLIT_TEST.csv"
    df.to_csv(test_file, index=False)

    engine = MarketRiskEngine(snapshots_dir=tmp_path)
    loaded = engine.load_price_history(["SPLIT_TEST"])

    # Verify loaded values match adj_close, NOT close
    assert loaded["SPLIT_TEST"].iloc[0] == 50.0, (
        f"Expected adj_close value 50.0, got {loaded['SPLIT_TEST'].iloc[0]} (engine mistakenly loaded unadjusted close)"
    )
    assert (loaded["SPLIT_TEST"] == 50.0).all()

    # Calculate returns: must be all 0.0, NOT -0.50 on day 15
    returns = engine.calculate_returns(loaded, method="simple")
    assert (returns["SPLIT_TEST"] == 0.0).all(), (
        f"Expected 0.0 return across all days; got returns:\n{returns['SPLIT_TEST'].describe()}"
    )


def test_market_engine_rejects_missing_adj_close(tmp_path: Path):
    """
    Assert that MarketRiskEngine raises ValueError when a price snapshot
    is missing the 'adj_close' column.
    """
    dates = pd.date_range("2024-01-01", periods=35, freq="D")
    df = pd.DataFrame({
        "date": dates.strftime("%Y-%m-%d"),
        "close": [100.0] * 35,
        "volume": [1000000] * 35
    })

    test_file = tmp_path / "NO_ADJ.csv"
    df.to_csv(test_file, index=False)

    engine = MarketRiskEngine(snapshots_dir=tmp_path)
    with pytest.raises(ValueError, match="missing required dividend/split adjusted column 'adj_close'"):
        engine.load_price_history(["NO_ADJ"])
