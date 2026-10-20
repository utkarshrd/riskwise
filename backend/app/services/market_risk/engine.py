import math
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from pydantic import BaseModel
from scipy import stats


class Holding(BaseModel):
    symbol: str
    weight: float | None = None
    position_value: float | None = None


class PortfolioRiskMetrics(BaseModel):
    portfolio_name: str
    currency: str
    symbols: list[str]
    weights: list[float]
    portfolio_value: float | None = None
    position_values: dict[str, float] | None = None
    observations_count: int
    start_date: str
    end_date: str
    data_source_mode: str = "offline_snapshot"
    annualized_volatility: float
    annualization_factor: int = 252
    historical_var_95: float
    historical_var_99: float
    parametric_var_95: float
    parametric_var_99: float
    expected_shortfall_95: float
    expected_shortfall_99: float
    historical_var_95_amount: float | None = None
    historical_var_99_amount: float | None = None
    parametric_var_95_amount: float | None = None
    parametric_var_99_amount: float | None = None
    expected_shortfall_95_amount: float | None = None
    expected_shortfall_99_amount: float | None = None
    maximum_drawdown: float
    mean_daily_return: float
    asset_correlations: dict[str, dict[str, float]]
    loss_convention: str = "Loss is positive magnitude (Loss = -Return)"
    assumptions: dict[str, Any]


class StressScenario(BaseModel):
    name: str
    description: str
    shocks: dict[str, float]  # symbol -> shock fraction (e.g. -0.20 for -20%)


class StressScenarioResult(BaseModel):
    scenario_name: str
    portfolio_loss_pct: float
    individual_asset_losses: dict[str, float]
    assumptions: dict[str, Any]


from backend.app.services.market_risk.market_data_service import MarketDataService
from backend.app.services.market_risk.ticker_normalizer import (
    get_symbol_currency,
    normalize_ticker,
)


class MarketRiskEngine:
    def __init__(
        self,
        snapshots_dir: Path | None = None,
        manifest_path: Path | None = None,
        data_service: MarketDataService | None = None
    ):
        if snapshots_dir is None:
            from backend.app.core.config import settings
            self.snapshots_dir = settings.DATA_DIR / "market_snapshots"
            self.manifest_path = settings.DATA_DIR / "manifests" / "market_manifest.json"
        else:
            self.snapshots_dir = snapshots_dir
            self.manifest_path = manifest_path or (snapshots_dir.parent / "manifests" / "market_manifest.json")

        self.data_service = data_service or MarketDataService(
            snapshots_dir=self.snapshots_dir,
            manifest_path=self.manifest_path
        )

    def _get_symbol_currency(self, symbol: str) -> str:
        """Determines asset currency from ticker normalizer or manifest."""
        return get_symbol_currency(symbol)

    def load_price_history(self, symbols: list[str], allow_live: bool = True) -> pd.DataFrame:
        """
        Loads aligned daily price history for requested symbols.
        Checks snapshot cache first, falling back to live retrieval via yfinance if permitted.
        Strictly reads 'adj_close' (split and dividend adjusted prices).
        Validates strictly positive prices, single currency uniformity, and at least 30 observations.
        """
        prices, _, _ = self.data_service.load_aligned_prices(symbols, allow_live=allow_live)
        return prices

    @staticmethod
    def calculate_returns(prices: pd.DataFrame, method: str = "simple") -> pd.DataFrame:
        """
        Calculate daily returns from price series.
        - 'simple': Discrete percentage change R_t = (P_t - P_{t-1}) / P_{t-1}
        - 'log': Continuously compounded return r_t = ln(P_t / P_{t-1})
        """
        if method == "log":
            return np.log(prices / prices.shift(1)).dropna()
        elif method == "simple":
            return prices.pct_change().dropna()
        else:
            raise ValueError(f"Unknown return calculation method '{method}'. Supported methods are 'simple' and 'log'.")

    def derive_historical_stress_scenarios(self, symbols: list[str]) -> list[StressScenario]:
        """
        Derives stress scenarios deterministically from the real snapshot observations:
        1. Historical_Worst_Single_Day: Minimum 1-day return observed per asset.
        2. Historical_Peak_to_Trough_Drawdown: Maximum cumulative drawdown observed per asset.
        Zero hidden constants or arbitrary numbers.
        """
        prices = self.load_price_history(symbols)
        simple_returns = self.calculate_returns(prices, method="simple")

        # 1. Worst single-day shock per asset
        worst_day_shocks = {}
        for sym in symbols:
            worst_ret = float(simple_returns[sym].min())
            worst_day_shocks[sym] = round(worst_ret, 4)

        # 2. Maximum peak-to-trough drawdown per asset
        max_dd_shocks = {}
        for sym in symbols:
            cummax = prices[sym].cummax()
            dd_series = (prices[sym] - cummax) / cummax
            max_dd = float(dd_series.min())
            max_dd_shocks[sym] = round(max_dd, 4)

        return [
            StressScenario(
                name="Historical_Worst_Single_Day",
                description="Asset-level empirical maximum 1-day drop observed across the historical snapshot window.",
                shocks=worst_day_shocks
            ),
            StressScenario(
                name="Historical_Peak_to_Trough_Drawdown",
                description="Asset-level empirical maximum peak-to-trough drawdown observed across the historical snapshot window.",
                shocks=max_dd_shocks
            )
        ]

    def analyze_portfolio(
        self,
        holdings: list[Holding],
        portfolio_name: str = "Demo Portfolio",
        currency: str = "USD",
        lookback_days: int | None = None,
        return_method: str = "simple",
        portfolio_value: float | None = None,
        data_source_mode: str = "offline_snapshot"
    ) -> PortfolioRiskMetrics:
        if not holdings:
            raise ValueError("Portfolio must contain at least one holding.")

        # Canonical symbol normalization and duplicate checking
        canonical_map = {h.symbol: normalize_ticker(h.symbol)["canonical_symbol"] for h in holdings}
        symbols = [canonical_map[h.symbol] for h in holdings]
        if len(symbols) != len(set(symbols)):
            dups = [s for s in symbols if symbols.count(s) > 1]
            raise ValueError(f"Duplicate holding symbol detected: '{dups[0]}'. Each holding in the portfolio must be unique.")

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

        # Handle weights vs position values
        has_pos_values = any(h.position_value is not None for h in holdings)
        has_weights = any(h.weight is not None for h in holdings)

        if has_pos_values and not has_weights:
            pos_vals = [float(h.position_value or 0.0) for h in holdings]
            if any(np.isnan(pos_vals)) or any(np.isinf(pos_vals)):
                raise ValueError("Position values contain non-finite numbers (NaN or Inf).")
            if any(v <= 0.0 for v in pos_vals):
                raise ValueError("Position values must be strictly positive numbers.")
            total_pos_val = float(sum(pos_vals))
            weights = np.array([v / total_pos_val for v in pos_vals], dtype=float)
            effective_portfolio_value = total_pos_val
            position_values_dict = {s: round(v, 2) for s, v in zip(symbols, pos_vals)}
        else:
            weights = np.array([float(h.weight if h.weight is not None else 0.0) for h in holdings], dtype=float)
            if any(np.isnan(weights)) or any(np.isinf(weights)):
                raise ValueError("Holdings weights contain non-finite numbers (NaN or Inf).")
            if any(w <= 0.0 for w in weights):
                raise ValueError("Holdings weights must be strictly positive.")
            weight_sum = float(np.sum(weights))
            if abs(weight_sum - 1.0) > 1e-4:
                raise ValueError(f"Holdings weights must sum to 1.0 (got {weight_sum:.6f}, tolerance +/-1e-4). Silent normalization is prohibited.")
            effective_portfolio_value = portfolio_value
            position_values_dict = (
                {s: round(float(w) * effective_portfolio_value, 2) for s, w in zip(symbols, weights)}
                if effective_portfolio_value is not None
                else None
            )

        # Load prices via unified data service
        prices, data_src, _ = self.data_service.load_aligned_prices(symbols, allow_live=True)
        if data_source_mode == "offline_snapshot":
            data_source_mode = data_src

        if lookback_days:
            if lookback_days < 30:
                raise ValueError("Lookback period must be at least 30 days.")
            if len(prices) > lookback_days:
                prices = prices.iloc[-lookback_days:]

        returns_df = self.calculate_returns(prices, method=return_method)
        if len(returns_df) < 20:
            raise ValueError("Insufficient return observations for risk calculation.")

        # Portfolio daily return series
        portfolio_returns = returns_df[symbols].dot(weights)
        portfolio_losses = -portfolio_returns  # Loss convention: loss is positive

        # 1. Volatility (Annualized using 252 trading day convention)
        daily_std = float(portfolio_returns.std(ddof=1))
        annualized_vol = daily_std * math.sqrt(252)

        # 2. Historical VaR and Expected Shortfall
        hist_var_95 = float(np.percentile(portfolio_losses, 95))
        hist_var_99 = float(np.percentile(portfolio_losses, 99))

        # Expected Shortfall (CVaR): Mean of losses exceeding VaR threshold
        tail_95 = portfolio_losses[portfolio_losses >= hist_var_95]
        es_95 = float(tail_95.mean()) if len(tail_95) > 0 else hist_var_95

        tail_99 = portfolio_losses[portfolio_losses >= hist_var_99]
        es_99 = float(tail_99.mean()) if len(tail_99) > 0 else hist_var_99

        # 3. Parametric VaR (Gaussian assumption using sample mean & std)
        mean_ret = float(portfolio_returns.mean())
        z_95 = stats.norm.ppf(0.95)
        z_99 = stats.norm.ppf(0.99)
        param_var_95 = z_95 * daily_std - mean_ret
        param_var_99 = z_99 * daily_std - mean_ret

        # 4. Maximum Drawdown on simulated wealth path
        wealth_index = (1.0 + portfolio_returns).cumprod()
        previous_peaks = wealth_index.cummax()
        drawdowns = (wealth_index - previous_peaks) / previous_peaks
        max_drawdown = float(abs(drawdowns.min()))

        # 5. Correlation matrix
        corr_matrix = returns_df[symbols].corr().fillna(0.0).to_dict()

        start_dt = str(prices.index[0].date())
        end_dt = str(prices.index[-1].date())

        hist_var_95_rounded = round(hist_var_95, 4)
        hist_var_99_rounded = round(hist_var_99, 4)
        param_var_95_rounded = round(param_var_95, 4)
        param_var_99_rounded = round(param_var_99, 4)
        es_95_rounded = round(es_95, 4)
        es_99_rounded = round(es_99, 4)

        # Monetary loss amounts where portfolio value is known
        hist_var_95_amt = round(hist_var_95_rounded * effective_portfolio_value, 2) if effective_portfolio_value else None
        hist_var_99_amt = round(hist_var_99_rounded * effective_portfolio_value, 2) if effective_portfolio_value else None
        param_var_95_amt = round(param_var_95_rounded * effective_portfolio_value, 2) if effective_portfolio_value else None
        param_var_99_amt = round(param_var_99_rounded * effective_portfolio_value, 2) if effective_portfolio_value else None
        es_95_amt = round(es_95_rounded * effective_portfolio_value, 2) if effective_portfolio_value else None
        es_99_amt = round(es_99_rounded * effective_portfolio_value, 2) if effective_portfolio_value else None

        assumptions = {
            "annualization_factor": 252,
            "return_convention": return_method,
            "price_field": "adj_close",
            "weight_tolerance": 1e-4,
            "loss_convention": "Loss is positive magnitude (Loss = -Return). VaR is the loss threshold not exceeded at (1-alpha) confidence.",
            "data_source_mode": data_source_mode,
            "portfolio_value": effective_portfolio_value
        }

        return PortfolioRiskMetrics(
            portfolio_name=portfolio_name,
            currency=currency,
            symbols=symbols,
            weights=[round(float(w), 4) for w in weights],
            portfolio_value=round(effective_portfolio_value, 2) if effective_portfolio_value else None,
            position_values=position_values_dict,
            observations_count=len(returns_df),
            start_date=start_dt,
            end_date=end_dt,
            data_source_mode=data_source_mode,
            annualized_volatility=round(annualized_vol, 4),
            annualization_factor=252,
            historical_var_95=round(hist_var_95, 4),
            historical_var_99=round(hist_var_99, 4),
            parametric_var_95=round(param_var_95, 4),
            parametric_var_99=round(param_var_99, 4),
            expected_shortfall_95=round(es_95, 4),
            expected_shortfall_99=round(es_99, 4),
            historical_var_95_amount=hist_var_95_amt,
            historical_var_99_amount=hist_var_99_amt,
            parametric_var_95_amount=param_var_95_amt,
            parametric_var_99_amount=param_var_99_amt,
            expected_shortfall_95_amount=es_95_amt,
            expected_shortfall_99_amount=es_99_amt,
            maximum_drawdown=round(max_drawdown, 4),
            mean_daily_return=round(mean_ret, 6),
            asset_correlations={
                k: {ik: round(float(iv), 4) for ik, iv in v.items()}
                for k, v in corr_matrix.items()
            },
            loss_convention="Loss is positive magnitude (Loss = -Return)",
            assumptions=assumptions
        )

    def run_stress_test(
        self,
        holdings: list[Holding],
        scenarios: list[StressScenario] | None = None
    ) -> list[StressScenarioResult]:
        """
        Calculates deterministic portfolio losses under historical snapshot worst-case
        or explicitly specified custom shock scenarios.
        No hidden constants or default shock fallbacks.
        """
        # Canonical symbol normalization and duplicate checking
        canonical_map = {h.symbol: normalize_ticker(h.symbol)["canonical_symbol"] for h in holdings}
        symbols = [canonical_map[h.symbol] for h in holdings]
        if len(symbols) != len(set(symbols)):
            dups = [s for s in symbols if symbols.count(s) > 1]
            raise ValueError(f"Duplicate holding symbol detected: '{dups[0]}'. Each holding must be unique.")

        has_pos_values = any(h.position_value is not None for h in holdings)
        has_weights = any(h.weight is not None for h in holdings)
        if has_pos_values and not has_weights:
            pos_vals = [float(h.position_value or 0.0) for h in holdings]
            total_val = sum(pos_vals)
            if total_val <= 0:
                raise ValueError("Sum of position values must be greater than zero.")
            weights = {canonical_map[h.symbol]: float(v) / total_val for h, v in zip(holdings, pos_vals)}
        else:
            weights = {canonical_map[h.symbol]: float(h.weight if h.weight is not None else 0.0) for h in holdings}
            weight_sum = sum(weights.values())
            if abs(weight_sum - 1.0) > 1e-4:
                raise ValueError(f"Holdings weights must sum to 1.0 (got {weight_sum:.6f}, tolerance +/-1e-4).")

        is_derived = scenarios is None
        if scenarios is None:
            # Derive stress shocks from real snapshot observations (worst single-day and max drawdown)
            scenarios = self.derive_historical_stress_scenarios(symbols)

        results = []
        for scen in scenarios:
            asset_losses = {}
            total_loss = 0.0
            norm_shocks = {normalize_ticker(k)["canonical_symbol"]: v for k, v in scen.shocks.items()}
            for sym, weight in weights.items():
                if sym not in norm_shocks and sym not in scen.shocks:
                    raise ValueError(f"Scenario '{scen.name}' missing explicit shock for symbol '{sym}'. Default fallbacks are prohibited.")
                shock = norm_shocks.get(sym, scen.shocks.get(sym))
                loss = shock * weight
                total_loss += loss
                asset_losses[sym] = round(shock, 4)

            assumptions = {
                "scenario_derivation": "historical_snapshot_worst_window" if is_derived else "user_specified",
                "description": scen.description,
                "holding_weights": weights,
                "loss_convention": "One-period linear stress loss approximation"
            }

            results.append(StressScenarioResult(
                scenario_name=scen.name,
                portfolio_loss_pct=round(total_loss, 4),
                individual_asset_losses=asset_losses,
                assumptions=assumptions
            ))

        return results
