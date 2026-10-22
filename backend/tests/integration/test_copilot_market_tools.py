"""Copilot market tools: replies cite computed numbers, and no figure appears unless a tool produced it."""

from datetime import date

import pandas as pd
import pytest
from backend.app.agents.copilot import RiskCopilotService, parse_target_loss_pct
from backend.app.agents.provenance import numbers_in
from backend.app.services.market_risk.stress import StressService


def series(points: dict[str, float]) -> pd.Series:
    return pd.Series(list(points.values()), index=pd.DatetimeIndex(list(points)), dtype=float)


class FakeProvider:
    """Hand-made event prices so the replay is offline. Returns drive the numbers the reply may quote."""

    source_label = "test_fixture"

    def __init__(self, fail: bool = False):
        self.fail = fail
        self.data = {
            "RELIANCE.NS": series({"2020-02-19": 100.0, "2020-03-23": 60.0, "2023-01-24": 100.0, "2023-02-28": 95.0, "2024-06-03": 100.0, "2024-06-04": 92.5}),
            "TCS.NS": series({"2020-02-19": 200.0, "2020-03-23": 150.0, "2023-01-24": 200.0, "2023-02-28": 190.0, "2024-06-03": 200.0, "2024-06-04": 200.5}),
        }

    def fetch(self, symbol: str, start: date, end: date) -> pd.Series:
        if self.fail:
            raise ValueError("the price provider could not be reached")
        return self.data.get(symbol, pd.Series(dtype=float, index=pd.DatetimeIndex([])))


@pytest.fixture(scope="module")
def service() -> RiskCopilotService:
    return RiskCopilotService(stress_service=StressService(provider=FakeProvider()))


PORTFOLIO = "60% reliance and 40% tcs"


# message, expected intent, expected first tool
CASES = [
    ("What is the EMI for 5 lakh at 10% for 3 years?", "CALCULATE_EMI", "calculate_emi"),
    (f"What is the market risk of {PORTFOLIO}?", "ANALYZE_PORTFOLIO_RISK", "analyze_portfolio"),
    ("Run a VaR backtest validation", "VALIDATE_VAR_MODEL", "validate_var_model"),
    ("Compare VaR models for equal weight spy and msft", "VAR_COMPARE", "var_compare"),
    (f"Replay covid and the adani sell-off on my portfolio of {PORTFOLIO}", "STRESS_REPLAY", "stress_replay"),
    ("Reverse stress my portfolio of 50% spy and 50% msft: what market fall gives a 20% loss?", "STRESS_REVERSE", "stress_reverse"),
]


@pytest.mark.parametrize("message, intent, tool", CASES)
def test_reply_is_routed_to_the_tool_and_every_figure_is_sourced(service, message, intent, tool):
    res = service.route_and_execute(message)

    assert res.intent == intent
    assert [t.tool_name for t in res.tool_trace] == [tool]
    assert res.tool_trace[0].is_authoritative
    assert res.provenance_flags == [], res.provenance_flags
    assert "[removed" not in res.answer
    assert numbers_in(res.answer), "a tool-backed reply should quote its computed figures"


def test_replay_reply_quotes_the_computed_losses_not_invented_ones(service):
    res = service.route_and_execute(f"Replay covid on my portfolio of {PORTFOLIO}")
    # 0.6 * (60/100 - 1) + 0.4 * (150/200 - 1) = -0.34
    assert "34.00%" in res.answer
    assert "40.00%" in res.answer and "25.00%" in res.answer  # the two holdings' own moves


def test_reverse_stress_reply_matches_the_tool_output(service):
    res = service.route_and_execute("Reverse stress my portfolio of 50% spy and 50% msft: what market fall gives a 20% loss?")
    out = res.tool_trace[0].output
    assert f"{abs(out['uniform_asset_shock']):.2%}" in res.answer
    assert f"{abs(out['implied_benchmark_shock']):.2%}" in res.answer
    assert f"{out['portfolio_beta']:.2f}" in res.answer


# ── the guard itself, end to end ────────────────────────────────────────────────


class InventsAFigure(RiskCopilotService):
    """Simulates a composer (or a future LLM step) that adds a number no tool produced."""

    def _node_answer_composition(self, state):
        out = super()._node_answer_composition(state)
        return {"answer": out["answer"] + "\n- **Sharpe ratio:** 2.41"}


def test_a_figure_with_no_source_is_removed_and_reported():
    svc = InventsAFigure()
    res = svc.route_and_execute(f"What is the market risk of {PORTFOLIO}?")

    assert "2.41" not in res.answer
    assert [f.token for f in res.provenance_flags] == ["2.41"]
    assert res.provenance_flags[0].action == "removed"
    # the genuine, sourced figures are untouched
    assert f"{res.tool_trace[0].output['annualized_volatility']:.2%}" in res.answer


def test_a_failed_tool_yields_no_numbers_and_says_why():
    svc = RiskCopilotService(stress_service=StressService(provider=FakeProvider(fail=True)))
    res = svc.route_and_execute(f"Replay covid on my portfolio of {PORTFOLIO}")

    assert res.tool_trace == []
    assert "could not complete" in res.answer and "price provider could not be reached" in res.answer
    assert numbers_in(res.answer) == []
    assert res.provenance_flags == []


# ── no silent substitution ──────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "message",
    [
        "Compare VaR models please",
        "Replay covid on my portfolio",
        "Reverse stress my portfolio: how far would the market fall for a 20% loss?",
    ],
)
def test_without_holdings_the_copilot_asks_instead_of_using_a_sample_portfolio(service, message):
    res = service.route_and_execute(message)
    assert res.tool_trace == []
    assert "does not substitute a sample portfolio" in res.answer


def test_reverse_stress_asks_for_the_target_loss_instead_of_assuming_one(service):
    res = service.route_and_execute("Reverse stress my portfolio of 50% spy and 50% msft, how far would the market fall?")
    assert res.tool_trace == []
    assert "does not assume a target loss" in res.answer


@pytest.mark.parametrize(
    "text, expected",
    [
        ("a 20% loss", 0.20),
        ("what if I lose 15%", 0.15),
        ("a drop of 30%", 0.30),
        ("12.5% drawdown", 0.125),
        ("no number here", None),
        ("a 150% loss", None),
        ("0% loss", None),
    ],
)
def test_target_loss_parsing(text, expected):
    assert parse_target_loss_pct(text) == expected


# ── routing does not steal existing intents ─────────────────────────────────────


def test_personal_finance_stress_still_routes_to_the_personal_stress_tool(service):
    res = service.route_and_execute(
        "Run a financial stress test: monthly income 80000, essential expenses 40000, discretionary 10000, liquid savings 200000"
    )
    assert res.intent == "PERSONAL_STRESS_TEST"


def test_event_words_without_a_portfolio_do_not_trigger_a_market_replay(service):
    res = service.route_and_execute("How did covid affect my household cash flow stress and savings runway?")
    assert res.intent != "STRESS_REPLAY"
