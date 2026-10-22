"""
var_models.py — VaR and Expected Shortfall estimation methods.

Methods implemented:
  - historical:         Empirical quantile of loss distribution
  - gaussian:           Parametric normal (μ, σ)
  - student_t:          Parametric fitted Student-t
  - cornish_fisher:     Cornish-Fisher expansion adjusting for skew/kurtosis
  - ewma:               EWMA variance (λ=0.94, RiskMetrics standard)
  - garch:              GARCH(1,1) via arch library (optional, falls back gracefully)
  - fhs:                Filtered Historical Simulation (GARCH-standardised residuals)
  - monte_carlo:        Correlated Monte Carlo (Cholesky decomposition, seeded)

Horizons: 1, 5, 10 days (√T scaling for parametric; simulation for MC).
Confidence: 0.90, 0.95, 0.975, 0.99.

All formulas referenced in docs/MARKET_RISK_METHODS.md.
"""
from __future__ import annotations

import math
import warnings
from dataclasses import dataclass, field
from typing import Any

import numpy as np
from scipy import stats

# ---------------------------------------------------------------------------
# Output schema
# ---------------------------------------------------------------------------

@dataclass
class VaRResult:
    method: str
    confidence: float
    horizon_days: int
    var: float               # VaR as a positive loss fraction
    es: float                # Expected Shortfall as a positive loss fraction
    var_bootstrap_ci: tuple[float, float] | None = None   # (lower, upper) 95% CI
    es_bootstrap_ci: tuple[float, float] | None = None
    n_obs: int = 0
    warnings: list[str] = field(default_factory=list)
    assumptions: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Bootstrap CI
# ---------------------------------------------------------------------------

def _bootstrap_var_es(
    losses: np.ndarray,
    confidence: float,
    n_boot: int = 500,
    seed: int = 42,
) -> tuple[tuple[float, float], tuple[float, float]]:
    """Returns 95% bootstrap CI for historical VaR and ES."""
    rng = np.random.default_rng(seed)
    var_samples = []
    es_samples = []
    n = len(losses)
    for _ in range(n_boot):
        sample = rng.choice(losses, size=n, replace=True)
        q = float(np.percentile(sample, confidence * 100))
        var_samples.append(q)
        tail = sample[sample >= q]
        es_samples.append(float(tail.mean()) if len(tail) > 0 else q)
    var_ci = (float(np.percentile(var_samples, 2.5)), float(np.percentile(var_samples, 97.5)))
    es_ci = (float(np.percentile(es_samples, 2.5)), float(np.percentile(es_samples, 97.5)))
    return var_ci, es_ci


def _warn_thin_tail(losses: np.ndarray, confidence: float) -> list[str]:
    """Warn if fewer than 10 observations in the tail."""
    warns = []
    n_tail = int((1 - confidence) * len(losses))
    if n_tail < 10:
        warns.append(
            f"Only ~{n_tail} observations in the {(1-confidence)*100:.1f}% tail "
            f"(n={len(losses)}). VaR/ES estimates are unreliable. "
            "Consider a longer lookback window."
        )
    return warns


# ---------------------------------------------------------------------------
# Horizon scaling
# ---------------------------------------------------------------------------

def _scale_horizon(var_1d: float, es_1d: float, horizon: int) -> tuple[float, float]:
    """Scale 1-day VaR/ES to h-day using √h (square-root-of-time rule)."""
    factor = math.sqrt(horizon)
    return var_1d * factor, es_1d * factor


# ---------------------------------------------------------------------------
# Individual VaR methods (all operate on 1-day losses; scaling applied after)
# ---------------------------------------------------------------------------

def _historical(losses: np.ndarray, confidence: float, bootstrap: bool = True) -> tuple[float, float, list[str], Any, Any]:
    var = float(np.percentile(losses, confidence * 100))
    tail = losses[losses >= var]
    es = float(tail.mean()) if len(tail) > 0 else var
    warns = _warn_thin_tail(losses, confidence)
    var_ci, es_ci = _bootstrap_var_es(losses, confidence) if bootstrap else (None, None)
    return var, es, warns, var_ci, es_ci


def _gaussian(losses: np.ndarray, confidence: float) -> tuple[float, float, list[str]]:
    mu = float(losses.mean())
    sig = float(losses.std(ddof=1))
    z = stats.norm.ppf(confidence)
    var = mu + z * sig
    # ES for normal: μ + σ × φ(z)/(1-α)
    es = mu + sig * stats.norm.pdf(z) / (1 - confidence)
    warns = _warn_thin_tail(losses, confidence)
    return var, es, warns


def _student_t(losses: np.ndarray, confidence: float) -> tuple[float, float, list[str]]:
    warns = _warn_thin_tail(losses, confidence)
    try:
        df_fit, loc_fit, scale_fit = stats.t.fit(losses)
        var = float(stats.t.ppf(confidence, df=df_fit, loc=loc_fit, scale=scale_fit))
        # ES for Student-t
        t_q = stats.t.ppf(confidence, df=df_fit)
        es_std = (stats.t.pdf(t_q, df=df_fit) / (1 - confidence)) * ((df_fit + t_q ** 2) / (df_fit - 1))
        es = loc_fit + scale_fit * es_std
        es = float(es)
        if df_fit <= 1:
            warns.append(f"Fitted Student-t df={df_fit:.2f} ≤ 1; ES undefined. Falling back to VaR.")
            es = var
    except (RuntimeError, ValueError, TypeError, FloatingPointError) as exc:
        warns.append(f"Student-t fitting failed ({exc}); falling back to Gaussian.")
        return _gaussian(losses, confidence)
    return var, es, warns


def _cornish_fisher(losses: np.ndarray, confidence: float) -> tuple[float, float, list[str]]:
    """
    Cornish-Fisher VaR adjusting standard normal quantile for skew (S) and excess kurtosis (K):
        z_CF = z + (z²-1)S/6 + (z³-3z)K/24 - (2z³-5z)S²/36
    """
    warns = _warn_thin_tail(losses, confidence)
    mu = float(losses.mean())
    sig = float(losses.std(ddof=1))
    S = float(stats.skew(losses))
    K = float(stats.kurtosis(losses))  # excess kurtosis
    z = stats.norm.ppf(confidence)
    z_cf = z + (z**2 - 1) * S / 6 + (z**3 - 3*z) * K / 24 - (2*z**3 - 5*z) * S**2 / 36
    var = mu + z_cf * sig
    # ES approximated via Gaussian ES scaled by same CF factor
    es_gauss = mu + sig * stats.norm.pdf(z) / (1 - confidence)
    cf_ratio = z_cf / z if z != 0 else 1.0
    es = es_gauss * cf_ratio
    return var, es, warns


def _ewma(losses: np.ndarray, confidence: float, lam: float = 0.94) -> tuple[float, float, list[str]]:
    """
    EWMA variance (RiskMetrics): σ²_t = λσ²_{t-1} + (1-λ)L²_{t-1}.
    VaR uses the last estimated σ with Gaussian assumption.
    λ=0.94 is the RiskMetrics daily standard.
    """
    warns = _warn_thin_tail(losses, confidence)
    if len(losses) < 5:
        warns.append("Too few observations for EWMA. Falling back to Gaussian.")
        return _gaussian(losses, confidence)
    var_t = float(losses[:5].var(ddof=0))
    for l_t in losses[5:]:
        var_t = lam * var_t + (1 - lam) * l_t ** 2
    sig_t = math.sqrt(var_t)
    mu = float(losses.mean())
    z = stats.norm.ppf(confidence)
    var = mu + z * sig_t
    es = mu + sig_t * stats.norm.pdf(z) / (1 - confidence)
    return var, es, warns


def _garch(losses: np.ndarray, confidence: float) -> tuple[float, float, list[str]]:
    """GARCH(1,1) via arch library. Falls back to EWMA if arch unavailable."""
    warns: list[str] = []
    try:
        from arch import arch_model  # type: ignore
        # Rescale to percent for numerical stability
        scale = 100.0
        pct_losses = losses * scale
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            gm = arch_model(pct_losses, vol="Garch", p=1, q=1, dist="Normal", rescale=False)
            res = gm.fit(disp="off", show_warning=False)
        fcast = res.forecast(horizon=1, reindex=False)
        cond_var = float(fcast.variance.iloc[-1, 0]) / (scale ** 2)
        cond_sig = math.sqrt(max(cond_var, 1e-12))
        mu = float(losses.mean())
        z = stats.norm.ppf(confidence)
        var = mu + z * cond_sig
        es = mu + cond_sig * stats.norm.pdf(z) / (1 - confidence)
        warns.append(f"GARCH(1,1) fitted. ω={res.params.get('omega', float('nan')):.2e}, "
                     f"α={res.params.get('alpha[1]', float('nan')):.4f}, "
                     f"β={res.params.get('beta[1]', float('nan')):.4f}")
    except ImportError:
        warns.append("arch library not installed; falling back to EWMA.")
        return _ewma(losses, confidence)
    except (RuntimeError, ValueError, TypeError, FloatingPointError) as exc:
        warns.append(f"GARCH fitting failed ({exc}); falling back to EWMA.")
        return _ewma(losses, confidence)
    return var, es, warns


def _filtered_historical(losses: np.ndarray, confidence: float, lam: float = 0.94) -> tuple[float, float, list[str]]:
    """
    Filtered Historical Simulation (FHS):
    1. Estimate EWMA conditional vol at each t.
    2. Standardise residuals: e_t = L_t / σ_t.
    3. Apply historical quantile to standardised residuals.
    4. Scale back by current conditional vol.
    """
    warns: list[str] = []
    if len(losses) < 30:
        warns.append("Insufficient observations for FHS. Falling back to EWMA.")
        return _ewma(losses, confidence)
    vols = []
    var_t = float(losses[:5].var(ddof=0)) or 1e-6
    for l_t in losses:
        vols.append(math.sqrt(var_t))
        var_t = lam * var_t + (1 - lam) * l_t ** 2
    vols_arr = np.array(vols)
    std_resid = losses / np.where(vols_arr > 0, vols_arr, 1e-6)
    # Current conditional vol = last in ewma sequence
    cur_var = lam * vols[-1] ** 2 + (1 - lam) * losses[-1] ** 2
    cur_sig = math.sqrt(max(cur_var, 1e-12))
    # Historical quantile of standardised residuals
    q_resid = float(np.percentile(std_resid, confidence * 100))
    var = q_resid * cur_sig
    tail = std_resid[std_resid >= q_resid]
    es_resid = float(tail.mean()) if len(tail) > 0 else q_resid
    es = es_resid * cur_sig
    warns += _warn_thin_tail(losses, confidence)
    return var, es, warns


def _monte_carlo(
    losses: np.ndarray,
    cov_matrix: np.ndarray | None,
    weights: np.ndarray | None,
    confidence: float,
    n_simulations: int = 10_000,
    seed: int = 42,
) -> tuple[float, float, list[str]]:
    """
    Correlated Monte Carlo VaR using Cholesky decomposition.
    If cov_matrix is provided, uses correlated multi-asset simulation.
    Otherwise uses univariate normal with sample σ.
    """
    warns: list[str] = []
    rng = np.random.default_rng(seed)
    mu = float(losses.mean())
    sig = float(losses.std(ddof=1))

    if cov_matrix is not None and weights is not None and len(weights) > 1:
        n_assets = len(weights)
        try:
            chol = np.linalg.cholesky(cov_matrix + np.eye(n_assets) * 1e-8)
            z = rng.standard_normal((n_simulations, n_assets))
            sim_returns = -z @ chol.T   # losses
            sim_portfolio = sim_returns @ weights
        except np.linalg.LinAlgError:
            warns.append("Covariance matrix not positive definite; falling back to univariate MC.")
            sim_portfolio = rng.normal(mu, sig, n_simulations)
    else:
        sim_portfolio = rng.normal(mu, sig, n_simulations)

    var = float(np.percentile(sim_portfolio, confidence * 100))
    tail = sim_portfolio[sim_portfolio >= var]
    es = float(tail.mean()) if len(tail) > 0 else var
    warns.append(f"MC: {n_simulations:,} simulations, seed={seed}")
    return var, es, warns


# ---------------------------------------------------------------------------
# Unified estimator
# ---------------------------------------------------------------------------

def estimate_var(
    losses: np.ndarray,
    method: str,
    confidence: float,
    horizon_days: int = 1,
    cov_matrix: np.ndarray | None = None,
    weights: np.ndarray | None = None,
    bootstrap: bool = True,
    n_simulations: int = 10_000,
    mc_seed: int = 42,
    ewma_lambda: float = 0.94,
) -> VaRResult:
    """
    Unified VaR/ES estimator. Returns a VaRResult dataclass.

    Args:
        losses:        1-D array of portfolio losses (positive = loss).
        method:        One of: historical | gaussian | student_t | cornish_fisher |
                               ewma | garch | fhs | monte_carlo
        confidence:    Confidence level, e.g. 0.95.
        horizon_days:  Scaling horizon (1/5/10). Uses √T rule for parametric;
                       direct simulation for MC.
        cov_matrix:    (n×n) covariance matrix of asset losses (for MC).
        weights:       Portfolio weights (for MC).
        bootstrap:     Whether to compute bootstrap CI (historical only).
        n_simulations: Number of MC paths.
        mc_seed:       Reproducibility seed for MC.
        ewma_lambda:   Decay factor for EWMA/FHS (default 0.94 per RiskMetrics).
    """
    losses = np.asarray(losses, dtype=float)
    losses = losses[np.isfinite(losses)]
    n = len(losses)

    var_ci: tuple[float, float] | None = None
    es_ci: tuple[float, float] | None = None
    warns: list[str] = []
    assumptions: dict[str, Any] = {
        "method": method,
        "confidence": confidence,
        "horizon_days": horizon_days,
        "n_observations": n,
        "loss_convention": "positive = loss",
    }

    if method == "historical":
        var_1d, es_1d, warns, var_ci, es_ci = _historical(losses, confidence, bootstrap)
        assumptions["scaling"] = "empirical quantile; bootstrap CI on historical distribution"
    elif method == "gaussian":
        var_1d, es_1d, warns = _gaussian(losses, confidence)
        assumptions["scaling"] = "√T (square-root-of-time)"
    elif method == "student_t":
        var_1d, es_1d, warns = _student_t(losses, confidence)
        assumptions["note"] = "MLE-fitted Student-t; tail ES uses analytical formula"
    elif method == "cornish_fisher":
        var_1d, es_1d, warns = _cornish_fisher(losses, confidence)
        assumptions["note"] = "Cornish-Fisher expansion adjusting for skew and excess kurtosis"
    elif method == "ewma":
        var_1d, es_1d, warns = _ewma(losses, confidence, lam=ewma_lambda)
        assumptions["lambda"] = ewma_lambda
        assumptions["note"] = "RiskMetrics EWMA conditional variance"
    elif method == "garch":
        var_1d, es_1d, warns = _garch(losses, confidence)
        assumptions["note"] = "GARCH(1,1) conditional variance via arch library"
    elif method == "fhs":
        var_1d, es_1d, warns = _filtered_historical(losses, confidence, lam=ewma_lambda)
        assumptions["lambda"] = ewma_lambda
        assumptions["note"] = "Filtered Historical Simulation: EWMA-standardised residuals"
    elif method == "monte_carlo":
        var_1d, es_1d, warns = _monte_carlo(losses, cov_matrix, weights, confidence,
                                             n_simulations=n_simulations, seed=mc_seed)
        assumptions["n_simulations"] = n_simulations
        assumptions["seed"] = mc_seed
        assumptions["note"] = "Correlated MC via Cholesky decomposition"
    else:
        raise ValueError(
            f"Unknown VaR method '{method}'. Supported: "
            "historical | gaussian | student_t | cornish_fisher | ewma | garch | fhs | monte_carlo"
        )

    if horizon_days > 1 and method != "monte_carlo":
        var_h, es_h = _scale_horizon(var_1d, es_1d, horizon_days)
        if var_ci:
            var_ci = (var_ci[0] * math.sqrt(horizon_days), var_ci[1] * math.sqrt(horizon_days))
        if es_ci:
            es_ci = (es_ci[0] * math.sqrt(horizon_days), es_ci[1] * math.sqrt(horizon_days))
    else:
        var_h, es_h = var_1d, es_1d

    return VaRResult(
        method=method,
        confidence=confidence,
        horizon_days=horizon_days,
        var=float(var_h),
        es=float(es_h),
        var_bootstrap_ci=var_ci,
        es_bootstrap_ci=es_ci,
        n_obs=n,
        warnings=warns,
        assumptions=assumptions,
    )


# ---------------------------------------------------------------------------
# Multi-method sweep
# ---------------------------------------------------------------------------

SUPPORTED_METHODS = ["historical", "gaussian", "student_t", "cornish_fisher", "ewma", "garch", "fhs", "monte_carlo"]
SUPPORTED_CONFIDENCES = [0.90, 0.95, 0.975, 0.99]
SUPPORTED_HORIZONS = [1, 5, 10]


def estimate_all(
    losses: np.ndarray,
    methods: list[str] | None = None,
    confidences: list[float] | None = None,
    horizons: list[int] | None = None,
    cov_matrix: np.ndarray | None = None,
    weights: np.ndarray | None = None,
    bootstrap: bool = True,
    mc_seed: int = 42,
) -> list[VaRResult]:
    """Run all requested method × confidence × horizon combinations."""
    methods = methods or SUPPORTED_METHODS
    confidences = confidences or [0.95, 0.99]
    horizons = horizons or [1]
    results = []
    for method in methods:
        for conf in confidences:
            for h in horizons:
                try:
                    res = estimate_var(
                        losses, method, conf, horizon_days=h,
                        cov_matrix=cov_matrix, weights=weights,
                        bootstrap=bootstrap, mc_seed=mc_seed,
                    )
                    results.append(res)
                except (ValueError, TypeError, RuntimeError, FloatingPointError) as exc:
                    results.append(VaRResult(
                        method=method, confidence=conf, horizon_days=h,
                        var=float("nan"), es=float("nan"),
                        warnings=[f"Estimation failed: {exc}"],
                    ))
    return results
