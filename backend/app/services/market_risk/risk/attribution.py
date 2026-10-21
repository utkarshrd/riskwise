"""
attribution.py — VaR decomposition and risk attribution.

Methods:
  - Marginal VaR:      ∂VaR/∂w_i  (sensitivity of portfolio VaR to a small change in weight of asset i)
  - Component VaR:     w_i × MVaR_i  (each asset's additive contribution to portfolio VaR)
  - Incremental VaR:   VaR(portfolio + asset_i) - VaR(portfolio without asset_i)
  - Volatility contribution: per-asset contribution to portfolio variance
  - Diversification ratio, HHI, effective N (re-exported from returns.py)

All formulas referenced in docs/MARKET_RISK_METHODS.md.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from scipy import stats


@dataclass
class RiskAttribution:
    symbols: list[str]
    weights: list[float]
    portfolio_var: float                          # 1-day parametric VaR (fraction)
    marginal_var: dict[str, float]               # ∂VaR/∂w_i
    component_var: dict[str, float]              # w_i × MVaR_i
    component_var_pct: dict[str, float]          # fraction of total VaR
    incremental_var: dict[str, float]            # exact incremental contribution
    vol_contribution: dict[str, float]           # fraction of portfolio variance
    diversification_ratio: float
    hhi: float
    effective_n: float
    assumptions: dict[str, str] = field(default_factory=dict)


def compute_attribution(
    returns_df: pd.DataFrame,
    symbols: list[str],
    weights: np.ndarray,
    confidence: float = 0.95,
) -> RiskAttribution:
    """
    Computes full VaR decomposition for a portfolio.

    Args:
        returns_df:  DataFrame of daily asset returns indexed by Date.
        symbols:     Column names in returns_df; must match weights order.
        weights:     Portfolio weights (must sum to 1).
        confidence:  VaR confidence level (default 0.95).

    Returns:
        RiskAttribution dataclass with all decomposition fields.
    """
    w = np.asarray(weights, dtype=float)
    R = returns_df[symbols].values  # shape (T, N)
    cov = np.cov(R.T, ddof=1)      # (N, N) covariance matrix of daily returns
    if cov.ndim == 0:
        cov = np.array([[float(cov)]])

    z = float(stats.norm.ppf(confidence))

    # Portfolio variance and vol
    port_var_daily = float(w @ cov @ w)
    port_sig = float(np.sqrt(max(port_var_daily, 0.0)))

    # Mean return
    mu_daily = float(returns_df[symbols].mean() @ w)

    # Parametric Gaussian VaR (loss positive)
    # portfolio_var is defined as z × σ_p so that the Euler identity
    # Σ component_var_i = portfolio_var holds exactly.
    # The mean-adjusted estimate (z × σ_p − μ) is used only internally.
    port_var_95 = z * port_sig          # VaR for additivity identity
    port_var_95_adj = z * port_sig - mu_daily  # mean-adjusted VaR (for incremental)

    # ---------------------------------------------------------------------------
    # Marginal VaR: MVaR_i = (Cov(R_i, R_p) / σ_p) × z
    # Cov(R_i, R_p) = (Cov × w)[i]
    # ---------------------------------------------------------------------------
    cov_asset_port = cov @ w          # shape (N,)  = Cov(each asset, portfolio)
    if port_sig > 0:
        marginal_var_arr = z * cov_asset_port / port_sig
    else:
        marginal_var_arr = np.zeros_like(w)

    # ---------------------------------------------------------------------------
    # Component VaR: CVaR_i = w_i × MVaR_i
    # ---------------------------------------------------------------------------
    component_var_arr = w * marginal_var_arr

    # Normalise to fractions of total VaR
    total_component = float(component_var_arr.sum())
    if abs(total_component) > 1e-10:
        component_pct_arr = component_var_arr / total_component
    else:
        component_pct_arr = np.ones_like(component_var_arr) / len(component_var_arr)

    # ---------------------------------------------------------------------------
    # Incremental VaR: exact difference when asset is removed and weight redistributed
    # ---------------------------------------------------------------------------
    incremental_arr = np.zeros(len(symbols))
    for i in range(len(symbols)):
        if w[i] == 0:
            incremental_arr[i] = 0.0
            continue
        # Portfolio without asset i: redistribute weight proportionally
        mask = np.arange(len(symbols)) != i
        w_sub = w[mask]
        w_sub_sum = w_sub.sum()
        if w_sub_sum > 0:
            w_sub = w_sub / w_sub_sum
        cov_sub = cov[np.ix_(mask, mask)]
        port_var_sub = float(w_sub @ cov_sub @ w_sub)
        port_sig_sub = float(np.sqrt(max(port_var_sub, 0.0)))
        mu_sub = float(returns_df[symbols].iloc[:, mask].mean() @ w_sub)
        var_sub = z * port_sig_sub - mu_sub
        incremental_arr[i] = port_var_95_adj - var_sub

    # ---------------------------------------------------------------------------
    # Volatility contribution: share of portfolio variance
    # σ²_p = Σ_i Σ_j w_i w_j σ_ij
    # Vol contrib asset i = Σ_j w_i w_j σ_ij / σ²_p
    # ---------------------------------------------------------------------------
    if port_var_daily > 0:
        vol_contrib_arr = (w * (cov @ w)) / port_var_daily
    else:
        vol_contrib_arr = np.ones_like(w) / len(w)

    # Individual asset annualised vols
    ind_vols = np.sqrt(np.diag(cov)) * np.sqrt(252)
    port_vol_annual = port_sig * np.sqrt(252)

    # Diversification ratio
    weighted_vol = float(w @ ind_vols)
    div_ratio = weighted_vol / port_vol_annual if port_vol_annual > 0 else 1.0

    # HHI and effective N
    hhi = float(np.sum(w ** 2))
    eff_n = 1.0 / hhi if hhi > 0 else 0.0

    return RiskAttribution(
        symbols=list(symbols),
        weights=[round(float(wi), 4) for wi in w],
        portfolio_var=port_var_95,
        marginal_var={sym: float(mv) for sym, mv in zip(symbols, marginal_var_arr)},
        component_var={sym: float(cv) for sym, cv in zip(symbols, component_var_arr)},
        component_var_pct={sym: round(float(cp), 4) for sym, cp in zip(symbols, component_pct_arr)},
        incremental_var={sym: round(float(iv), 6) for sym, iv in zip(symbols, incremental_arr)},
        vol_contribution={sym: round(float(vc), 4) for sym, vc in zip(symbols, vol_contrib_arr)},
        diversification_ratio=round(div_ratio, 4),
        hhi=round(hhi, 4),
        effective_n=round(eff_n, 2),
        assumptions={
            "method": "parametric Gaussian",
            "confidence": str(confidence),
            "cov_estimator": "sample covariance (ddof=1)",
            "incremental_var": "exact removal with proportional weight redistribution",
        },
    )
