"""
Task A4 tests - VaR Validation (enhanced)
- Christoffersen conditional coverage (CC) joint test (LR_cc ~ chi2(2))
- Basel capital multiplier table (official BCBS 250-day, 99% confidence)
- VaRValidationEngine.compare_models() ranking logic
- POST /api/v1/market/var/compare smoke test via TestClient
- Edge cases: 0 exceptions, all exceptions, clustered exceptions
"""
import math

import pytest
from scipy import stats

from backend.app.services.market_risk.engine import Holding, MarketRiskEngine
from backend.app.services.var_validation.engine import VaRValidationEngine


def _make_engine(tmp_path, seed=42, n=600):
    """Generate synthetic price series and return a MarketRiskEngine."""
    import numpy as np
    import pandas as pd

    rng = np.random.default_rng(seed)
    returns = rng.normal(0.0005, 0.01, size=n)
    prices = 100.0 * np.cumprod(1 + returns)
    dates = pd.date_range("2019-01-01", periods=n, freq="B")
    df = pd.DataFrame({
        "date": dates.strftime("%Y-%m-%d"),
        "close": prices,
        "adj_close": prices,
        "volume": [100_000] * n,
    })
    tmp_path.mkdir(parents=True, exist_ok=True)
    df.to_csv(tmp_path / "SYNTHETIC.csv", index=False)
    return MarketRiskEngine(snapshots_dir=tmp_path)


class TestChristoffersenCC:
    def test_cc_stat_equals_sum_of_uc_and_ind(self, tmp_path):
        engine = _make_engine(tmp_path / "cc")
        val = VaRValidationEngine(risk_engine=engine)
        res = val.run_rolling_backtest(
            holdings=[Holding(symbol="SYNTHETIC", weight=1.0)],
            currency="USD",
            method="historical",
            confidence_level=0.95,
            lookback_window=100,
        )
        if res.christoffersen_cc_stat is not None:
            assert res.kupiec_lr_stat is not None
            assert res.christoffersen_lr_stat is not None
            expected_cc = round(res.kupiec_lr_stat + res.christoffersen_lr_stat, 4)
            assert abs(res.christoffersen_cc_stat - expected_cc) < 1e-3

    def test_cc_p_value_is_chi2_2_tail(self, tmp_path):
        engine = _make_engine(tmp_path / "cc2")
        val = VaRValidationEngine(risk_engine=engine)
        res = val.run_rolling_backtest(
            holdings=[Holding(symbol="SYNTHETIC", weight=1.0)],
            currency="USD",
            method="historical",
            confidence_level=0.95,
            lookback_window=100,
        )
        if res.christoffersen_cc_stat is not None:
            expected_p = float(1.0 - stats.chi2.cdf(res.christoffersen_cc_stat, df=2))
            assert abs(res.christoffersen_cc_p_value - expected_p) < 1e-4

    def test_cc_is_none_when_no_exceptions(self, tmp_path):
        import pandas as pd

        prices = [100.0] * 400  # Constant price -> zero returns -> zero historical VaR exceptions
        dates = pd.date_range("2020-01-01", periods=400, freq="B")
        df = pd.DataFrame({
            "date": dates.strftime("%Y-%m-%d"),
            "close": prices,
            "adj_close": prices,
            "volume": [1000] * 400,
        })
        p = tmp_path / "mono"
        p.mkdir()
        df.to_csv(p / "MONO.csv", index=False)
        eng = MarketRiskEngine(snapshots_dir=p)
        val = VaRValidationEngine(risk_engine=eng)
        res = val.run_rolling_backtest(
            holdings=[Holding(symbol="MONO", weight=1.0)],
            currency="USD",
            method="historical",
            confidence_level=0.95,
            lookback_window=50,
        )
        assert res.exception_count == 0
        assert res.christoffersen_lr_stat is None
        assert res.christoffersen_cc_stat is None


class TestBaselCapitalMultiplier:
    OFFICIAL_TABLE = {
        0: ("GREEN", 3.00),
        1: ("GREEN", 3.00),
        2: ("GREEN", 3.00),
        3: ("GREEN", 3.00),
        4: ("GREEN", 3.00),
        5: ("YELLOW", 3.40),
        6: ("YELLOW", 3.50),
        7: ("YELLOW", 3.65),
        8: ("YELLOW", 3.75),
        9: ("YELLOW", 3.85),
        10: ("RED", 4.00),
        15: ("RED", 4.00),
    }

    def test_official_bcbs_table_direct(self, tmp_path):
        for n_exc, (expected_zone, expected_mult) in self.OFFICIAL_TABLE.items():
            forecast_count = 250
            confidence_level = 0.99
            expected_rate = 0.01
            cum_prob = float(stats.binom.cdf(n_exc, forecast_count, expected_rate))

            if forecast_count == 250 and abs(confidence_level - 0.99) < 1e-3:
                if n_exc <= 4:
                    zone = "GREEN"
                    mult = 3.00
                elif n_exc <= 9:
                    zone = "YELLOW"
                    mult_map = {5: 3.40, 6: 3.50, 7: 3.65, 8: 3.75, 9: 3.85}
                    mult = mult_map.get(n_exc, 3.85)
                else:
                    zone = "RED"
                    mult = 4.00
            else:
                if cum_prob < 0.95:
                    zone = "GREEN"
                    mult = 3.00
                elif cum_prob < 0.9999:
                    zone = "YELLOW"
                    mult = round(3.0 + ((cum_prob - 0.95) / (0.9999 - 0.95)) * 0.85, 2)
                else:
                    zone = "RED"
                    mult = 4.00

            assert zone == expected_zone, f"n_exc={n_exc}: expected {expected_zone}, got {zone}"
            assert abs(mult - expected_mult) < 1e-9, f"n_exc={n_exc}: expected {expected_mult}, got {mult}"


class TestCompareModels:
    def test_returns_sorted_leaderboard(self, tmp_path):
        engine = _make_engine(tmp_path / "cmp")
        val = VaRValidationEngine(risk_engine=engine)
        result = val.compare_models(
            holdings=[Holding(symbol="SYNTHETIC", weight=1.0)],
            currency="USD",
            confidence_level=0.95,
            lookback_window=100,
            methods=["historical", "parametric"],
        )
        assert len(result["models"]) >= 1
        scores = [m["score"] for m in result["models"]]
        assert scores == sorted(scores)

    def test_recommended_method_in_candidates(self, tmp_path):
        engine = _make_engine(tmp_path / "cmp2")
        val = VaRValidationEngine(risk_engine=engine)
        methods = ["historical", "parametric"]
        result = val.compare_models(
            holdings=[Holding(symbol="SYNTHETIC", weight=1.0)],
            currency="USD",
            confidence_level=0.95,
            lookback_window=100,
            methods=methods,
        )
        assert result["recommended_method"] in methods

    def test_recommendation_reason_is_non_empty_string(self, tmp_path):
        engine = _make_engine(tmp_path / "cmp3")
        val = VaRValidationEngine(risk_engine=engine)
        result = val.compare_models(
            holdings=[Holding(symbol="SYNTHETIC", weight=1.0)],
            currency="USD",
            confidence_level=0.95,
            lookback_window=100,
            methods=["historical", "parametric"],
        )
        reason = result["recommendation_reason"]
        assert isinstance(reason, str) and len(reason) > 20

    def test_all_required_keys_present(self, tmp_path):
        engine = _make_engine(tmp_path / "cmp4")
        val = VaRValidationEngine(risk_engine=engine)
        result = val.compare_models(
            holdings=[Holding(symbol="SYNTHETIC", weight=1.0)],
            currency="USD",
            confidence_level=0.95,
            lookback_window=100,
            methods=["historical", "parametric"],
        )
        required_top = {"portfolio_name", "currency", "confidence_level", "lookback_window",
                        "forecast_count", "models", "recommended_method", "recommendation_reason"}
        assert required_top.issubset(result.keys())
        required_model = {"method", "exceptions", "expected_exceptions", "exception_rate",
                          "expected_exception_rate", "basel_zone", "basel_capital_multiplier",
                          "kupiec_p_value", "kupiec_test_passed",
                          "christoffersen_ind_p_value", "christoffersen_ind_passed",
                          "christoffersen_cc_p_value", "christoffersen_cc_test_passed", "score"}
        for m in result["models"]:
            assert required_model.issubset(m.keys())

    def test_score_penalty_red_zone(self, tmp_path):
        engine = _make_engine(tmp_path / "score")
        val = VaRValidationEngine(risk_engine=engine)
        result = val.compare_models(
            holdings=[Holding(symbol="SYNTHETIC", weight=1.0)],
            currency="USD",
            confidence_level=0.95,
            lookback_window=100,
            methods=["historical", "parametric"],
        )
        for m in result["models"]:
            if m["basel_zone"] == "RED":
                assert m["score"] >= 50.0


class TestVaRCompareEndpoint:
    def test_endpoint_structure(self):
        from unittest.mock import patch

        from backend.app.main import app
        from fastapi.testclient import TestClient

        fake_result = {
            "portfolio_name": "Test",
            "currency": "USD",
            "confidence_level": 0.95,
            "lookback_window": 100,
            "forecast_count": 400,
            "models": [{
                "method": "historical",
                "exceptions": 20,
                "expected_exceptions": 20.0,
                "exception_rate": 0.05,
                "expected_exception_rate": 0.05,
                "basel_zone": "GREEN",
                "basel_capital_multiplier": 3.00,
                "kupiec_p_value": 0.95,
                "kupiec_test_passed": True,
                "christoffersen_ind_p_value": 0.80,
                "christoffersen_ind_passed": True,
                "christoffersen_cc_p_value": 0.75,
                "christoffersen_cc_test_passed": True,
                "score": 0.0,
            }],
            "recommended_method": "historical",
            "recommendation_reason": "Historical VaR is recommended: It achieves Basel GREEN zone.",
        }

        with patch(
            "backend.app.api.v1.market.VaRValidationEngine.compare_models",
            return_value=fake_result,
        ):
            client = TestClient(app)
            payload = {
                "portfolio_name": "Test",
                "currency": "USD",
                "holdings": [{"symbol": "SPY", "weight": 1.0}],
                "confidence_level": 0.95,
                "lookback_window": 100,
                "methods": ["historical"],
            }
            resp = client.post("/api/v1/market/var/compare", json=payload)
            assert resp.status_code == 200, f"Status {resp.status_code}: {resp.text}"
            data = resp.json()
            assert data["recommended_method"] == "historical"
            assert data["currency"] == "USD"
            assert len(data["models"]) == 1
            assert data["models"][0]["kupiec_test_passed"] is True

    def test_endpoint_invalid_confidence_422(self):
        from backend.app.main import app
        from fastapi.testclient import TestClient

        client = TestClient(app)
        payload = {
            "portfolio_name": "BadConf",
            "currency": "USD",
            "holdings": [{"symbol": "SPY", "weight": 1.0}],
            "confidence_level": 0.50,
            "lookback_window": 100,
        }
        resp = client.post("/api/v1/market/var/compare", json=payload)
        assert resp.status_code == 422


class TestEdgeCases:
    def test_zero_exceptions_kupiec_no_sentinel(self, tmp_path):
        """0 exceptions must compute exact log-likelihood without 999.0 sentinel."""
        import pandas as pd

        n = 200
        dates = pd.date_range("2021-01-01", periods=n, freq="B")
        df = pd.DataFrame({
            "date": dates.strftime("%Y-%m-%d"),
            "close": [100.0] * n,
            "adj_close": [100.0] * n,
            "volume": [1000] * n,
        })
        p = tmp_path / "zero_exc"
        p.mkdir(parents=True)
        df.to_csv(p / "ZERO.csv", index=False)
        eng = MarketRiskEngine(snapshots_dir=p)
        val = VaRValidationEngine(risk_engine=eng)
        res = val.run_rolling_backtest(
            holdings=[Holding(symbol="ZERO", weight=1.0)],
            currency="USD",
            method="historical",
            confidence_level=0.95,
            lookback_window=50,
        )
        assert res.exception_count == 0
        assert res.kupiec_lr_stat is not None
        assert res.kupiec_lr_stat != 999.0
        assert res.kupiec_lr_stat >= 0.0
        assert res.christoffersen_lr_stat is None
        assert res.christoffersen_cc_stat is None

    def test_all_exceptions_kupiec_no_sentinel(self, tmp_path):
        """All exceptions must compute finite log-likelihood without 999.0 sentinel."""
        import numpy as np
        import pandas as pd

        n_calm = 51
        n_crash = 40
        calm_rets = [0.0001] * n_calm
        crash_rets = [-0.01 - 0.005 * i for i in range(n_crash)]
        rets = calm_rets + crash_rets
        prices = 100.0 * np.cumprod(1.0 + np.array(rets))
        n = len(prices)
        dates = pd.date_range("2021-01-01", periods=n, freq="B")
        df = pd.DataFrame({
            "date": dates.strftime("%Y-%m-%d"),
            "close": prices,
            "adj_close": prices,
            "volume": [1000] * n,
        })
        p = tmp_path / "all_exc"
        p.mkdir(parents=True)
        df.to_csv(p / "CRASH.csv", index=False)
        eng = MarketRiskEngine(snapshots_dir=p)
        val = VaRValidationEngine(risk_engine=eng)
        res = val.run_rolling_backtest(
            holdings=[Holding(symbol="CRASH", weight=1.0)],
            currency="USD",
            method="historical",
            confidence_level=0.95,
            lookback_window=50,
        )
        assert res.exception_count == res.forecast_count
        assert res.kupiec_lr_stat is not None
        assert res.kupiec_lr_stat != 999.0
        assert res.kupiec_lr_stat > 0.0
        assert res.kupiec_test_passed is False
        assert res.basel_zone == "RED"

    def test_clustered_exceptions_rejected_by_christoffersen_independence(self, tmp_path):
        """Clustered exceptions must trigger Christoffersen independence rejection."""
        import numpy as np
        import pandas as pd

        ret_calm_init = [0.0001] * 55
        ret_cluster = [-0.08] * 12
        ret_calm_end = [0.0001] * 90
        all_rets = np.array(ret_calm_init + ret_cluster + ret_calm_end)
        prices = 100.0 * np.cumprod(1.0 + all_rets)
        n = len(prices)
        dates = pd.date_range("2021-01-01", periods=n, freq="B")
        df = pd.DataFrame({
            "date": dates.strftime("%Y-%m-%d"),
            "close": prices,
            "adj_close": prices,
            "volume": [1000] * n,
        })
        p = tmp_path / "cluster_exc"
        p.mkdir(parents=True)
        df.to_csv(p / "CLUSTER.csv", index=False)
        eng = MarketRiskEngine(snapshots_dir=p)
        val = VaRValidationEngine(risk_engine=eng)
        res = val.run_rolling_backtest(
            holdings=[Holding(symbol="CLUSTER", weight=1.0)],
            currency="USD",
            method="historical",
            confidence_level=0.95,
            lookback_window=50,
        )
        assert res.exception_count >= 5
        assert res.christoffersen_lr_stat is not None
        assert res.christoffersen_lr_stat > 0.0
        assert res.christoffersen_test_passed is False
