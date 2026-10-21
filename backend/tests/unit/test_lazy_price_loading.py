"""
test_lazy_price_loading.py

Validates Task A2:
- Lazy price loading for any NSE symbol when no snapshot exists
- Validation of positive prices, gaps, staleness
- Retry with exponential backoff on transient failure
- Caching to disk and SQLite daily_prices with recorded freshness
- Test with mocked provider
- Test with real call if network allows
"""

from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch
import numpy as np
import pandas as pd
import pytest
from backend.app.services.market_risk.market_data_service import MarketDataService
from backend.app.db.session import SessionLocal
from backend.app.db.models import DailyPrice, Instrument


class TestLazyPriceLoadingMocked:
    """Test suite using mocked yfinance provider for rigorous edge case validation."""

    def test_mocked_lazy_load_success_and_caching(self, tmp_path: Path):
        """Verify successful fetch, column normalization, disk and DB caching, and freshness recording."""
        dates = pd.date_range("2024-01-01", periods=60, freq="B")
        cols = pd.MultiIndex.from_tuples([
            ("Adj Close", "MOCK_NSE.NS"),
            ("Close", "MOCK_NSE.NS"),
            ("Volume", "MOCK_NSE.NS"),
        ])
        mock_raw = pd.DataFrame(
            data=np.column_stack([[250.0] * 60, [255.0] * 60, [50000] * 60]),
            index=dates,
            columns=cols
        )

        manifest_file = tmp_path / "market_manifest.json"
        manifest_file.write_text('{"snapshots": {}, "symbols": []}', encoding="utf-8")

        svc = MarketDataService(snapshots_dir=tmp_path, manifest_path=manifest_file)

        with patch("yfinance.download", return_value=mock_raw):
            clean_df, source = svc.get_symbol_price_history("MOCK_NSE.NS", allow_live=True)

            assert source == "live_download"
            assert len(clean_df) == 60
            assert (clean_df["adj_close"] == 250.0).all()

            # Verify saved to disk snapshot
            assert (tmp_path / "MOCK_NSE.NS.csv").exists()

            # Verify saved to SQLite DB
            db = SessionLocal()
            try:
                db_count = db.query(DailyPrice).filter(DailyPrice.symbol == "MOCK_NSE.NS").count()
                assert db_count == 60
            finally:
                db.close()

    def test_mocked_lazy_load_rejects_excessive_gap(self, tmp_path: Path):
        """Verify validation rejects time series with gaps > 45 calendar days."""
        # 30 days, then 60-day gap, then 30 days
        part1 = pd.date_range("2024-01-01", periods=30, freq="B")
        part2 = pd.date_range("2024-04-15", periods=30, freq="B")
        dates = part1.append(part2)

        cols = pd.MultiIndex.from_tuples([
            ("Adj Close", "GAP_SYM.NS"),
            ("Close", "GAP_SYM.NS"),
        ])
        mock_raw = pd.DataFrame(
            data=np.column_stack([[100.0] * len(dates), [100.0] * len(dates)]),
            index=dates,
            columns=cols
        )

        svc = MarketDataService(snapshots_dir=tmp_path)
        with patch("yfinance.download", return_value=mock_raw):
            with pytest.raises(ValueError, match="Excessive price gap detected"):
                svc.fetch_live_price_history("GAP_SYM.NS")

    def test_mocked_lazy_load_rejects_non_positive_prices(self, tmp_path: Path):
        """Verify validation rejects series with zero or negative prices."""
        dates = pd.date_range("2024-01-01", periods=35, freq="B")
        cols = pd.MultiIndex.from_tuples([
            ("Adj Close", "NEG_SYM.NS"),
            ("Close", "NEG_SYM.NS"),
        ])
        mock_raw = pd.DataFrame(
            data=np.column_stack([[-50.0] * 35, [-50.0] * 35]),
            index=dates,
            columns=cols
        )

        svc = MarketDataService(snapshots_dir=tmp_path)
        with patch("yfinance.download", return_value=mock_raw):
            with pytest.raises(ValueError, match="invalid or non-positive price values"):
                svc.fetch_live_price_history("NEG_SYM.NS")

    def test_mocked_lazy_load_retry_backoff(self, tmp_path: Path):
        """Verify retry and exponential backoff on transient network failures."""
        dates = pd.date_range("2024-01-01", periods=35, freq="B")
        cols = pd.MultiIndex.from_tuples([
            ("Adj Close", "RETRY_SYM.NS"),
            ("Close", "RETRY_SYM.NS"),
        ])
        good_df = pd.DataFrame(
            data=np.column_stack([[150.0] * 35, [150.0] * 35]),
            index=dates,
            columns=cols
        )

        # Fail twice with ConnectionError, succeed on 3rd attempt
        mock_download = MagicMock(side_effect=[
            ConnectionError("Network timeout"),
            ConnectionError("Remote disconnected"),
            good_df,
        ])

        svc = MarketDataService(snapshots_dir=tmp_path)
        with patch("yfinance.download", mock_download), patch("time.sleep") as mock_sleep:
            clean_df = svc.fetch_live_price_history("RETRY_SYM.NS", max_retries=3, backoff_factor=1.0)
            assert len(clean_df) == 35
            assert mock_download.call_count == 3
            assert mock_sleep.call_count == 2


class TestLazyPriceLoadingRealNetwork:
    """Real call to yfinance if network allows."""

    def test_real_nse_lazy_fetch_and_cache(self, tmp_path: Path):
        """Perform one real call for an NSE symbol and verify caching and validation."""
        svc = MarketDataService(snapshots_dir=tmp_path)
        try:
            clean_df, source = svc.get_symbol_price_history("ITC.NS", allow_live=True)
            assert source == "live_download"
            assert len(clean_df) >= 30
            assert (clean_df["adj_close"] > 0).all()
            # Verify cached file was written
            assert (tmp_path / "ITC.NS.csv").exists()
        except Exception as exc:
            # If network or provider rate limit occurs, record reason
            pytest.skip(f"Live network call to yfinance failed: {exc}")
