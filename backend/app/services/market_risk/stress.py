"""
Named historical stress replays and reverse stress testing.

Replays measure what each holding actually did between two fixed dates, using real prices.
Holdings with no price data in a window are skipped and reported, never filled in.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Protocol

import numpy as np
import pandas as pd

from backend.app.core.config import settings
from backend.app.services.market_risk.engine import CurrencyPolicy, Holding, MarketRiskEngine
from backend.app.services.market_risk.risk import returns as _ret
from backend.app.services.market_risk.ticker_normalizer import get_symbol_currency, normalize_ticker

logger = logging.getLogger(__name__)

FX_SYMBOL = "USDINR=X"


@dataclass(frozen=True)
class ScenarioWindow:
    id: str
    name: str
    description: str
    start: date  # base price = last close on or before this date
    end: date  # end price = last close on or before this date


SCENARIO_WINDOWS: dict[str, ScenarioWindow] = {
    "covid_2020": ScenarioWindow(
        id="covid_2020",
        name="COVID-19 crash (Feb to Mar 2020)",
        description="From the 19 Feb 2020 close, the S&P 500 peak, to the 23 Mar 2020 close, the S&P 500 low. Nifty 50 bottomed one day later.",
        start=date(2020, 2, 19),
        end=date(2020, 3, 23),
    ),
    "election_2024": ScenarioWindow(
        id="election_2024",
        name="Indian election result day (4 Jun 2024)",
        description="The 3 Jun 2024 close to the 4 Jun 2024 close, the day results landed against exit-poll expectations. Nifty 50 fell about 5.9%.",
        start=date(2024, 6, 3),
        end=date(2024, 6, 4),
    ),
    "adani_2023": ScenarioWindow(
        id="adani_2023",
        name="Adani sell-off (Jan to Feb 2023)",
        description="From the 24 Jan 2023 close, just before the Hindenburg report, to the 28 Feb 2023 close.",
        start=date(2023, 1, 24),
        end=date(2023, 2, 28),
    ),
}


class WindowPriceProvider(Protocol):
    """Source of adjusted close prices for a date window. Returns an empty series when there is no data."""

    def fetch(self, symbol: str, start: date, end: date) -> pd.Series: ...

    source_label: str


class YahooWindowProvider:
    """Yahoo Finance adjusted closes for a window, cached on disk so replays are repeatable offline."""

    source_label = "yahoo_finance"

    def __init__(self, cache_dir: Path | None = None, max_retries: int = 3, backoff_factor: float = 1.5):
        self.cache_dir = cache_dir or (settings.DATA_DIR / "stress_windows")
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor

    def _cache_path(self, symbol: str, start: date, end: date) -> Path:
        stem = normalize_ticker(symbol)["file_stem"]
        return self.cache_dir / f"{stem}__{start.isoformat()}__{end.isoformat()}.csv"

    def fetch(self, symbol: str, start: date, end: date) -> pd.Series:
        path = self._cache_path(symbol, start, end)
        if path.exists():
            df = pd.read_csv(path, parse_dates=["date"])
            return pd.Series(df["adj_close"].values, index=pd.DatetimeIndex(df["date"]), dtype=float)

        series = self._download(symbol, start, end)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        # An empty file records "the provider has no data here" so we do not re-ask on every request
        pd.DataFrame({"date": series.index.strftime("%Y-%m-%d"), "adj_close": series.values}).to_csv(path, index=False)
        return series

    def _download(self, symbol: str, start: date, end: date) -> pd.Series:
        import yfinance as yf

        provider_sym = normalize_ticker(symbol)["provider_symbol"]
        last_exc: Exception | None = None
        raw = None
        for attempt in range(self.max_retries):
            try:
                raw = yf.download(
                    provider_sym,
                    start=(start - timedelta(days=10)).isoformat(),
                    end=(end + timedelta(days=2)).isoformat(),
                    auto_adjust=False,
                    progress=False,
                )
                break
            except Exception as exc:  # network or provider failure: retry, then surface
                last_exc = exc
                time.sleep(self.backoff_factor**attempt)
        if raw is None:
            raise ValueError(f"Could not reach the price provider for '{provider_sym}': {last_exc}")
        if raw.empty:
            return _empty_series()

        if isinstance(raw.columns, pd.MultiIndex):
            raw.columns = [str(c[0]).strip().lower() for c in raw.columns]
        else:
            raw.columns = [str(c).strip().lower() for c in raw.columns]
        col = next((c for c in ("adj close", "adj_close", "close") if c in raw.columns), None)
        if col is None:
            return _empty_series()

        idx = pd.DatetimeIndex(raw.index)
        if idx.tz is not None:
            idx = idx.tz_localize(None)
        series = pd.Series(pd.to_numeric(raw[col], errors="coerce").values, index=idx.normalize(), dtype=float).dropna()
        return series[series > 0].sort_index()


def _empty_series() -> pd.Series:
    return pd.Series(dtype=float, index=pd.DatetimeIndex([]))


def _price_on_or_before(series: pd.Series, day: date) -> tuple[pd.Timestamp, float] | None:
    eligible = series.loc[: pd.Timestamp(day)]
    if eligible.empty:
        return None
    return eligible.index[-1], float(eligible.iloc[-1])


def _to_base_currency(
    series: pd.Series, asset_currency: str, base: str, fx: pd.Series | None
) -> pd.Series | None:
    """USD prices times USDINR for an INR base, INR prices divided by it for a USD base."""
    if asset_currency == base:
        return series
    if fx is None or fx.empty:
        return None
    rate = fx.reindex(series.index.union(fx.index)).ffill().reindex(series.index)
    if rate.isna().any():
        return None
    return series * rate if (asset_currency, base) == ("USD", "INR") else series / rate


def beta_model_warning(benchmark_shock: float, holding_shocks: list[float]) -> str | None:
    """A long-only position cannot lose more than 100%, so shocks at or beyond that are not meaningful."""
    if benchmark_shock <= -1.0 or any(x <= -1.0 for x in holding_shocks):
        return (
            "At this loss the beta model implies a fall of 100% or more for the benchmark or a holding, which is not "
            "possible for long-only positions. Read the uniform-shock answer instead."
        )
    return None


class StressService:
    def __init__(self, engine: MarketRiskEngine | None = None, provider: WindowPriceProvider | None = None):
        self.engine = engine or MarketRiskEngine()
        self.provider = provider or YahooWindowProvider()

    # ── shared input handling ───────────────────────────────────────────────────

    def _resolve_weights(self, holdings: list[Holding]) -> tuple[list[str], np.ndarray]:
        symbols = [normalize_ticker(h.symbol)["canonical_symbol"] for h in holdings]
        if len(symbols) != len(set(symbols)):
            dup = next(s for s in symbols if symbols.count(s) > 1)
            raise ValueError(f"Duplicate holding symbol detected: '{dup}'. Each holding must be unique.")

        if any(h.position_value is not None for h in holdings) and not any(h.weight is not None for h in holdings):
            values = np.array([float(h.position_value or 0.0) for h in holdings])
            if values.sum() <= 0 or (values <= 0).any():
                raise ValueError("Position values must be strictly positive.")
            return symbols, values / values.sum()

        weights = np.array([float(h.weight if h.weight is not None else 0.0) for h in holdings])
        if (weights <= 0).any():
            raise ValueError("Holdings weights must be strictly positive.")
        if abs(weights.sum() - 1.0) > 1e-4:
            raise ValueError(f"Holdings weights must sum to 1.0 (got {weights.sum():.6f}, tolerance +/-1e-4).")
        return symbols, weights

    # ── named replays ───────────────────────────────────────────────────────────

    def replay(
        self,
        holdings: list[Holding],
        currency: str | None,
        fx_mode: str = "strict",
        scenario_ids: list[str] | None = None,
        portfolio_value: float | None = None,
    ) -> list[dict[str, Any]]:
        symbols, weights = self._resolve_weights(holdings)
        policy = self.engine.resolve_currency_policy(symbols, currency, fx_mode)

        ids = scenario_ids or list(SCENARIO_WINDOWS)
        unknown = [i for i in ids if i not in SCENARIO_WINDOWS]
        if unknown:
            raise ValueError(f"Unknown scenario id(s) {unknown}. Available: {list(SCENARIO_WINDOWS)}.")

        return [
            self._replay_one(SCENARIO_WINDOWS[i], symbols, weights, policy, portfolio_value) for i in ids
        ]

    def _replay_one(
        self,
        window: ScenarioWindow,
        symbols: list[str],
        weights: np.ndarray,
        policy: CurrencyPolicy,
        portfolio_value: float | None,
    ) -> dict[str, Any]:
        fx: pd.Series | None = None
        if policy.convert:
            fx = self.provider.fetch(FX_SYMBOL, window.start, window.end)

        rows: list[dict[str, Any]] = []
        skipped: list[dict[str, str]] = []

        for sym, weight in zip(symbols, weights, strict=True):
            series = self.provider.fetch(sym, window.start, window.end)
            if series.empty:
                skipped.append({"symbol": sym, "reason": "The price provider has no data for this symbol in the window."})
                continue

            asset_currency = get_symbol_currency(sym)
            converted = _to_base_currency(series, asset_currency, policy.base, fx)
            if converted is None:
                skipped.append({"symbol": sym, "reason": f"No {FX_SYMBOL} rate available to convert {asset_currency} to {policy.base}."})
                continue

            first = _price_on_or_before(converted, window.start)
            last = _price_on_or_before(converted, window.end)
            if first is None:
                listed = converted.index[0].date().isoformat()
                skipped.append({"symbol": sym, "reason": f"No price on or before {window.start}; first available close is {listed}."})
                continue
            assert last is not None  # a close on or before start implies one on or before end

            (d0, p0), (d1, p1) = first, last
            inside = converted.loc[d0:d1]
            rows.append(
                {
                    "symbol": sym,
                    "weight": float(weight),
                    "start_date": d0.date().isoformat(),
                    "end_date": d1.date().isoformat(),
                    "start_price": round(p0, 4),
                    "end_price": round(p1, 4),
                    "return": float(p1 / p0 - 1.0),
                    "trough_return": float(inside.min() / p0 - 1.0),
                }
            )

        covered_weight = float(sum(r["weight"] for r in rows))
        result: dict[str, Any] = {
            "id": window.id,
            "name": window.name,
            "description": window.description,
            "window_start": window.start.isoformat(),
            "window_end": window.end.isoformat(),
            "status": "ok" if rows else "unavailable",
            "currency": policy.base,
            "data_source": self.provider.source_label,
            "covered_weight": round(covered_weight, 6),
            "skipped": skipped,
            "contributions": [],
            "portfolio_return": None,
            "portfolio_loss_pct": None,
            "portfolio_loss_amount": None,
            "fx": {"mode": policy.mode, "base_currency": policy.base, "fx_converted": bool(policy.convert), "fx_pair": FX_SYMBOL if policy.convert else None},
        }
        if not rows:
            return result

        # Weights are renormalised over the holdings that have data, so the loss describes the covered part
        for r in rows:
            r["covered_weight_share"] = r["weight"] / covered_weight
            r["contribution"] = r["covered_weight_share"] * r["return"]
        portfolio_return = float(sum(r["contribution"] for r in rows))
        result["contributions"] = rows
        result["portfolio_return"] = portfolio_return
        result["portfolio_loss_pct"] = round(-portfolio_return, 6)
        if portfolio_value:
            result["portfolio_loss_amount"] = round(-portfolio_return * portfolio_value * covered_weight, 2)
        return result

    # ── reverse stress ──────────────────────────────────────────────────────────

    def reverse(
        self,
        holdings: list[Holding],
        currency: str | None,
        target_loss_pct: float | None = None,
        target_loss_amount: float | None = None,
        portfolio_value: float | None = None,
        fx_mode: str = "strict",
        lookback_days: int = 252,
        benchmark_symbol: str | None = None,
    ) -> dict[str, Any]:
        """
        What uniform market move produces the given portfolio loss?

        Two answers are returned. (1) A uniform fall across every holding: since weights sum to 1 this
        equals the target loss. (2) The benchmark fall that would cause it, scaling each holding by its
        beta to the benchmark over the lookback window: shock = -loss / portfolio_beta.
        """
        if (target_loss_pct is None) == (target_loss_amount is None):
            raise ValueError("Give exactly one of target_loss_pct or target_loss_amount.")
        if target_loss_amount is not None:
            if not portfolio_value or portfolio_value <= 0:
                raise ValueError("portfolio_value is required to convert a target loss amount.")
            target_loss_pct = target_loss_amount / portfolio_value
        assert target_loss_pct is not None
        if not (0.0 < target_loss_pct < 1.0):
            raise ValueError("The target loss must be greater than 0% and less than 100% of the portfolio.")

        symbols, weights = self._resolve_weights(holdings)
        policy = self.engine.resolve_currency_policy(symbols, currency, fx_mode)

        prices, _, fx_info = self.engine.load_prices_with_policy(symbols, policy)
        if lookback_days and len(prices) > lookback_days:
            prices = prices.iloc[-lookback_days:]
        asset_returns = self.engine.calculate_returns(prices, method="simple")

        bench_sym = benchmark_symbol or ("^NSEI" if policy.base == "INR" else "SPY")
        bench_prices = self.engine.load_price_history([bench_sym])
        bench_returns = _ret.simple_returns(bench_prices[bench_sym])
        aligned = asset_returns.join(bench_returns.rename("__bench__"), how="inner").dropna()
        if len(aligned) < 30:
            raise ValueError(f"Only {len(aligned)} days overlap with benchmark {bench_sym}; at least 30 are needed to estimate betas.")

        var_b = float(aligned["__bench__"].var(ddof=1))
        betas = np.array([float(aligned[s].cov(aligned["__bench__"])) / var_b for s in symbols])
        portfolio_beta = float(np.dot(weights, betas))

        loss = float(target_loss_pct)
        uniform_rows = [
            {"symbol": s, "weight": float(w), "beta": float(b), "shock": -loss, "contribution": -loss * float(w)}
            for s, w, b in zip(symbols, weights, betas, strict=True)
        ]

        result: dict[str, Any] = {
            "currency": policy.base,
            "target_loss_pct": round(loss, 6),
            "target_loss_amount": round(loss * portfolio_value, 2) if portfolio_value else None,
            "uniform_asset_shock": round(-loss, 6),
            "uniform_contributions": uniform_rows,
            "benchmark_symbol": bench_sym,
            "lookback_observations": int(len(aligned)),
            "lookback_start": aligned.index[0].date().isoformat(),
            "lookback_end": aligned.index[-1].date().isoformat(),
            "portfolio_beta": round(portfolio_beta, 4),
            "implied_benchmark_shock": None,
            "beta_contributions": [],
            "note": None,
            "fx": {"mode": policy.mode, "base_currency": policy.base, **fx_info},
        }

        if portfolio_beta <= 0:
            result["note"] = (
                f"The portfolio's beta to {bench_sym} is {portfolio_beta:.2f}, so a fall in the benchmark cannot produce "
                "this loss. Only the uniform per-holding shock applies."
            )
            return result

        shock = -loss / portfolio_beta
        result["implied_benchmark_shock"] = round(shock, 6)
        result["beta_contributions"] = [
            {"symbol": s, "weight": float(w), "beta": float(b), "shock": float(b * shock), "contribution": float(w * b * shock)}
            for s, w, b in zip(symbols, weights, betas, strict=True)
        ]
        result["note"] = beta_model_warning(shock, [r["shock"] for r in result["beta_contributions"]])
        return result

