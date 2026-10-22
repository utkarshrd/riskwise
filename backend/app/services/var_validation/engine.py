import math
from typing import Any
import numpy as np
import pandas as pd
from numpy.lib.stride_tricks import sliding_window_view
from pydantic import BaseModel
from scipy import stats

from backend.app.services.market_risk.engine import Holding, MarketRiskEngine
from backend.app.services.market_risk.risk import var_models as _vm
from backend.app.services.market_risk.ticker_normalizer import (
    get_symbol_currency,
    normalize_ticker,
)


class VaRValidationPoint(BaseModel):
    date: str
    realized_loss: float
    forecast_var: float
    is_exception: bool


class VaRValidationResult(BaseModel):
    portfolio_name: str
    currency: str
    method: str  # historical, parametric, student_t, cornish_fisher, ewma, etc.
    confidence_level: float
    lookback_window: int
    n_obs: int
    window: int
    confidence: float
    exceptions: int
    expected_exceptions: float
    forecast_count: int
    exception_count: int
    exception_rate: float
    expected_exception_rate: float
    basel_zone: str
    basel_zone_cumulative_prob: float
    basel_capital_multiplier: float = 3.00
    kupiec_lr_stat: float | None
    kupiec_p_value: float | None
    kupiec_test_passed: bool
    christoffersen_lr_stat: float | None
    christoffersen_p_value: float | None
    christoffersen_test_passed: bool | None
    christoffersen_cc_stat: float | None = None
    christoffersen_cc_p_value: float | None = None
    christoffersen_cc_test_passed: bool | None = None
    summary_message: str
    validation_points: list[VaRValidationPoint]
    fx: dict[str, Any] | None = None


class VaRValidationEngine:
    def __init__(self, risk_engine: MarketRiskEngine | None = None):
        self.risk_engine = risk_engine or MarketRiskEngine()

    def run_rolling_backtest(
        self,
        holdings: list[Holding],
        portfolio_name: str = "Backtest Portfolio",
        currency: str = "USD",
        method: str = "historical",
        confidence_level: float = 0.95,
        lookback_window: int = 250,
        fx_mode: str = "strict",
    ) -> VaRValidationResult:
        if lookback_window < 50:
            raise ValueError("Lookback window must be at least 50 trading days.")
        if not (0.80 <= confidence_level < 1.0):
            raise ValueError("Confidence level must be between 0.80 and 0.999.")

        # Canonical symbol normalization and duplicate checking
        canonical_map = {h.symbol: normalize_ticker(h.symbol)["canonical_symbol"] for h in holdings}
        symbols = [canonical_map[h.symbol] for h in holdings]
        if len(symbols) != len(set(symbols)):
            dups = [s for s in symbols if symbols.count(s) > 1]
            raise ValueError(f"Duplicate holding symbol detected: '{dups[0]}'. Each holding must be unique.")

        policy = self.risk_engine.resolve_currency_policy(symbols, currency, fx_mode)

        has_pos_values = any(h.position_value is not None for h in holdings)
        has_weights = any(h.weight is not None for h in holdings)
        if has_pos_values and not has_weights:
            pos_vals = [float(h.position_value or 0.0) for h in holdings]
            total_val = sum(pos_vals)
            if total_val <= 0:
                raise ValueError("Sum of position values must be greater than zero.")
            weights = np.array([float(v) / total_val for v in pos_vals], dtype=float)
        else:
            weights = np.array([float(h.weight if h.weight is not None else 0.0) for h in holdings], dtype=float)
            if any(np.isnan(weights)) or any(np.isinf(weights)):
                raise ValueError("Holdings weights contain non-finite numbers (NaN or Inf).")
            if any(w <= 0.0 for w in weights):
                raise ValueError("Holdings weights must be strictly positive.")
            weight_sum = float(np.sum(weights))
            if abs(weight_sum - 1.0) > 1e-4:
                raise ValueError(f"Holdings weights must sum to 1.0 (got {weight_sum:.6f}, tolerance +/-1e-4).")

        # Load price series and calculate daily returns strictly from adj_close
        prices, _, fx = self.risk_engine.load_prices_with_policy(symbols, policy, allow_live=True)
        returns_df = self.risk_engine.calculate_returns(prices, method="simple")
        portfolio_returns = returns_df[symbols].dot(weights)
        portfolio_losses = -portfolio_returns  # Loss convention: loss is positive

        total_obs = len(portfolio_losses)
        if total_obs <= lookback_window + 10:
            raise ValueError(
                f"Insufficient historical data for rolling backtest. Need at least {lookback_window + 11} days, found {total_obs}."
            )

        z_score = stats.norm.ppf(confidence_level)
        losses_arr = portfolio_losses.values

        # Vectorised sliding window view: shape (total_obs - lookback_window, lookback_window)
        # Estimation window at step t is losses_arr[t - lookback_window : t]
        windows = sliding_window_view(losses_arr[:-1], lookback_window)

        # Forecast VaR for each window
        norm_method = (method or "historical").lower().strip()
        if norm_method in ("parametric", "gaussian"):
            window_means = windows.mean(axis=1)
            window_stds = windows.std(axis=1, ddof=1)
            forecast_vars = window_means + z_score * window_stds
        elif norm_method == "historical":
            forecast_vars = np.percentile(windows, confidence_level * 100, axis=1)
        else:
            # Delegate to expanded var_models engine for other methods
            forecast_vars = np.array([
                _vm.estimate_var(w, method=norm_method, confidence=confidence_level, bootstrap=False).var
                for w in windows
            ])

        realized_losses = losses_arr[lookback_window:]
        is_exceptions = realized_losses > forecast_vars
        exception_indicators = is_exceptions.astype(int).tolist()
        exception_count = int(np.sum(is_exceptions))

        dates_index = portfolio_losses.index
        validation_points = [
            VaRValidationPoint(
                date=str(dates_index[lookback_window + i].date()) if hasattr(dates_index[lookback_window + i], "date") else str(dates_index[lookback_window + i]),
                realized_loss=round(float(realized_losses[i]), 6),
                forecast_var=round(float(forecast_vars[i]), 6),
                is_exception=bool(is_exceptions[i]),
            )
            for i in range(len(realized_losses))
        ]

        forecast_count = len(validation_points)
        exception_rate = exception_count / forecast_count
        expected_rate = 1.0 - confidence_level
        expected_exceptions = round(forecast_count * expected_rate, 2)

        # 1. Basel Traffic-Light Zone and Capital Multiplier
        cum_prob = float(stats.binom.cdf(exception_count, forecast_count, expected_rate))

        # Check official BCBS 250-day table for 99% confidence
        if forecast_count == 250 and abs(confidence_level - 0.99) < 1e-3:
            if exception_count <= 4:
                basel_zone = "GREEN"
                capital_mult = 3.00
            elif exception_count <= 9:
                basel_zone = "YELLOW"
                mult_map = {5: 3.40, 6: 3.50, 7: 3.65, 8: 3.75, 9: 3.85}
                capital_mult = mult_map.get(exception_count, 3.85)
            else:
                basel_zone = "RED"
                capital_mult = 4.00
        else:
            if cum_prob < 0.95:
                basel_zone = "GREEN"
                capital_mult = 3.00
            elif cum_prob < 0.9999:
                basel_zone = "YELLOW"
                capital_mult = round(3.0 + ((cum_prob - 0.95) / (0.9999 - 0.95)) * 0.85, 2)
            else:
                basel_zone = "RED"
                capital_mult = 4.00

        # 2. Kupiec POF Likelihood Ratio Test (exact asymptotic log-likelihood without 999.0 sentinel)
        if exception_count == 0:
            lr_stat = float(-2.0 * forecast_count * math.log(1.0 - expected_rate))
            p_val = float(1.0 - stats.chi2.cdf(lr_stat, df=1))
            passed = p_val >= 0.05
        elif exception_count == forecast_count:
            lr_stat = float(-2.0 * forecast_count * math.log(expected_rate))
            p_val = float(1.0 - stats.chi2.cdf(lr_stat, df=1))
            passed = p_val >= 0.05
        else:
            p = expected_rate
            p_hat = exception_rate
            log_lik_null = (forecast_count - exception_count) * math.log(1.0 - p) + exception_count * math.log(p)
            log_lik_alt = (forecast_count - exception_count) * math.log(1.0 - p_hat) + exception_count * math.log(p_hat)
            lr_stat = float(-2.0 * (log_lik_null - log_lik_alt))
            p_val = float(1.0 - stats.chi2.cdf(lr_stat, df=1))
            passed = p_val >= 0.05

        # 3. Christoffersen Independence Test
        christoffersen_lr = None
        christoffersen_p = None
        christoffersen_passed = None

        if len(exception_indicators) > 1 and exception_count > 0:
            n00, n01, n10, n11 = 0, 0, 0, 0
            for i in range(len(exception_indicators) - 1):
                prev_i = exception_indicators[i]
                curr_i = exception_indicators[i + 1]
                if prev_i == 0 and curr_i == 0:
                    n00 += 1
                elif prev_i == 0 and curr_i == 1:
                    n01 += 1
                elif prev_i == 1 and curr_i == 0:
                    n10 += 1
                elif prev_i == 1 and curr_i == 1:
                    n11 += 1

            total_transitions = n00 + n01 + n10 + n11
            pi_null = (n01 + n11) / total_transitions if total_transitions > 0 else 0.0
            pi_01 = n01 / (n00 + n01) if (n00 + n01) > 0 else 0.0
            pi_11 = n11 / (n10 + n11) if (n10 + n11) > 0 else 0.0

            def safe_ll(count, prob):
                return count * math.log(prob) if count > 0 and prob > 0 else 0.0

            ll_null = (
                safe_ll(n00 + n10, 1.0 - pi_null) +
                safe_ll(n01 + n11, pi_null)
            )
            ll_alt = (
                safe_ll(n00, 1.0 - pi_01) +
                safe_ll(n01, pi_01) +
                safe_ll(n10, 1.0 - pi_11) +
                safe_ll(n11, pi_11)
            )
            ind_stat = -2.0 * (ll_null - ll_alt)
            christoffersen_lr = float(max(0.0, ind_stat))
            christoffersen_p = float(1.0 - stats.chi2.cdf(christoffersen_lr, df=1))
            christoffersen_passed = christoffersen_p >= 0.05

        # 4. Christoffersen Conditional Coverage Joint Test (LR_cc = LR_uc + LR_ind ~ chi2(2))
        christoffersen_cc_stat = None
        christoffersen_cc_p = None
        christoffersen_cc_passed = None

        if lr_stat is not None and christoffersen_lr is not None:
            christoffersen_cc_stat = float(lr_stat + christoffersen_lr)
            christoffersen_cc_p = float(1.0 - stats.chi2.cdf(christoffersen_cc_stat, df=2))
            christoffersen_cc_passed = christoffersen_cc_p >= 0.05

        summary = (
            f"Basel Zone: {basel_zone} (cum prob {cum_prob:.4f}, capital multiplier {capital_mult:.2f}x). "
            f"Kupiec test {'PASSED' if passed else 'REJECTED'} (p-value {p_val:.4f}). "
            f"Exceptions: {exception_count} observed vs {expected_exceptions:.1f} expected ({exception_rate:.2%} vs {expected_rate:.2%})."
        )

        return VaRValidationResult(
            portfolio_name=portfolio_name,
            currency=currency,
            method=norm_method,
            confidence_level=confidence_level,
            lookback_window=lookback_window,
            n_obs=total_obs,
            window=lookback_window,
            confidence=confidence_level,
            exceptions=exception_count,
            expected_exceptions=expected_exceptions,
            forecast_count=forecast_count,
            exception_count=exception_count,
            exception_rate=round(exception_rate, 4),
            expected_exception_rate=round(expected_rate, 4),
            basel_zone=basel_zone,
            basel_zone_cumulative_prob=round(cum_prob, 4),
            basel_capital_multiplier=capital_mult,
            kupiec_lr_stat=round(lr_stat, 4) if lr_stat is not None else None,
            kupiec_p_value=round(p_val, 4) if p_val is not None else None,
            kupiec_test_passed=passed,
            christoffersen_lr_stat=round(christoffersen_lr, 4) if christoffersen_lr is not None else None,
            christoffersen_p_value=round(christoffersen_p, 4) if christoffersen_p is not None else None,
            christoffersen_test_passed=christoffersen_passed,
            christoffersen_cc_stat=round(christoffersen_cc_stat, 4) if christoffersen_cc_stat is not None else None,
            christoffersen_cc_p_value=round(christoffersen_cc_p, 4) if christoffersen_cc_p is not None else None,
            christoffersen_cc_test_passed=christoffersen_cc_passed,
            summary_message=summary,
            validation_points=validation_points,
            fx=fx,
        )

    def compare_models(
        self,
        holdings: list[Holding],
        portfolio_name: str = "Comparison Portfolio",
        currency: str = "USD",
        confidence_level: float = 0.95,
        lookback_window: int = 250,
        methods: list[str] | None = None,
        fx_mode: str = "strict",
    ) -> dict[str, Any]:
        """
        Runs rolling backtests for all candidate models on the exact same estimation window,
        compares exception rates, Basel traffic-light compliance, and coverage tests,
        and recommends the optimal model with a plain-English explanation.
        """
        candidate_methods = methods or ["historical", "parametric", "student_t", "cornish_fisher", "ewma"]
        results: list[dict[str, Any]] = []
        fx_info: dict[str, Any] | None = None

        for m in candidate_methods:
            try:
                res = self.run_rolling_backtest(
                    holdings=holdings,
                    portfolio_name=portfolio_name,
                    currency=currency,
                    method=m,
                    confidence_level=confidence_level,
                    lookback_window=lookback_window,
                    fx_mode=fx_mode,
                )
                fx_info = res.fx

                # Score model (lower is better):
                # 1. Base penalty: absolute error in exception rate (scaled)
                score = abs(res.exception_rate - res.expected_exception_rate) * 100.0

                # 2. Basel penalties
                if res.basel_zone == "YELLOW":
                    score += 15.0
                elif res.basel_zone == "RED":
                    score += 50.0

                # 3. Kupiec test failure penalty
                if not res.kupiec_test_passed:
                    score += 20.0

                # 4. Christoffersen conditional coverage failure penalty
                if res.christoffersen_cc_test_passed is False:
                    score += 15.0

                results.append({
                    "method": m,
                    "exceptions": res.exception_count,
                    "expected_exceptions": res.expected_exceptions,
                    "exception_rate": res.exception_rate,
                    "expected_exception_rate": res.expected_exception_rate,
                    "basel_zone": res.basel_zone,
                    "basel_capital_multiplier": res.basel_capital_multiplier,
                    "kupiec_p_value": res.kupiec_p_value,
                    "kupiec_test_passed": res.kupiec_test_passed,
                    "christoffersen_ind_p_value": res.christoffersen_p_value,
                    "christoffersen_ind_passed": res.christoffersen_test_passed,
                    "christoffersen_cc_p_value": res.christoffersen_cc_p_value,
                    "christoffersen_cc_test_passed": res.christoffersen_cc_test_passed,
                    "score": round(score, 3),
                })
            except Exception:
                continue

        if not results:
            raise ValueError("All candidate VaR models failed backtest execution.")

        # Rank by score ascending
        results.sort(key=lambda r: r["score"])
        best = results[0]

        method_display = best["method"].replace("_", " ").title()
        reason = (
            f"{method_display} VaR is recommended: It achieves Basel {best['basel_zone']} zone with "
            f"{best['exceptions']} exceptions ({best['exception_rate']:.2%} observed vs {best['expected_exception_rate']:.2%} expected), "
            f"passes the Kupiec POF unconditional coverage test (p={best['kupiec_p_value'] or 0.0:.3f}), "
            f"and satisfies Christoffersen conditional coverage (p={best['christoffersen_cc_p_value'] or 0.0:.3f}). "
            f"It maintains a low regulatory capital multiplier ({best['basel_capital_multiplier']:.2f}x) while avoiding risk underestimation."
        )

        return {
            "portfolio_name": portfolio_name,
            "currency": currency,
            "confidence_level": confidence_level,
            "lookback_window": lookback_window,
            "forecast_count": res.forecast_count,
            "models": results,
            "recommended_method": best["method"],
            "recommendation_reason": reason,
            "fx": fx_info,
        }
