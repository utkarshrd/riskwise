"""The provenance guard: no figure survives in a reply unless a tool, citation or the user supplied it."""

import pytest
from backend.app.agents.provenance import check_answer, numbers_in

OUT = {"annualized_volatility": 0.1587, "historical_var_95": 0.0308, "observations_count": 251, "start_date": "2025-10-13"}


def kept(answer, sources=(OUT,), user=""):
    return check_answer(answer, list(sources), user)


# ── parsing ─────────────────────────────────────────────────────────────────────


def test_number_parsing_handles_indian_grouping_percentages_dates_and_symbol_digits():
    toks = numbers_in("Loan ₹3,24,734 (₹324,734.19) at 8.50% on 2025-10-13, see §1.5 and 3MINDIA.NS")
    assert [(t, v) for t, v, _ in toks] == [("3,24,734", 324734.0), ("324,734.19", 324734.19), ("8.50", 8.5)]
    assert toks[2][2] == 2  # decimals recorded so rounding tolerance matches what was displayed


# ── accepted: traceable to a source ─────────────────────────────────────────────


def test_fraction_shown_as_percentage_is_accepted():
    r = kept("Historical VaR (95%): 3.08%")
    assert r.flags == [] and r.answer == "Historical VaR (95%): 3.08%"


def test_rounding_to_the_displayed_precision_is_accepted():
    assert kept("Volatility is 15.87%").flags == []
    assert kept("Volatility is 15.9%").flags == []  # 15.87 rounded to one decimal
    assert kept("Volatility is 16%").flags == []  # and to a whole number


def test_integers_from_tool_output_and_dates_are_accepted():
    r = kept("Window: 251 trading days from 2025-10-13")
    assert r.flags == []


def test_numbers_the_user_gave_are_accepted():
    r = kept("You asked about a 20% loss over 250 days.", sources=[], user="what if I lose 20% over 250 days?")
    assert r.flags == []


def test_months_shown_as_years_is_accepted():
    assert kept("Tenure: 36 months (3.0 years)", sources=[{"tenure_months": 36}]).flags == []


def test_methodology_constants_and_section_references_are_accepted():
    assert kept("Annualised on a 252 trading-day convention. See PRD §1.5.", sources=[]).flags == []


def test_numbers_inside_tool_text_fields_and_keys_are_accepted():
    r = kept("Source RBI-2023 mentions 97% coverage", sources=[{"label": "RBI-2023 note"}, {"coverage_97": 1}])
    assert r.flags == []


# ── rejected: no source ─────────────────────────────────────────────────────────


def test_invented_percentage_is_removed():
    r = kept("Historical VaR (95%): 3.2%")  # tool says 3.08%
    assert [f.token for f in r.flags] == ["3.2"]
    assert "3.2" not in r.answer and "removed" in r.answer


def test_percentages_and_amounts_get_no_special_exemption():
    r = kept("Expected loss is 7.5% or ₹82,000 on this portfolio.", sources=[OUT])
    assert {f.token for f in r.flags} == {"7.5", "82,000"}


def test_small_integers_get_no_exemption():
    r = kept("There were 7 exceptions.", sources=[{"exception_count": 21}])
    assert [f.token for f in r.flags] == ["7"]
    assert kept("There were 21 exceptions.", sources=[{"exception_count": 21}]).flags == []


def test_rounding_tolerance_is_half_a_unit_not_a_loose_percentage():
    assert kept("VaR is 3.09%").flags != []  # 3.08 shown as 3.09 is off by more than rounding
    assert kept("VaR is 3.08%").flags == []


def test_unsourced_date_and_constant_lookalike_are_removed():
    assert kept("Data starts 2024-01-02").flags != []
    assert kept("Annualised on 253 days").flags != []


def test_without_any_tool_output_every_figure_is_removed():
    r = kept("Your VaR is 4.1% and volatility is 18%.", sources=[])
    assert len(r.flags) == 2


# ── behaviour of the removal ────────────────────────────────────────────────────


def test_only_the_offending_line_is_removed_and_bullet_markers_survive():
    text = "Summary:\n- **Volatility:** 15.87%\n- **Sharpe:** 2.41\n- **Window:** 251 days"
    r = kept(text)
    lines = r.answer.split("\n")
    assert lines[1] == "- **Volatility:** 15.87%"
    assert lines[2].startswith("- [removed") and "2.41" not in r.answer
    assert lines[3] == "- **Window:** 251 days"
    assert r.checked == 3  # 15.87, 2.41 and 251


def test_text_with_no_numbers_is_untouched():
    r = kept("VaR is a threshold, not a maximum loss.", sources=[])
    assert r.flags == [] and r.checked == 0


@pytest.mark.parametrize("bad", ["2.41", "0.0001", "99999"])
def test_unrelated_values_never_pass(bad):
    assert kept(f"Result {bad}").flags != []
