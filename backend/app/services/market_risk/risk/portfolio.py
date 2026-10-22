"""
portfolio.py — Portfolio optimisation and what-if analysis.

Tools (labelled not-advice):
  - Minimum-variance portfolio
  - Risk-parity portfolio (equal risk contribution)
  - Maximum Sharpe ratio portfolio
  - Efficient frontier (parameterised by target return)
  - What-if trade simulator (shows Δ VaR / Δ ES / Δ vol for a proposed trade)

All methods use scipy.optimize with documented assumptions.
Results are clearly labelled as analytical tools, not investment advice.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd
from scipy import stats
from scipy.optimize import OptimizeResult, minimize

ANNUALISATION = 252
DEFAULT_RISK_FREE = 0.06   # 6% p.a., documented default


# ---------------------------------------------------------------------------
# Optimisation result schema
# ---------------------------------------------------------------------------

@dataclass
class OptimisedPortfolio:
    method: str
    symbols: list[str]
    weights: dict[str, float]
    expected_annual_return: float
    annual_volatility: float
    sharpe_ratio: float
    var_95: float              # 1-day historical VaR at 95%
    max_drawdown_approx: float # analytical approximation
    converged: bool
    iterations: int
    warnings: list[str] = field(default_factory=list)
    assumptions: dict[str, Any] = field(default_factory=dict)


@dataclass
class EfficientFrontierPoint:
    target_return: float
    annual_volatility: float
    weights: dict[str, float]
    sharpe_ratio: float


@dataclass
class WhatIfResult:
    original_var_95: float
    new_var_95: float
    delta_var_95: float
    original_es_95: float
    new_es_95: float
    delta_es_95: float
    original_vol: float
    new_vol: float
    delta_vol: float
    new_weights: dict[str, float]
    warnings: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _port_return(w: np.ndarray, mu: np.ndarray) -> float:
    return float(w @ mu)


def _port_variance(w: np.ndarray, cov: np.ndarray) -> float:
    return float(w @ cov @ w)


def _port_vol(w: np.ndarray, cov: np.ndarray) -> float:
    return math.sqrt(max(_port_variance(w, cov), 0.0))


def _port_sharpe(w: np.ndarray, mu: np.ndarray, cov: np.ndarray, rf_annual: float) -> float:
    ann_ret = _port_return(w, mu) * ANNUALISATION
    ann_vol = _port_vol(w, cov) * math.sqrt(ANNUALISATION)
    if ann_vol == 0:
        return 0.0
    return (ann_ret - rf_annual) / ann_vol


def _parametric_var_95(w: np.ndarray, mu_daily: np.ndarray, cov: np.ndarray) -> float:
    sig = _port_vol(w, cov)
    m = float(w @ mu_daily)
    return float(stats.norm.ppf(0.95)) * sig - m


def _base_constraints(n: int) -> list[dict]:
    return [{"type": "eq", "fun": lambda w: np.sum(w) - 1.0}]


def _long_only_bounds(n: int) -> list[tuple[float, float]]:
    return [(0.0, 1.0)] * n


def _build_result(
    method: str,
    symbols: list[str],
    w: np.ndarray,
    mu: np.ndarray,
    cov: np.ndarray,
    opt_result: OptimizeResult,
    rf: float = DEFAULT_RISK_FREE,
    warns: list[str] | None = None,
) -> OptimisedPortfolio:
    ann_ret = _port_return(w, mu) * ANNUALISATION
    ann_vol = _port_vol(w, cov) * math.sqrt(ANNUALISATION)
    sharpe = _port_sharpe(w, mu, cov, rf)
    var_95 = _parametric_var_95(w, mu, cov)
    # Max drawdown approximation: -2σ_annual / μ_annual (Magdon-Ismail formula, rough proxy)
    mdd_approx = abs(-2 * ann_vol ** 2 / ann_ret) if ann_ret > 0 else float("nan")

    return OptimisedPortfolio(
        method=method,
        symbols=list(symbols),
        weights={sym: round(float(w[i]), 4) for i, sym in enumerate(symbols)},
        expected_annual_return=round(ann_ret, 4),
        annual_volatility=round(ann_vol, 4),
        sharpe_ratio=round(sharpe, 4),
        var_95=round(var_95, 6),
        max_drawdown_approx=round(mdd_approx, 4) if not math.isnan(mdd_approx) else float("nan"),
        converged=opt_result.success,
        iterations=int(opt_result.get("nit", 0)),
        warnings=warns or ([] if opt_result.success else [f"Optimiser did not converge: {opt_result.message}"]),
        assumptions={
            "risk_free_rate": rf,
            "annualisation_factor": ANNUALISATION,
            "covariance_estimator": "sample (ddof=1)",
            "constraint": "long-only, fully invested",
            "disclaimer": "Optimisation output is an analytical tool only, not investment advice.",
        },
    )


# ---------------------------------------------------------------------------
# 1. Minimum-variance portfolio
# ---------------------------------------------------------------------------

def minimum_variance(
    returns_df: pd.DataFrame,
    symbols: list[str],
    rf: float = DEFAULT_RISK_FREE,
) -> OptimisedPortfolio:
    """Minimise portfolio variance subject to Σw=1 and w≥0."""
    R = returns_df[symbols].dropna()
    mu = R.mean().values
    cov = R.cov().values
    n = len(symbols)
    w0 = np.ones(n) / n

    result = minimize(
        lambda w: _port_variance(w, cov),
        w0,
        method="SLSQP",
        bounds=_long_only_bounds(n),
        constraints=_base_constraints(n),
        options={"ftol": 1e-9, "maxiter": 500},
    )
    w_opt = np.clip(result.x, 0, 1)
    w_opt /= w_opt.sum()
    return _build_result("minimum_variance", symbols, w_opt, mu, cov, result, rf)


# ---------------------------------------------------------------------------
# 2. Risk-parity portfolio (equal risk contribution)
# ---------------------------------------------------------------------------

def risk_parity(
    returns_df: pd.DataFrame,
    symbols: list[str],
    rf: float = DEFAULT_RISK_FREE,
) -> OptimisedPortfolio:
    """
    Equal risk contribution: RC_i = w_i × (∂σ_p / ∂w_i) = σ_p / N for all i.
    Minimise Σ(RC_i - σ_p/N)² subject to Σw=1 and w≥0.
    """
    R = returns_df[symbols].dropna()
    mu = R.mean().values
    cov = R.cov().values
    n = len(symbols)
    w0 = np.ones(n) / n

    def _risk_parity_obj(w: np.ndarray) -> float:
        sig_p = _port_vol(w, cov)
        if sig_p < 1e-12:
            return 0.0
        RC = w * (cov @ w) / sig_p
        target_RC = sig_p / n
        return float(np.sum((RC - target_RC) ** 2))

    result = minimize(
        _risk_parity_obj,
        w0,
        method="SLSQP",
        bounds=_long_only_bounds(n),
        constraints=_base_constraints(n),
        options={"ftol": 1e-12, "maxiter": 1000},
    )
    w_opt = np.clip(result.x, 0, 1)
    w_opt /= w_opt.sum()
    return _build_result("risk_parity", symbols, w_opt, mu, cov, result, rf)


# ---------------------------------------------------------------------------
# 3. Maximum Sharpe ratio portfolio
# ---------------------------------------------------------------------------

def max_sharpe(
    returns_df: pd.DataFrame,
    symbols: list[str],
    rf: float = DEFAULT_RISK_FREE,
) -> OptimisedPortfolio:
    """Maximise Sharpe ratio (minimise -Sharpe) subject to Σw=1 and w≥0."""
    R = returns_df[symbols].dropna()
    mu = R.mean().values
    cov = R.cov().values
    n = len(symbols)
    w0 = np.ones(n) / n

    result = minimize(
        lambda w: -_port_sharpe(w, mu, cov, rf),
        w0,
        method="SLSQP",
        bounds=_long_only_bounds(n),
        constraints=_base_constraints(n),
        options={"ftol": 1e-9, "maxiter": 500},
    )
    w_opt = np.clip(result.x, 0, 1)
    w_opt_sum = w_opt.sum()
    w_opt = w_opt / w_opt_sum if w_opt_sum > 0 else w0
    return _build_result("max_sharpe", symbols, w_opt, mu, cov, result, rf)


# ---------------------------------------------------------------------------
# 4. Efficient frontier
# ---------------------------------------------------------------------------

def efficient_frontier(
    returns_df: pd.DataFrame,
    symbols: list[str],
    n_points: int = 20,
    rf: float = DEFAULT_RISK_FREE,
) -> list[EfficientFrontierPoint]:
    """
    Computes n_points on the efficient frontier by minimising variance
    for a range of target annualised returns from min-var to max-return.
    """
    R = returns_df[symbols].dropna()
    mu = R.mean().values
    cov = R.cov().values
    n = len(symbols)
    w0 = np.ones(n) / n

    # Bounds on achievable returns
    min_ret = float(min(mu)) * ANNUALISATION
    max_ret = float(max(mu)) * ANNUALISATION
    target_returns = np.linspace(min_ret, max_ret, n_points)

    points = []
    for target_ann_ret in target_returns:
        target_daily_ret = target_ann_ret / ANNUALISATION
        constraints = _base_constraints(n) + [
            {"type": "eq", "fun": lambda w, t=target_daily_ret: _port_return(w, mu) - t}
        ]
        result = minimize(
            lambda w: _port_variance(w, cov),
            w0,
            method="SLSQP",
            bounds=_long_only_bounds(n),
            constraints=constraints,
            options={"ftol": 1e-9, "maxiter": 500},
        )
        if not result.success:
            continue
        w_opt = np.clip(result.x, 0, 1)
        w_sum = w_opt.sum()
        if w_sum > 0:
            w_opt /= w_sum
        ann_vol = _port_vol(w_opt, cov) * math.sqrt(ANNUALISATION)
        sharpe = (target_ann_ret - rf) / ann_vol if ann_vol > 0 else 0.0
        points.append(EfficientFrontierPoint(
            target_return=round(target_ann_ret, 4),
            annual_volatility=round(ann_vol, 4),
            weights={sym: round(float(w_opt[i]), 4) for i, sym in enumerate(symbols)},
            sharpe_ratio=round(sharpe, 4),
        ))

    return points


# ---------------------------------------------------------------------------
# 5. What-if trade simulator
# ---------------------------------------------------------------------------

def what_if_trade(
    returns_df: pd.DataFrame,
    symbols: list[str],
    current_weights: np.ndarray,
    trade_symbol: str,
    trade_weight_delta: float,
    confidence: float = 0.95,
) -> WhatIfResult:
    """
    Simulates the effect of changing the weight of trade_symbol by trade_weight_delta
    (e.g. +0.05 = add 5% to that position, funded by proportional reduction in others).

    Shows change in:
      - 1-day parametric VaR at confidence level
      - Expected Shortfall
      - Annualised portfolio volatility
    """
    warns: list[str] = []
    R = returns_df[symbols].dropna()
    mu = R.mean().values
    cov = R.cov().values
    w_orig = np.asarray(current_weights, dtype=float)

    def _var_es(w: np.ndarray) -> tuple[float, float]:
        sig = _port_vol(w, cov)
        m = float(w @ mu)
        z = stats.norm.ppf(confidence)
        var = z * sig - m
        es = sig * stats.norm.pdf(z) / (1 - confidence) - m
        return float(var), float(es)

    var_orig, es_orig = _var_es(w_orig)
    vol_orig = _port_vol(w_orig, cov) * math.sqrt(ANNUALISATION)

    # Apply trade: adjust target symbol, renormalise others
    if trade_symbol not in symbols:
        warns.append(f"Trade symbol '{trade_symbol}' not in portfolio; no change applied.")
        return WhatIfResult(
            original_var_95=round(var_orig, 6),
            new_var_95=round(var_orig, 6),
            delta_var_95=0.0,
            original_es_95=round(es_orig, 6),
            new_es_95=round(es_orig, 6),
            delta_es_95=0.0,
            original_vol=round(vol_orig, 4),
            new_vol=round(vol_orig, 4),
            delta_vol=0.0,
            new_weights={sym: round(float(w_orig[i]), 4) for i, sym in enumerate(symbols)},
            warnings=warns,
        )

    idx = symbols.index(trade_symbol)
    w_new = w_orig.copy()
    w_new[idx] = max(0.0, w_new[idx] + trade_weight_delta)

    # Renormalise
    w_sum = w_new.sum()
    if w_sum <= 0:
        warns.append("New weights sum to ≤0 after trade; returning original portfolio.")
        w_new = w_orig
    else:
        w_new /= w_sum

    if abs(w_new.sum() - 1.0) > 1e-3:
        warns.append(f"Weight sum after trade: {w_new.sum():.4f} (may not equal 1 exactly).")

    var_new, es_new = _var_es(w_new)
    vol_new = _port_vol(w_new, cov) * math.sqrt(ANNUALISATION)

    return WhatIfResult(
        original_var_95=round(var_orig, 6),
        new_var_95=round(var_new, 6),
        delta_var_95=round(var_new - var_orig, 6),
        original_es_95=round(es_orig, 6),
        new_es_95=round(es_new, 6),
        delta_es_95=round(es_new - es_orig, 6),
        original_vol=round(vol_orig, 4),
        new_vol=round(vol_new, 4),
        delta_vol=round(vol_new - vol_orig, 4),
        new_weights={sym: round(float(w_new[i]), 4) for i, sym in enumerate(symbols)},
        warnings=warns,
    )
