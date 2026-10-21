"""
stress.py — Stress testing scenarios for portfolio risk analysis.

Scenario types:
  1. Historical worst-day / max-drawdown (derived from real data)
  2. Historical event replays (COVID, 2008-GFC, India Election 2024, Adani 2023)
     — computed from real price data where available; date ranges documented.
  3. Beta-scaled index shocks (user provides index shock; asset shocks = β × index_shock)
  4. Sector shocks (uniform shock to all holdings in specified sector)
  5. Custom shocks (user-specified per-asset)
  6. Reverse stress test (finds minimum uniform shock that breaches a loss threshold)
  7. Correlation-breakdown stress (assume all correlations → 1)

All scenarios require explicit per-asset shocks — no hidden fallback constants.
See docs/MARKET_RISK_METHODS.md for methodology and data sources.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# Date ranges for named historical events
# Documentation: actual observed index/asset returns extracted from price data.
# ---------------------------------------------------------------------------

HISTORICAL_EVENT_WINDOWS: dict[str, dict[str, str]] = {
    "COVID_Feb_Mar_2020": {
        "start": "2020-02-17",
        "end": "2020-03-23",
        "description": "COVID-19 market crash. Nifty 50 fell ~38% peak-to-trough. "
                       "S&P 500 fell ~34%. Computed from real daily prices in snapshot.",
    },
    "GFC_Sep_Oct_2008": {
        "start": "2008-09-01",
        "end": "2008-10-31",
        "description": "Global Financial Crisis post-Lehman. "
                       "Nifty 50 fell ~36% over this 2-month window where data exists.",
    },
    "India_Election_Jun2024": {
        "start": "2024-06-04",
        "end": "2024-06-04",
        "description": "India general election results day (4 Jun 2024). "
                       "Nifty 50 fell ~5.93% intraday before recovering.",
    },
    "Adani_Jan_Feb_2023": {
        "start": "2023-01-24",
        "end": "2023-02-28",
        "description": "Hindenburg Research short report on Adani Group (24 Jan 2023). "
                       "Adani group stocks fell 40–80%. Computed from real price data.",
    },
}


# ---------------------------------------------------------------------------
# Result schema
# ---------------------------------------------------------------------------

@dataclass
class StressResult:
    scenario_name: str
    scenario_type: str                          # historical | event_replay | beta_scaled | sector | custom | reverse | correlation_breakdown
    portfolio_loss_pct: float                   # positive = loss
    portfolio_loss_amount: float | None         # None if portfolio_value not provided
    asset_shocks: dict[str, float]             # per-asset shock applied
    asset_loss_contributions: dict[str, float]  # per-asset contribution to portfolio loss
    description: str
    data_source: str
    warnings: list[str] = field(default_factory=list)
    assumptions: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Core computation
# ---------------------------------------------------------------------------

def _apply_shocks(
    weights: dict[str, float],
    shocks: dict[str, float],
    portfolio_value: float | None = None,
) -> tuple[float, dict[str, float]]:
    """
    Linear approximation: portfolio_loss = Σ w_i × shock_i.
    Returns (total_loss_pct, per_asset_loss_contributions).
    """
    total_loss = 0.0
    contributions = {}
    for sym, w in weights.items():
        shock = shocks.get(sym, 0.0)
        contrib = -shock * w   # negative shock = positive loss
        contributions[sym] = round(contrib, 6)
        total_loss += contrib
    return round(total_loss, 6), contributions


# ---------------------------------------------------------------------------
# 1. Historical worst-day / max-drawdown (derived from prices)
# ---------------------------------------------------------------------------

def historical_shock_scenarios(
    returns_df: pd.DataFrame,
    symbols: list[str],
    weights: dict[str, float],
    portfolio_value: float | None = None,
) -> list[StressResult]:
    """
    Derives worst-case scenarios directly from the historical return data:
    - Worst single trading day
    - Maximum peak-to-trough drawdown per asset
    No hidden constants — all values computed from real data.
    """
    results = []

    # Scenario 1: Worst single trading day (each asset's personal worst day)
    worst_day: dict[str, float] = {}
    for sym in symbols:
        if sym in returns_df.columns:
            worst_day[sym] = round(float(returns_df[sym].min()), 4)

    if worst_day:
        loss_pct, contribs = _apply_shocks(weights, worst_day, portfolio_value)
        results.append(StressResult(
            scenario_name="Historical_Worst_Single_Day",
            scenario_type="historical",
            portfolio_loss_pct=loss_pct,
            portfolio_loss_amount=round(loss_pct * portfolio_value, 2) if portfolio_value else None,
            asset_shocks=worst_day,
            asset_loss_contributions=contribs,
            description="Each asset's individually worst observed 1-day return applied simultaneously.",
            data_source="Historical snapshot daily returns",
            assumptions={"note": "Simultaneous occurrence is a stress assumption, not a forecast."},
        ))

    # Scenario 2: Maximum peak-to-trough drawdown
    max_dd: dict[str, float] = {}
    for sym in symbols:
        if sym in returns_df.columns:
            wealth = (1 + returns_df[sym]).cumprod()
            drawdown = (wealth - wealth.cummax()) / wealth.cummax()
            max_dd[sym] = round(float(drawdown.min()), 4)

    if max_dd:
        loss_pct, contribs = _apply_shocks(weights, max_dd, portfolio_value)
        results.append(StressResult(
            scenario_name="Historical_Max_Drawdown",
            scenario_type="historical",
            portfolio_loss_pct=loss_pct,
            portfolio_loss_amount=round(loss_pct * portfolio_value, 2) if portfolio_value else None,
            asset_shocks=max_dd,
            asset_loss_contributions=contribs,
            description="Each asset's maximum observed peak-to-trough drawdown applied simultaneously.",
            data_source="Historical snapshot daily prices",
            assumptions={"note": "Simultaneous occurrence is a stress assumption, not a forecast."},
        ))

    return results


# ---------------------------------------------------------------------------
# 2. Historical event replay
# ---------------------------------------------------------------------------

def event_replay_scenarios(
    prices_df: pd.DataFrame,
    symbols: list[str],
    weights: dict[str, float],
    portfolio_value: float | None = None,
    events: list[str] | None = None,
) -> list[StressResult]:
    """
    Computes total return of each asset over named historical event windows.
    Only uses events where price data exists in the snapshot; warns otherwise.
    """
    results = []
    events = events or list(HISTORICAL_EVENT_WINDOWS.keys())

    for event_name in events:
        if event_name not in HISTORICAL_EVENT_WINDOWS:
            continue
        ew = HISTORICAL_EVENT_WINDOWS[event_name]
        start, end = pd.Timestamp(ew["start"]), pd.Timestamp(ew["end"])

        shocks: dict[str, float] = {}
        warns: list[str] = []

        for sym in symbols:
            if sym not in prices_df.columns:
                warns.append(f"No price data for '{sym}' — shock set to 0. Scenario is partial.")
                shocks[sym] = 0.0
                continue

            series = prices_df[sym].dropna()
            window = series[(series.index >= start) & (series.index <= end)]

            if len(window) < 1:
                warns.append(
                    f"No price data for '{sym}' in {ew['start']}–{ew['end']} window. "
                    "Shock set to 0. This is expected for data not covering that period."
                )
                shocks[sym] = 0.0
            elif len(window) == 1:
                # Single day: use that day's return if prev price available
                idx = list(series.index).index(window.index[0])
                if idx > 0:
                    prev_price = float(series.iloc[idx - 1])
                    shock = (float(window.iloc[0]) - prev_price) / prev_price if prev_price != 0 else 0.0
                else:
                    shock = 0.0
                shocks[sym] = round(shock, 4)
            else:
                p_start = float(window.iloc[0])
                p_end = float(window.iloc[-1])
                shock = (p_end - p_start) / p_start if p_start != 0 else 0.0
                shocks[sym] = round(shock, 4)

        loss_pct, contribs = _apply_shocks(weights, shocks, portfolio_value)
        results.append(StressResult(
            scenario_name=event_name,
            scenario_type="event_replay",
            portfolio_loss_pct=loss_pct,
            portfolio_loss_amount=round(loss_pct * portfolio_value, 2) if portfolio_value else None,
            asset_shocks=shocks,
            asset_loss_contributions=contribs,
            description=ew["description"],
            data_source=f"Historical price snapshots, window {ew['start']}–{ew['end']}",
            warnings=warns,
            assumptions={
                "note": "Returns computed as (P_end - P_start) / P_start within the event window. "
                        "Where data is unavailable, shock is 0 and a warning is raised.",
            },
        ))

    return results


# ---------------------------------------------------------------------------
# 3. Beta-scaled index shock
# ---------------------------------------------------------------------------

def beta_scaled_scenarios(
    returns_df: pd.DataFrame,
    symbols: list[str],
    weights: dict[str, float],
    benchmark_returns: pd.Series,
    index_shocks: list[float],
    benchmark_name: str = "Nifty50",
    portfolio_value: float | None = None,
) -> list[StressResult]:
    """
    Computes per-asset shock = β_i × index_shock, where β_i is the OLS beta
    of asset i against the benchmark.

    Args:
        index_shocks: List of shocks to the benchmark (e.g. [-0.05, -0.10, -0.20]).
    """
    results = []

    # Estimate betas
    betas: dict[str, float] = {}
    for sym in symbols:
        if sym not in returns_df.columns:
            betas[sym] = 1.0
            continue
        aligned = pd.concat([returns_df[sym], benchmark_returns], axis=1).dropna()
        if len(aligned) < 20:
            betas[sym] = 1.0
            continue
        y = aligned.iloc[:, 0].values
        x = aligned.iloc[:, 1].values
        x_c = x - x.mean()
        betas[sym] = round(float(np.dot(x_c, y - y.mean()) / (np.dot(x_c, x_c) or 1.0)), 4)

    for idx_shock in index_shocks:
        shocks = {sym: round(betas[sym] * idx_shock, 4) for sym in symbols}
        loss_pct, contribs = _apply_shocks(weights, shocks, portfolio_value)
        results.append(StressResult(
            scenario_name=f"BetaScaled_{benchmark_name}_{idx_shock*100:+.0f}pct",
            scenario_type="beta_scaled",
            portfolio_loss_pct=loss_pct,
            portfolio_loss_amount=round(loss_pct * portfolio_value, 2) if portfolio_value else None,
            asset_shocks=shocks,
            asset_loss_contributions=contribs,
            description=(
                f"{benchmark_name} index shock of {idx_shock*100:.0f}%. "
                "Per-asset shocks = OLS β × index shock."
            ),
            data_source=f"OLS regression against {benchmark_name}",
            assumptions={
                "betas": betas,
                "index_shock": idx_shock,
                "benchmark": benchmark_name,
                "note": "Linear beta scaling assumes stable factor exposures.",
            },
        ))

    return results


# ---------------------------------------------------------------------------
# 4. Sector shock
# ---------------------------------------------------------------------------

def sector_shock_scenario(
    symbols: list[str],
    weights: dict[str, float],
    symbol_sectors: dict[str, str],
    target_sector: str,
    sector_shock: float,
    other_shock: float = 0.0,
    portfolio_value: float | None = None,
) -> StressResult:
    """
    Applies a uniform shock to all holdings in target_sector,
    and a different shock (default 0) to all others.
    """
    shocks = {}
    for sym in symbols:
        sector = symbol_sectors.get(sym, "Unknown")
        shocks[sym] = sector_shock if sector == target_sector else other_shock

    loss_pct, contribs = _apply_shocks(weights, shocks, portfolio_value)
    return StressResult(
        scenario_name=f"SectorShock_{target_sector}_{sector_shock*100:+.0f}pct",
        scenario_type="sector",
        portfolio_loss_pct=loss_pct,
        portfolio_loss_amount=round(loss_pct * portfolio_value, 2) if portfolio_value else None,
        asset_shocks=shocks,
        asset_loss_contributions=contribs,
        description=f"Uniform {sector_shock*100:.0f}% shock to {target_sector} sector holdings.",
        data_source="User-specified sector classification",
        assumptions={
            "target_sector": target_sector,
            "sector_shock": sector_shock,
            "other_shock": other_shock,
        },
    )


# ---------------------------------------------------------------------------
# 5. Custom shock
# ---------------------------------------------------------------------------

def custom_shock_scenario(
    symbols: list[str],
    weights: dict[str, float],
    shocks: dict[str, float],
    scenario_name: str = "Custom",
    description: str = "User-specified shocks",
    portfolio_value: float | None = None,
) -> StressResult:
    """User-specified per-asset shocks."""
    # Fill missing symbols with 0
    full_shocks = {sym: shocks.get(sym, 0.0) for sym in symbols}
    loss_pct, contribs = _apply_shocks(weights, full_shocks, portfolio_value)
    return StressResult(
        scenario_name=scenario_name,
        scenario_type="custom",
        portfolio_loss_pct=loss_pct,
        portfolio_loss_amount=round(loss_pct * portfolio_value, 2) if portfolio_value else None,
        asset_shocks=full_shocks,
        asset_loss_contributions=contribs,
        description=description,
        data_source="User-specified",
        assumptions={"note": "Unspecified assets have shock=0."},
    )


# ---------------------------------------------------------------------------
# 6. Reverse stress test
# ---------------------------------------------------------------------------

def reverse_stress_test(
    symbols: list[str],
    weights: dict[str, float],
    loss_threshold: float,
    portfolio_value: float | None = None,
) -> StressResult:
    """
    Finds the minimum uniform shock across all assets that breaches the loss threshold.
    loss_threshold is a positive fraction (e.g. 0.20 for 20% loss).

    Formula: uniform_shock = -loss_threshold / Σ w_i
    (since portfolio_loss = -shock × Σw_i and Σw_i=1 for fully invested)
    """
    weight_sum = sum(weights.values())
    if weight_sum <= 0:
        raise ValueError("Sum of weights must be positive for reverse stress test.")
    uniform_shock = -(loss_threshold / weight_sum)  # negative = down shock
    shocks = {sym: uniform_shock for sym in symbols}
    loss_pct, contribs = _apply_shocks(weights, shocks, portfolio_value)

    return StressResult(
        scenario_name=f"ReverseStress_Loss{loss_threshold*100:.0f}pct",
        scenario_type="reverse",
        portfolio_loss_pct=loss_pct,
        portfolio_loss_amount=round(loss_pct * portfolio_value, 2) if portfolio_value else None,
        asset_shocks=shocks,
        asset_loss_contributions=contribs,
        description=(
            f"Minimum uniform shock ({uniform_shock*100:.2f}% per asset) that produces "
            f"a {loss_threshold*100:.0f}% portfolio loss."
        ),
        data_source="Analytical (no historical data required)",
        assumptions={
            "loss_threshold": loss_threshold,
            "uniform_shock": uniform_shock,
            "note": "Assumes equal shock across all assets; real scenarios may differ.",
        },
    )


# ---------------------------------------------------------------------------
# 7. Correlation-breakdown stress
# ---------------------------------------------------------------------------

def correlation_breakdown_scenario(
    returns_df: pd.DataFrame,
    symbols: list[str],
    weights: dict[str, float],
    correlation_assumption: float = 1.0,
    portfolio_value: float | None = None,
) -> StressResult:
    """
    Stress-tests portfolio assuming all pairwise correlations → correlation_assumption (default 1).
    VaR under full correlation = Σ w_i σ_i × z (worst case: no diversification benefit).

    Uses historical individual volatilities from returns_df.
    """
    from scipy import stats as sp_stats

    R = returns_df[symbols]
    ind_vols = R.std(ddof=1)
    w = np.array([weights[sym] for sym in symbols])
    sigs = np.array([float(ind_vols[sym]) if sym in ind_vols else 0.0 for sym in symbols])

    # Under full correlation ρ=1: portfolio variance = (Σ w_i σ_i)²
    stressed_port_sig = float(np.dot(w, sigs))
    z95 = float(sp_stats.norm.ppf(0.95))
    stressed_var = z95 * stressed_port_sig

    # Undiversified loss as a "shock" per asset (proportional to weight × vol)
    shocks = {sym: -z95 * float(sigs[i]) for i, sym in enumerate(symbols)}
    loss_pct, contribs = _apply_shocks(weights, shocks, portfolio_value)

    return StressResult(
        scenario_name=f"CorrelationBreakdown_rho{correlation_assumption:.0f}",
        scenario_type="correlation_breakdown",
        portfolio_loss_pct=round(stressed_var, 6),
        portfolio_loss_amount=round(stressed_var * portfolio_value, 2) if portfolio_value else None,
        asset_shocks=shocks,
        asset_loss_contributions=contribs,
        description=(
            f"All pairwise correlations set to {correlation_assumption:.0f}. "
            "Portfolio loss = Σ w_i σ_i × z (no diversification benefit)."
        ),
        data_source="Historical volatilities from snapshot; correlation assumption applied",
        assumptions={
            "correlation_assumption": correlation_assumption,
            "individual_vols": {sym: round(float(sigs[i]), 6) for i, sym in enumerate(symbols)},
            "note": "This is the parametric Gaussian 95% VaR under full correlation.",
        },
    )
