"""Named historical replays and reverse stress. Prices here are fixtures chosen so the expected answers can be computed by hand."""

from datetime import date

import pandas as pd
import pytest
from backend.app.api.v1.market import get_stress_service
from backend.app.main import app
from backend.app.services.market_risk.engine import Holding
from backend.app.services.market_risk.stress import SCENARIO_WINDOWS, FX_SYMBOL, StressService
from fastapi.testclient import TestClient

client = TestClient(app)

COVID = SCENARIO_WINDOWS["covid_2020"]  # 2020-02-19 .. 2020-03-23


def series(points: dict[str, float]) -> pd.Series:
    return pd.Series(list(points.values()), index=pd.DatetimeIndex(list(points)), dtype=float)


class FakeProvider:
    source_label = "test_fixture"

    def __init__(self, data: dict[str, pd.Series]):
        self.data = data

    def fetch(self, symbol: str, start: date, end: date) -> pd.Series:
        return self.data.get(symbol, pd.Series(dtype=float, index=pd.DatetimeIndex([])))


def two_stock_provider() -> FakeProvider:
    return FakeProvider(
        {
            # 19 Feb is a Wednesday; the base close is that day. 23 Mar is the end.
            "AAA.NS": series({"2020-02-18": 105.0, "2020-02-19": 100.0, "2020-03-10": 70.0, "2020-03-23": 80.0}),
            "BBB.NS": series({"2020-02-19": 200.0, "2020-03-12": 150.0, "2020-03-23": 180.0}),
        }
    )


def holdings(**weights: float) -> list[Holding]:
    return [Holding(symbol=f"{sym}.NS", weight=w) for sym, w in weights.items()]


def covid(results):
    return next(r for r in results if r["id"] == "covid_2020")


# ── replay ──────────────────────────────────────────────────────────────────────


def test_replay_portfolio_return_is_the_weighted_sum_of_holding_returns():
    svc = StressService(provider=two_stock_provider())
    r = covid(svc.replay(holdings(AAA=0.6, BBB=0.4), "INR", scenario_ids=["covid_2020"], portfolio_value=1_000_000))

    assert r["status"] == "ok" and r["skipped"] == []
    by = {c["symbol"]: c for c in r["contributions"]}
    assert by["AAA.NS"]["return"] == pytest.approx(-0.20)  # 80 / 100 - 1
    assert by["BBB.NS"]["return"] == pytest.approx(-0.10)  # 180 / 200 - 1
    assert r["portfolio_return"] == pytest.approx(0.6 * -0.20 + 0.4 * -0.10)  # -0.16
    assert r["portfolio_loss_pct"] == pytest.approx(0.16)
    assert r["portfolio_loss_amount"] == pytest.approx(160_000)
    assert sum(c["contribution"] for c in r["contributions"]) == pytest.approx(r["portfolio_return"])
    # the lowest close inside the window is reported separately from the end-of-window return
    assert by["AAA.NS"]["trough_return"] == pytest.approx(-0.30)


def test_base_price_is_the_last_close_on_or_before_the_window_start():
    provider = FakeProvider({"AAA.NS": series({"2020-02-14": 90.0, "2020-02-21": 95.0, "2020-03-23": 99.0})})
    r = covid(StressService(provider=provider).replay(holdings(AAA=1.0), "INR", scenario_ids=["covid_2020"]))
    c = r["contributions"][0]
    assert c["start_date"] == "2020-02-14"  # 19 Feb has no quote; 21 Feb is after the start and must not be used
    assert c["start_price"] == 90.0
    assert c["return"] == pytest.approx(99.0 / 90.0 - 1)


def test_holdings_without_data_are_skipped_reported_and_weights_renormalised():
    provider = two_stock_provider()
    provider.data["NEW.NS"] = series({"2021-11-23": 50.0})  # first listed after the window
    # CCC has no data at all
    svc = StressService(provider=provider)
    r = covid(svc.replay(holdings(AAA=0.3, BBB=0.2, NEW=0.3, CCC=0.2), "INR", scenario_ids=["covid_2020"]))

    skipped = {s["symbol"]: s["reason"] for s in r["skipped"]}
    assert set(skipped) == {"NEW.NS", "CCC.NS"}
    assert "first available close is 2021-11-23" in skipped["NEW.NS"]
    assert "no data" in skipped["CCC.NS"].lower()

    assert r["covered_weight"] == pytest.approx(0.5)
    # AAA and BBB re-weighted to 0.6 / 0.4 of the covered part
    assert r["portfolio_return"] == pytest.approx(0.6 * -0.20 + 0.4 * -0.10)


def test_scenario_is_unavailable_when_no_holding_has_data():
    r = covid(StressService(provider=FakeProvider({})).replay(holdings(AAA=1.0), "INR", scenario_ids=["covid_2020"]))
    assert r["status"] == "unavailable"
    assert r["portfolio_loss_pct"] is None and r["contributions"] == []
    assert len(r["skipped"]) == 1


def test_all_three_named_scenarios_are_replayed_by_default():
    prices = series({"2020-02-19": 100.0, "2020-03-23": 60.0, "2023-01-24": 100.0, "2023-02-28": 50.0, "2024-06-03": 100.0, "2024-06-04": 90.0})
    results = StressService(provider=FakeProvider({"AAA.NS": prices})).replay(holdings(AAA=1.0), "INR")
    assert [r["id"] for r in results] == ["covid_2020", "election_2024", "adani_2023"]
    losses = {r["id"]: r["portfolio_loss_pct"] for r in results}
    assert losses == {"covid_2020": pytest.approx(0.4), "election_2024": pytest.approx(0.1), "adani_2023": pytest.approx(0.5)}


def test_unknown_scenario_id_is_rejected():
    with pytest.raises(ValueError, match="Unknown scenario"):
        StressService(provider=two_stock_provider()).replay(holdings(AAA=1.0), "INR", scenario_ids=["dotcom"])


def test_mixed_currencies_need_the_fx_opt_in_and_are_then_converted_with_that_days_rate():
    provider = FakeProvider(
        {
            "SPY": series({"2020-02-19": 300.0, "2020-03-23": 220.0}),
            "AAA.NS": series({"2020-02-19": 100.0, "2020-03-23": 80.0}),
            FX_SYMBOL: series({"2020-02-19": 71.0, "2020-03-23": 76.0}),
        }
    )
    svc = StressService(provider=provider)
    mixed = [Holding(symbol="SPY", weight=0.5), Holding(symbol="AAA.NS", weight=0.5)]

    with pytest.raises(ValueError, match="fx_mode"):
        svc.replay(mixed, "INR", scenario_ids=["covid_2020"])

    r = covid(svc.replay(mixed, "INR", fx_mode="convert_to_base", scenario_ids=["covid_2020"]))
    spy = next(c for c in r["contributions"] if c["symbol"] == "SPY")
    assert spy["start_price"] == pytest.approx(300 * 71)
    assert spy["return"] == pytest.approx((220 * 76) / (300 * 71) - 1)  # USD fall partly offset by a weaker rupee
    assert r["fx"]["fx_converted"] is True and r["fx"]["fx_pair"] == FX_SYMBOL


# ── API ─────────────────────────────────────────────────────────────────────────


@pytest.fixture
def fake_provider_api():
    app.dependency_overrides[get_stress_service] = lambda: StressService(provider=two_stock_provider())
    yield
    app.dependency_overrides.pop(get_stress_service, None)


def test_replay_endpoint_returns_contributions_under_the_return_key(fake_provider_api):
    res = client.post(
        "/api/v1/market/portfolio/stress/replay",
        json={"holdings": [{"symbol": "AAA.NS", "weight": 0.6}, {"symbol": "BBB.NS", "weight": 0.4}], "currency": "INR", "scenarios": ["covid_2020"]},
    )
    assert res.status_code == 200
    body = res.json()[0]
    assert body["window_start"] == "2020-02-19" and body["window_end"] == "2020-03-23"
    assert body["contributions"][0]["return"] == pytest.approx(-0.20)
    assert body["data_source"] == "test_fixture"


def test_replay_endpoint_rejects_unknown_scenarios(fake_provider_api):
    res = client.post(
        "/api/v1/market/portfolio/stress/replay",
        json={"holdings": [{"symbol": "AAA.NS", "weight": 1.0}], "currency": "INR", "scenarios": ["nope"]},
    )
    assert res.status_code == 400


# ── reverse stress (uses the committed price snapshots) ─────────────────────────


def reverse(**kw):
    base = {"holdings": [{"symbol": "SPY", "weight": 0.5}, {"symbol": "AAPL", "weight": 0.5}], "currency": "USD", **kw}
    return client.post("/api/v1/market/portfolio/stress/reverse", json=base)


def test_reverse_stress_inverts_the_portfolio_beta():
    res = reverse(target_loss_pct=0.20)
    assert res.status_code == 200
    b = res.json()

    assert b["uniform_asset_shock"] == pytest.approx(-0.20)
    assert sum(r["contribution"] for r in b["uniform_contributions"]) == pytest.approx(-0.20, abs=1e-5)

    beta = sum(r["weight"] * r["beta"] for r in b["beta_contributions"])
    assert b["portfolio_beta"] == pytest.approx(beta, abs=1e-3)
    assert b["implied_benchmark_shock"] * b["portfolio_beta"] == pytest.approx(-0.20, abs=2e-3)
    # the per-holding moves under the implied benchmark shock add back up to the target loss
    assert sum(r["contribution"] for r in b["beta_contributions"]) == pytest.approx(-0.20, abs=1e-5)


def test_reverse_stress_for_the_benchmark_itself_has_beta_one():
    b = reverse(holdings=[{"symbol": "SPY", "weight": 1.0}], target_loss_pct=0.10).json()
    assert b["portfolio_beta"] == pytest.approx(1.0)
    assert b["implied_benchmark_shock"] == pytest.approx(-0.10)


def test_reverse_stress_accepts_a_loss_amount():
    b = reverse(target_loss_amount=25_000, portfolio_value=100_000).json()
    assert b["target_loss_pct"] == pytest.approx(0.25)
    assert b["target_loss_amount"] == pytest.approx(25_000)


@pytest.mark.parametrize(
    "extra",
    [
        {},  # no target
        {"target_loss_pct": 0.1, "target_loss_amount": 5000, "portfolio_value": 100_000},  # both
        {"target_loss_amount": 5000},  # amount without a value
    ],
)
def test_reverse_stress_requires_exactly_one_usable_target(extra):
    assert reverse(**extra).status_code == 400


@pytest.mark.parametrize("pct", [0.0, 1.0, 1.5, -0.1])
def test_reverse_stress_rejects_losses_outside_zero_to_one(pct):
    assert reverse(target_loss_pct=pct).status_code == 422


def test_reverse_stress_has_no_warning_when_the_implied_fall_is_representable():
    b = reverse(holdings=[{"symbol": "SPY", "weight": 1.0}], target_loss_pct=0.90).json()
    assert b["implied_benchmark_shock"] == pytest.approx(-0.90)
    assert b["note"] is None


@pytest.mark.parametrize(
    "benchmark_shock, holding_shocks, warns",
    [
        (-0.40, [-0.30, -0.55], False),
        (-0.40, [-0.30, -1.00], True),  # a holding at exactly -100%
        (-0.40, [-0.30, -1.25], True),  # a high-beta holding past a total loss
        (-1.05, [-0.50], True),  # the benchmark itself
    ],
)
def test_beta_model_warning_rule(benchmark_shock, holding_shocks, warns):
    from backend.app.services.market_risk.stress import beta_model_warning

    assert (beta_model_warning(benchmark_shock, holding_shocks) is not None) is warns
