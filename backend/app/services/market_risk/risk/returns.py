"""
returns.py — Return calculation and portfolio performance metrics.

All formulas are documented in docs/MARKET_RISK_METHODS.md.
Conventions:
  - Simple return:  R_t = (P_t - P_{t-1}) / P_{t-1}
  - Log return:     r_t = ln(P_t / P_{t-1})
  - Loss:           L_t = -R_t  (loss positive convention)
  - Annualisation:  √252 for daily → annual vol; 252 for mean return
  - Risk-free rate: Configurable, default 0.06 (6% p.a. INR) or 0.05 (5% USD)
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd
from scipy import stats


# ---------------------------------------------------------------------------
# Default risk-free rates (documented assumption)
# ---------------------------------------------------------------------------
DEFAULT_RISK_FREE_INR = 0.06   # ~RBI repo rate proxy, annualised
DEFAULT_RISK_FREE_USD = 0.05   # ~US Fed funds proxy, annualised
ANNUALISATION_FACTOR = 252


# ---------------------------------------------------------------------------
# Return series
# ---------------------------------------------------------------------------

def simple_returns(prices: pd.DataFrame | pd.Series) -> pd.DataFrame | pd.Series:
    """Discrete percentage change: R_t = (P_t - P_{t-1}) / P_{t-1}."""
    return prices.pct_change().dropna()


def log_returns(prices: pd.DataFrame | pd.Series) -> pd.DataFrame | pd.Series:
    """Continuously compounded: r_t = ln(P_t / P_{t-1})."""
    return np.log(prices / prices.shift(1)).dropna()


def portfolio_returns(returns_df: pd.DataFrame, weights: np.ndarray, symbols: list[str]) -> pd.Series:
    """Weighted-sum portfolio daily return series."""
    return returns_df[symbols].dot(weights)


# ---------------------------------------------------------------------------
# Descriptive statistics
# ---------------------------------------------------------------------------

def annualized_volatility(daily_ret: pd.Series) -> float:
    """σ_annual = σ_daily × √252."""
    return float(daily_ret.std(ddof=1)) * math.sqrt(ANNUALISATION_FACTOR)


def annualized_return(daily_ret: pd.Series) -> float:
    """μ_annual = μ_daily × 252."""
    return float(daily_ret.mean()) * ANNUALISATION_FACTOR


def skewness(daily_ret: pd.Series) -> float:
    return float(daily_ret.skew())


def excess_kurtosis(daily_ret: pd.Series) -> float:
    """Fisher kurtosis (excess); normal = 0."""
    return float(daily_ret.kurtosis())


def jarque_bera(daily_ret: pd.Series) -> dict[str, float]:
    """Jarque-Bera normality test. Returns statistic and p-value."""
    jb_stat, jb_p = stats.jarque_bera(daily_ret.dropna())
    return {"statistic": float(jb_stat), "p_value": float(jb_p)}


def downside_deviation(daily_ret: pd.Series, mar: float = 0.0) -> float:
    """Semi-deviation: std of returns below MAR (Minimum Acceptable Return)."""
    below = daily_ret[daily_ret < mar] - mar
    if len(below) == 0:
        return 0.0
    return float(np.sqrt((below ** 2).mean()))


# ---------------------------------------------------------------------------
# Risk-adjusted ratios (all annualised)
# ---------------------------------------------------------------------------

def sharpe_ratio(daily_ret: pd.Series, risk_free_annual: float = DEFAULT_RISK_FREE_INR) -> float:
    """Sharpe = (μ_annual - Rf) / σ_annual."""
    mu = annualized_return(daily_ret)
    sig = annualized_volatility(daily_ret)
    if sig == 0:
        return 0.0
    return (mu - risk_free_annual) / sig


def sortino_ratio(daily_ret: pd.Series, risk_free_annual: float = DEFAULT_RISK_FREE_INR) -> float:
    """Sortino = (μ_annual - Rf) / downside_deviation_annual."""
    mu = annualized_return(daily_ret)
    dd = downside_deviation(daily_ret) * math.sqrt(ANNUALISATION_FACTOR)
    if dd == 0:
        return 0.0
    return (mu - risk_free_annual) / dd


def information_ratio(portfolio_ret: pd.Series, benchmark_ret: pd.Series) -> float:
    """IR = active_return_annual / tracking_error_annual."""
    active = portfolio_ret - benchmark_ret
    te = annualized_volatility(active)
    if te == 0:
        return 0.0
    return annualized_return(active) / te


def calmar_ratio(daily_ret: pd.Series, max_dd: float) -> float:
    """Calmar = μ_annual / |max_drawdown|."""
    if max_dd == 0:
        return 0.0
    return annualized_return(daily_ret) / abs(max_dd)


def beta(portfolio_ret: pd.Series, benchmark_ret: pd.Series) -> float:
    """CAPM beta = Cov(Rp, Rb) / Var(Rb)."""
    aligned = pd.concat([portfolio_ret, benchmark_ret], axis=1).dropna()
    if len(aligned) < 2:
        return float("nan")
    cov = float(np.cov(aligned.iloc[:, 0], aligned.iloc[:, 1])[0, 1])
    var_b = float(aligned.iloc[:, 1].var(ddof=1))
    return cov / var_b if var_b != 0 else float("nan")


def alpha(portfolio_ret: pd.Series, benchmark_ret: pd.Series, risk_free_annual: float = DEFAULT_RISK_FREE_INR) -> float:
    """Jensen's alpha (annualised): α = Rp - [Rf + β(Rb - Rf)]."""
    b = beta(portfolio_ret, benchmark_ret)
    if math.isnan(b):
        return float("nan")
    rf_daily = risk_free_annual / ANNUALISATION_FACTOR
    aligned = pd.concat([portfolio_ret - rf_daily, benchmark_ret - rf_daily], axis=1).dropna()
    if len(aligned) < 2:
        return float("nan")
    return float(aligned.iloc[:, 0].mean() - b * aligned.iloc[:, 1].mean()) * ANNUALISATION_FACTOR


def tracking_error(portfolio_ret: pd.Series, benchmark_ret: pd.Series) -> float:
    """Annualised tracking error = σ(Rp - Rb) × √252."""
    active = portfolio_ret - benchmark_ret
    return annualized_volatility(active)


def up_capture(portfolio_ret: pd.Series, benchmark_ret: pd.Series) -> float:
    """Up-market capture ratio."""
    up_days = benchmark_ret > 0
    if up_days.sum() == 0:
        return float("nan")
    p = portfolio_ret[up_days].mean()
    b = benchmark_ret[up_days].mean()
    return p / b if b != 0 else float("nan")


def down_capture(portfolio_ret: pd.Series, benchmark_ret: pd.Series) -> float:
    """Down-market capture ratio."""
    down_days = benchmark_ret < 0
    if down_days.sum() == 0:
        return float("nan")
    p = portfolio_ret[down_days].mean()
    b = benchmark_ret[down_days].mean()
    return p / b if b != 0 else float("nan")


# ---------------------------------------------------------------------------
# Drawdown analysis
# ---------------------------------------------------------------------------

@dataclass
class DrawdownPeriod:
    peak_date: str
    trough_date: str
    recovery_date: str | None
    depth: float          # negative fraction (e.g. -0.25 = -25%)
    duration_days: int    # peak → trough
    recovery_days: int | None


def drawdown_series(wealth: pd.Series) -> pd.Series:
    """Rolling drawdown from running peak: DD_t = (W_t - peak_t) / peak_t."""
    peak = wealth.cummax()
    return (wealth - peak) / peak


def max_drawdown(daily_ret: pd.Series) -> float:
    """Maximum peak-to-trough drawdown of the wealth index."""
    wealth = (1.0 + daily_ret).cumprod()
    dd = drawdown_series(wealth)
    return float(dd.min())


def drawdown_table(daily_ret: pd.Series, top_n: int = 5) -> list[DrawdownPeriod]:
    """
    Identifies the top_n worst drawdown periods with depth, duration, and recovery.
    Uses a greedy scan: find trough, scan backward for peak, scan forward for recovery.
    """
    wealth = (1.0 + daily_ret).cumprod()
    dd = drawdown_series(wealth)
    dates = dd.index

    periods: list[DrawdownPeriod] = []
    visited: set[int] = set()

    # Sort trough indices by depth
    sorted_troughs = dd.argsort()  # ascending → most negative first

    for trough_idx in sorted_troughs:
        if trough_idx in visited:
            continue
        if dd.iloc[trough_idx] >= 0:
            break

        # Find peak: last index before trough where wealth was at its high
        peak_val = wealth.iloc[: trough_idx + 1].max()
        peak_candidates = np.where(wealth.iloc[: trough_idx + 1].values == peak_val)[0]
        peak_idx = int(peak_candidates[-1])

        # Find recovery: first index after trough where wealth >= peak level
        recovery_idx = None
        for k in range(trough_idx + 1, len(wealth)):
            if wealth.iloc[k] >= peak_val:
                recovery_idx = k
                break

        # Mark covered indices as visited
        end_visited = recovery_idx if recovery_idx is not None else len(dd) - 1
        visited.update(range(peak_idx, end_visited + 1))

        depth = float(dd.iloc[trough_idx])
        duration = int((dates[trough_idx] - dates[peak_idx]).days)
        rec_days = int((dates[recovery_idx] - dates[trough_idx]).days) if recovery_idx is not None else None
        rec_date = str(dates[recovery_idx].date()) if recovery_idx is not None else None

        periods.append(DrawdownPeriod(
            peak_date=str(dates[peak_idx].date()),
            trough_date=str(dates[trough_idx].date()),
            recovery_date=rec_date,
            depth=round(depth, 4),
            duration_days=duration,
            recovery_days=rec_days,
        ))

        if len(periods) >= top_n:
            break

    return periods


# ---------------------------------------------------------------------------
# Rolling metrics
# ---------------------------------------------------------------------------

def rolling_volatility(daily_ret: pd.Series, window: int = 60) -> pd.Series:
    """Annualised rolling volatility."""
    return daily_ret.rolling(window).std(ddof=1) * math.sqrt(ANNUALISATION_FACTOR)


def rolling_correlation(ret_a: pd.Series, ret_b: pd.Series, window: int = 60) -> pd.Series:
    """Rolling Pearson correlation."""
    return ret_a.rolling(window).corr(ret_b)


# ---------------------------------------------------------------------------
# Correlation / concentration
# ---------------------------------------------------------------------------

def herfindahl_index(weights: np.ndarray) -> float:
    """HHI = Σ w_i². Ranges from 1/N (perfect diversification) to 1 (full concentration)."""
    w = np.array(weights, dtype=float)
    return float(np.sum(w ** 2))


def effective_n(weights: np.ndarray) -> float:
    """Effective N = 1 / HHI. Equal to N when weights are equal."""
    hhi = herfindahl_index(weights)
    return 1.0 / hhi if hhi > 0 else 0.0


def diversification_ratio(weights: np.ndarray, individual_vols: np.ndarray, portfolio_vol: float) -> float:
    """DR = (Σ w_i σ_i) / σ_portfolio."""
    weighted_vol = float(np.dot(weights, individual_vols))
    if portfolio_vol == 0:
        return 1.0
    return weighted_vol / portfolio_vol
