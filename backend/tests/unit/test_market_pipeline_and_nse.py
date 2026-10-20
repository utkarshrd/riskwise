from pathlib import Path
from unittest.mock import patch

import numpy as np
import pandas as pd
import pytest
from backend.app.main import app
from backend.app.services.market_risk.market_data_service import MarketDataService
from backend.app.services.market_risk.ticker_normalizer import (
    normalize_ticker,
)
from fastapi.testclient import TestClient


class TestTickerNormalization:
    """Tests for ticker normalization and currency inference."""

    def test_nse_suffix_preservation(self):
        norm = normalize_ticker("RELIANCE.NS")
        assert norm["canonical_symbol"] == "RELIANCE.NS"
        assert norm["currency"] == "INR"
        assert norm["exchange"] == "NSE"
        assert norm["file_stem"] == "RELIANCE.NS"

    def test_no_double_suffix(self):
        norm = normalize_ticker("RELIANCE.NS.NS")
        assert norm["canonical_symbol"] == "RELIANCE.NS"
        assert norm["currency"] == "INR"

    def test_lowercase_suffix(self):
        norm = normalize_ticker("tcs.ns")
        assert norm["canonical_symbol"] == "TCS.NS"
        assert norm["currency"] == "INR"

    def test_base_symbol_without_suffix(self):
        norm_rel = normalize_ticker("RELIANCE")
        assert norm_rel["canonical_symbol"] == "RELIANCE.NS"
        assert norm_rel["currency"] == "INR"

        norm_tcs = normalize_ticker("TCS")
        assert norm_tcs["canonical_symbol"] == "TCS.NS"
        assert norm_tcs["currency"] == "INR"

        norm_sbin = normalize_ticker("SBIN")
        assert norm_sbin["canonical_symbol"] == "SBIN.NS"
        assert norm_sbin["currency"] == "INR"

    def test_bse_suffix_distinction(self):
        norm_bse = normalize_ticker("TCS.BO")
        assert norm_bse["canonical_symbol"] == "TCS.BO"
        assert norm_bse["currency"] == "INR"
        assert norm_bse["exchange"] == "BSE"

    def test_nifty_index_normalization(self):
        for index_alias in ["^NSEI", "_NSEI", "NIFTY", "NIFTY50", "NSEI"]:
            norm = normalize_ticker(index_alias)
            assert norm["canonical_symbol"] == "^NSEI"
            assert norm["currency"] == "INR"
            assert norm["file_stem"] == "_NSEI"

    def test_us_equities(self):
        for sym in ["AAPL", "MSFT", "SPY", "GOOGL"]:
            norm = normalize_ticker(sym)
            assert norm["canonical_symbol"] == sym
            assert norm["currency"] == "USD"
            assert norm["file_stem"] == sym

    def test_empty_ticker_rejected(self):
        with pytest.raises(ValueError, match="Ticker symbol cannot be empty"):
            normalize_ticker("   ")


class TestMarketDataService:
    """Tests for price loading, provider response parsing, and error handling."""

    def test_read_cached_file_uses_adj_close(self, tmp_path: Path):
        dates = pd.date_range("2024-01-01", periods=35, freq="D")
        df = pd.DataFrame({
            "date": dates.strftime("%Y-%m-%d"),
            "close": [100.0] * 35,
            "adj_close": [50.0] * 35,
            "volume": [1000] * 35,
        })
        test_file = tmp_path / "TEST_STOCK.NS.csv"
        df.to_csv(test_file, index=False)

        svc = MarketDataService(snapshots_dir=tmp_path)
        loaded = svc._read_cached_file(test_file, "TEST_STOCK.NS")
        assert (loaded["adj_close"] == 50.0).all()
        assert len(loaded) == 35

    def test_missing_adj_close_raises_error(self, tmp_path: Path):
        dates = pd.date_range("2024-01-01", periods=35, freq="D")
        df = pd.DataFrame({
            "date": dates.strftime("%Y-%m-%d"),
            "close": [100.0] * 35,
            "volume": [1000] * 35,
        })
        test_file = tmp_path / "NO_ADJ.NS.csv"
        df.to_csv(test_file, index=False)

        svc = MarketDataService(snapshots_dir=tmp_path)
        with pytest.raises(ValueError, match="missing required dividend/split adjusted column 'adj_close'"):
            svc._read_cached_file(test_file, "NO_ADJ.NS")

    def test_non_positive_price_raises_error(self, tmp_path: Path):
        dates = pd.date_range("2024-01-01", periods=35, freq="D")
        df = pd.DataFrame({
            "date": dates.strftime("%Y-%m-%d"),
            "close": [10.0] * 34 + [-1.0],
            "adj_close": [10.0] * 34 + [-1.0],
            "volume": [1000] * 35,
        })
        test_file = tmp_path / "NEGATIVE_PRICE.NS.csv"
        df.to_csv(test_file, index=False)

        svc = MarketDataService(snapshots_dir=tmp_path)
        with pytest.raises(ValueError, match="Non-positive price detected in snapshot"):
            svc._read_cached_file(test_file, "NEGATIVE_PRICE.NS")

    def test_currency_mismatch_rejected(self, tmp_path: Path):
        dates = pd.date_range("2024-01-01", periods=35, freq="D")
        df_inr = pd.DataFrame({
            "date": dates.strftime("%Y-%m-%d"),
            "adj_close": [100.0] * 35,
            "close": [100.0] * 35,
        })
        df_inr.to_csv(tmp_path / "RELIANCE.NS.csv", index=False)

        df_usd = pd.DataFrame({
            "date": dates.strftime("%Y-%m-%d"),
            "adj_close": [150.0] * 35,
            "close": [150.0] * 35,
        })
        df_usd.to_csv(tmp_path / "AAPL.csv", index=False)

        svc = MarketDataService(snapshots_dir=tmp_path)
        with pytest.raises(ValueError, match="Mixed-currency portfolio detected"):
            svc.load_aligned_prices(["RELIANCE.NS", "AAPL"], allow_live=False)

    def test_insufficient_history_rejected(self, tmp_path: Path):
        dates = pd.date_range("2024-01-01", periods=15, freq="D")  # Only 15 days
        df = pd.DataFrame({
            "date": dates.strftime("%Y-%m-%d"),
            "adj_close": [100.0] * 15,
            "close": [100.0] * 15,
        })
        df.to_csv(tmp_path / "SHORT_HIST.NS.csv", index=False)

        svc = MarketDataService(snapshots_dir=tmp_path)
        with pytest.raises(ValueError, match="Insufficient common trading dates"):
            svc.load_aligned_prices(["SHORT_HIST.NS"], allow_live=False)

    def test_mock_live_provider_download_and_multiindex_parsing(self, tmp_path: Path):
        """Verify MultiIndex column flattening and price caching from live provider."""
        dates = pd.date_range("2024-01-01", periods=35, freq="D")
        cols = pd.MultiIndex.from_tuples([
            ("Adj Close", "TEST_SYM.NS"),
            ("Close", "TEST_SYM.NS"),
            ("Volume", "TEST_SYM.NS"),
        ])
        mock_raw = pd.DataFrame(
            data=np.column_stack([[500.0] * 35, [505.0] * 35, [10000] * 35]),
            index=dates,
            columns=cols
        )

        svc = MarketDataService(snapshots_dir=tmp_path)
        with patch("yfinance.download", return_value=mock_raw):
            clean = svc.fetch_live_price_history("TEST_SYM.NS")
            assert len(clean) == 35
            assert (clean["adj_close"] == 500.0).all()
            assert (tmp_path / "TEST_SYM.NS.csv").exists()

    def test_empty_provider_response_raises_error(self, tmp_path: Path):
        svc = MarketDataService(snapshots_dir=tmp_path)
        with (
            patch("yfinance.download", return_value=pd.DataFrame()),
            pytest.raises(ValueError, match="Provider returned empty price history"),
        ):
            svc.fetch_live_price_history("INVALID_TICKER.NS")


class TestStockSearchEndpoint:
    """Tests for the stock search API endpoint."""

    @pytest.fixture
    def client(self):
        return TestClient(app)

    def test_search_nse_equities(self, client):
        res = client.get("/api/v1/market/search?q=reliance")
        assert res.status_code == 200
        data = res.json()
        assert data["query"] == "reliance"
        symbols = [r["symbol"] for r in data["results"]]
        assert "RELIANCE.NS" in symbols
        reliance_meta = next(r for r in data["results"] if r["symbol"] == "RELIANCE.NS")
        assert reliance_meta["currency"] == "INR"
        assert reliance_meta["exchange"] == "NSE"

    def test_search_tcs(self, client):
        res = client.get("/api/v1/market/search?q=tcs")
        assert res.status_code == 200
        symbols = [r["symbol"] for r in res.json()["results"]]
        assert "TCS.NS" in symbols

    def test_search_index_nifty(self, client):
        res = client.get("/api/v1/market/search?q=nifty")
        assert res.status_code == 200
        symbols = [r["symbol"] for r in res.json()["results"]]
        assert "^NSEI" in symbols or "NIFTYBEES.NS" in symbols


class TestCustomPortfolioRiskAssessment:
    """Tests running actual risk metrics and backtests with custom NSE holdings."""

    @pytest.fixture
    def client(self):
        return TestClient(app)

    def test_analyze_custom_nse_portfolio(self, client):
        res = client.post("/api/v1/market/portfolio/analyze", json={
            "portfolio_name": "Indian IT & Conglomerate",
            "currency": "INR",
            "holdings": [
                {"symbol": "RELIANCE.NS", "weight": 0.5},
                {"symbol": "TCS.NS", "weight": 0.5}
            ],
            "portfolio_value": 2000000,
            "lookback_days": 252
        })
        assert res.status_code == 200
        metrics = res.json()
        assert metrics["currency"] == "INR"
        assert metrics["annualized_volatility"] > 0.0
        assert metrics["historical_var_95"] > 0.0
        assert metrics["historical_var_95_amount"] is not None
        assert metrics["historical_var_95_amount"] > 0.0
        assert metrics["parametric_var_95"] > 0.0
        assert metrics["expected_shortfall_95"] >= metrics["historical_var_95"]

    def test_currency_mismatch_error_message(self, client):
        res = client.post("/api/v1/market/portfolio/analyze", json={
            "portfolio_name": "Mixed Test",
            "currency": "INR",
            "holdings": [
                {"symbol": "RELIANCE.NS", "weight": 0.5},
                {"symbol": "AAPL", "weight": 0.5}
            ],
            "portfolio_value": 100000
        })
        assert res.status_code == 400
        detail = res.json()["detail"]
        assert "Mixed-currency portfolio detected" in detail["message"]

    def test_var_validation_custom_nse_backtest(self, client):
        res = client.post("/api/v1/market/var/validate", json={
            "portfolio_name": "Custom NSE Validation",
            "currency": "INR",
            "holdings": [
                {"symbol": "RELIANCE.NS", "weight": 0.6},
                {"symbol": "TCS.NS", "weight": 0.4}
            ],
            "method": "historical",
            "confidence_level": 0.95,
            "lookback_window": 100
        })
        assert res.status_code == 200
        val = res.json()
        assert val["currency"] == "INR"
        assert val["forecast_count"] > 300
        assert val["basel_zone"] in ["GREEN", "YELLOW", "RED"]
        assert val["kupiec_p_value"] is not None
        assert len(val["validation_points"]) == val["forecast_count"]


class TestSymbolValidationAndThreeStates:
    """Tests for Phase 4 & 5: Three symbol states, aliases, and dynamic validation."""

    @pytest.fixture
    def client(self):
        return TestClient(app)

    def test_validate_symbol_verified_snapshot(self):
        svc = MarketDataService()
        res = svc.validate_symbol("RELIANCE.NS", target_currency="INR")
        assert res["state"] == "verified_snapshot"
        assert res["is_cached"] is True
        assert res["observations_count"] > 200
        assert res["currency"] == "INR"

    def test_validate_symbol_invalid(self):
        svc = MarketDataService()
        res = svc.validate_symbol("INVALID_TICKER_XYZ999", target_currency="USD")
        assert res["state"] == "not_available"
        assert res["is_cached"] is False
        assert res["error_reason"] is not None

    def test_corporate_alias_zomato(self):
        norm = normalize_ticker("ZOMATO")
        assert norm["canonical_symbol"] == "ETERNAL.NS"
        assert norm["currency"] == "INR"
        assert norm["exchange"] == "NSE"

    def test_corporate_alias_tatamotors(self):
        norm = normalize_ticker("TATAMOTORS")
        assert norm["canonical_symbol"] == "TMCV.NS"
        assert norm["currency"] == "INR"
        assert norm["exchange"] == "NSE"

    def test_currency_hint_infers_nse_for_unsuffixed(self):
        norm = normalize_ticker("ADANIENT", currency_hint="INR")
        assert norm["canonical_symbol"] == "ADANIENT.NS"
        assert norm["currency"] == "INR"
        assert norm["exchange"] == "NSE"

    def test_validate_symbol_endpoint_post(self, client):
        res = client.post("/api/v1/market/validate-symbol", json={
            "symbol": "TCS.NS",
            "target_currency": "INR"
        })
        assert res.status_code == 200
        data = res.json()
        assert data["canonical_symbol"] == "TCS.NS"
        assert data["currency"] == "INR"
        assert data["state"] == "verified_snapshot"
        assert data["is_cached"] is True
        assert data["observations_count"] > 100

    def test_search_with_currency_hint_candidates(self, client):
        res = client.get("/api/v1/market/search?q=zomato&currency=INR")
        assert res.status_code == 200
        data = res.json()
        symbols = [r["symbol"] for r in data["results"]]
        assert "ETERNAL.NS" in symbols

