import math

import numpy as np
from backend.app.services.market_risk.engine import Holding, MarketRiskEngine
from backend.app.services.market_risk.ticker_normalizer import (
    get_symbol_currency,
    normalize_ticker,
)
from pydantic import BaseModel
from scipy import stats


class VaRValidationPoint(BaseModel):
    date: str
    realized_loss: float
    forecast_var: float
    is_exception: bool


class VaRValidationResult(BaseModel):
    portfolio_name: str
    currency: str
    method: str  # historical or parametric
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
    kupiec_lr_stat: float | None
    kupiec_p_value: float | None
    kupiec_test_passed: bool
    christoffersen_lr_stat: float | None
    christoffersen_p_value: float | None
    christoffersen_test_passed: bool | None
    summary_message: str
    validation_points: list[VaRValidationPoint]


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
        lookback_window: int = 250
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

        # Validate portfolio currency matches asset currency
        asset_currencies = {s: get_symbol_currency(s) for s in symbols}
        distinct_asset_currencies = set(asset_currencies.values())
        if len(distinct_asset_currencies) > 1:
            raise ValueError(
                f"Mixed-currency portfolio detected: {asset_currencies}. "
                "Portfolios must be strictly single-currency (all USD or all INR). "
                "Silent FX conversion is prohibited."
            )
        inferred_curr = next(iter(distinct_asset_currencies))
        if currency.upper() != inferred_curr:
            raise ValueError(
                f"Portfolio currency mismatch: specified currency is '{currency.upper()}', "
                f"but assets are denominated in '{inferred_curr}' ({symbols})."
            )

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
        prices = self.risk_engine.load_price_history(symbols, allow_live=True)
        returns_df = self.risk_engine.calculate_returns(prices, method="simple")
        portfolio_returns = returns_df[symbols].dot(weights)
        portfolio_losses = -portfolio_returns  # Loss convention: loss is positive

        total_obs = len(portfolio_losses)
        if total_obs <= lookback_window + 10:
            raise ValueError(
                f"Insufficient historical data for rolling backtest. Need at least {lookback_window + 11} days, found {total_obs}."
            )

        z_score = stats.norm.ppf(confidence_level)
        validation_points = []
        exception_indicators = []
        exception_count = 0

        # Strict temporal separation: at step t, use only historical data [t - lookback_window : t]
        # and compare against realized loss at step t. Never peek into future rows.
        for t in range(lookback_window, total_obs):
            estimation_window = portfolio_losses.iloc[t - lookback_window: t]
            realized_loss_t = float(portfolio_losses.iloc[t])
            date_t = str(portfolio_losses.index[t].date())

            if method == "parametric":
                # Parametric VaR = z * sigma - mu
                window_rets = -estimation_window
                mu = float(window_rets.mean())
                sigma = float(window_rets.std(ddof=1))
                forecast_var = z_score * sigma - mu
            else:
                # Historical VaR: empirical quantile of losses
                forecast_var = float(np.percentile(estimation_window, confidence_level * 100))

            is_exception = realized_loss_t > forecast_var
            if is_exception:
                exception_count += 1
                exception_indicators.append(1)
            else:
                exception_indicators.append(0)

            validation_points.append(VaRValidationPoint(
                date=date_t,
                realized_loss=round(realized_loss_t, 6),
                forecast_var=round(forecast_var, 6),
                is_exception=is_exception
            ))

        forecast_count = len(validation_points)
        exception_rate = exception_count / forecast_count
        expected_rate = 1.0 - confidence_level
        expected_exceptions = round(forecast_count * expected_rate, 2)

        # 1. Basel Traffic-Light Zone (cumulative binomial probability)
        cum_prob = float(stats.binom.cdf(exception_count, forecast_count, expected_rate))
        if cum_prob < 0.95:
            basel_zone = "GREEN"
        elif cum_prob < 0.9999:
            basel_zone = "YELLOW"
        else:
            basel_zone = "RED"

        # 2. Kupiec POF Likelihood Ratio Test
        # LR = -2 * ln( ( (1-p)^(N-x) * p^x ) / ( (1-phat)^(N-x) * phat^x ) )
        lr_stat = None
        p_val = None
        passed = False

        if exception_count == 0:
            lr_stat = -2.0 * forecast_count * math.log(1.0 - expected_rate)
            p_val = float(1.0 - stats.chi2.cdf(lr_stat, df=1))
            passed = p_val >= 0.05
        elif exception_count == forecast_count:
            lr_stat = 999.0
            p_val = 0.0
            passed = False
        else:
            p = expected_rate
            p_hat = exception_rate
            log_lik_null = (forecast_count - exception_count) * math.log(1.0 - p) + exception_count * math.log(p)
            log_lik_alt = (forecast_count - exception_count) * math.log(1.0 - p_hat) + exception_count * math.log(p_hat)
            lr_stat = float(-2.0 * (log_lik_null - log_lik_alt))
            p_val = float(1.0 - stats.chi2.cdf(lr_stat, df=1))
            passed = p_val >= 0.05

        # 3. Christoffersen Independence Test
        # Evaluates first-order Markov independence of exception indicators
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

            # Log-likelihoods (with safeguards for 0 counts)
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

        summary = (
            f"Basel Zone: {basel_zone} (cum prob {cum_prob:.4f}). "
            f"Kupiec test {'PASSED' if passed else 'REJECTED'} (p-value {p_val:.4f}). "
            f"Exceptions: {exception_count} observed vs {expected_exceptions:.1f} expected ({exception_rate:.2%} vs {expected_rate:.2%})."
        )

        return VaRValidationResult(
            portfolio_name=portfolio_name,
            currency=currency,
            method=method,
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
            kupiec_lr_stat=round(lr_stat, 4) if lr_stat is not None else None,
            kupiec_p_value=round(p_val, 4) if p_val is not None else None,
            kupiec_test_passed=passed,
            christoffersen_lr_stat=round(christoffersen_lr, 4) if christoffersen_lr is not None else None,
            christoffersen_p_value=round(christoffersen_p, 4) if christoffersen_p is not None else None,
            christoffersen_test_passed=christoffersen_passed,
            summary_message=summary,
            validation_points=validation_points
        )
