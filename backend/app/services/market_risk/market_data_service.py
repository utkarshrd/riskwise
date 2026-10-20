import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd
from backend.app.services.market_risk.ticker_normalizer import (
    SYMBOL_CATALOGUE,
    normalize_ticker,
)

logger = logging.getLogger(__name__)


class MarketDataService:
    """
    Unified market data service for RiskWise.
    Handles symbol normalization, historical price retrieval, provider response parsing,
    cache/snapshot persistence, and symbol catalogue search.
    """

    def __init__(self, snapshots_dir: Path | None = None, manifest_path: Path | None = None):
        if snapshots_dir is None:
            from backend.app.core.config import settings
            self.snapshots_dir = settings.DATA_DIR / "market_snapshots"
            self.manifest_path = settings.DATA_DIR / "manifests" / "market_manifest.json"
        else:
            self.snapshots_dir = snapshots_dir
            self.manifest_path = manifest_path or (snapshots_dir.parent / "manifests" / "market_manifest.json")

        self.snapshots_dir.mkdir(parents=True, exist_ok=True)

    def _read_cached_file(self, file_path: Path, canonical_symbol: str) -> pd.DataFrame:
        """Reads and validates a local CSV price snapshot."""
        if not file_path.exists():
            raise FileNotFoundError(f"Snapshot file not found: {file_path}")

        df = pd.read_csv(file_path)
        date_col = next((c for c in df.columns if c.lower() == "date"), None)
        if not date_col:
            raise ValueError(f"Snapshot for '{canonical_symbol}' missing 'date' column.")

        price_col = next((c for c in df.columns if c.lower() in ["adj_close", "adj close"]), None)
        if not price_col:
            raise ValueError(f"Snapshot for '{canonical_symbol}' missing required dividend/split adjusted column 'adj_close'.")

        # Parse date and sort
        df[date_col] = pd.to_datetime(df[date_col])
        df = df.sort_values(date_col).drop_duplicates(subset=[date_col])

        # Validate prices
        prices = pd.to_numeric(df[price_col], errors="coerce").dropna()
        if (prices <= 0).any() or len(prices) == 0:
            raise ValueError(f"Non-positive price detected in snapshot for '{canonical_symbol}'.")

        result_df = pd.DataFrame({
            "Date": df[date_col],
            "adj_close": prices
        }).dropna().sort_values("Date")
        return result_df

    def fetch_live_price_history(self, symbol: str, period: str = "2y") -> pd.DataFrame:
        """
        Retrieves historical market data from yfinance provider.
        Parses MultiIndex columns, validates non-empty responses, verifies strictly positive prices,
        saves validated adjusted prices to local snapshot cache, and updates manifest.
        """
        import hashlib

        import yfinance as yf

        norm = normalize_ticker(symbol)
        provider_sym = norm["provider_symbol"]
        canonical_sym = norm["canonical_symbol"]
        file_stem = norm["file_stem"]

        try:
            raw_df = yf.download(provider_sym, period=period, auto_adjust=False, progress=False)
        except Exception as exc:
            raise RuntimeError(f"Provider connection error for '{provider_sym}': {exc}") from exc

        if raw_df is None or raw_df.empty:
            raise ValueError(f"Provider returned empty price history for '{provider_sym}'. Check symbol validity.")

        # Flatten columns if MultiIndex
        if isinstance(raw_df.columns, pd.MultiIndex):
            col_names = [str(c[0]).strip().lower() for c in raw_df.columns]
            raw_df.columns = col_names
        else:
            raw_df.columns = [str(c).strip().lower() for c in raw_df.columns]

        # Prioritize dividend/split-adjusted close
        adj_close_col = next((c for c in ["adj close", "adj_close"] if c in raw_df.columns), None)
        close_col = next((c for c in ["close"] if c in raw_df.columns), adj_close_col)
        vol_col = next((c for c in ["volume"] if c in raw_df.columns), None)

        if not adj_close_col:
            raise ValueError(f"Provider response for '{provider_sym}' missing required dividend/split adjusted column 'adj_close'.")

        # Date handling from index
        if "date" in raw_df.columns:
            dates = pd.to_datetime(raw_df["date"])
            if hasattr(dates.dt, "tz") and dates.dt.tz is not None:
                dates = dates.dt.tz_localize(None)
        else:
            dates = pd.to_datetime(raw_df.index)
            if hasattr(dates, "tz") and dates.tz is not None:
                dates = dates.tz_localize(None)

        date_strings = dates.dt.strftime("%Y-%m-%d") if hasattr(dates, "dt") else [str(d)[:10] for d in dates]
        adj_prices = pd.to_numeric(raw_df[adj_close_col], errors="coerce")
        raw_prices = pd.to_numeric(raw_df[close_col], errors="coerce") if close_col else adj_prices
        volumes = pd.to_numeric(raw_df[vol_col], errors="coerce").fillna(0) if vol_col else [0] * len(adj_prices)

        clean_df = pd.DataFrame({
            "date": date_strings,
            "close": raw_prices.values,
            "adj_close": adj_prices.values,
            "volume": volumes.values
        }).dropna()
        clean_df = clean_df.reset_index(drop=True)
        clean_df = clean_df[clean_df["adj_close"] > 0]
        clean_df = clean_df.sort_values("date").drop_duplicates(subset=["date"])

        # Validate strictly positive prices
        if (clean_df["adj_close"] <= 0).any() or len(clean_df) < 10:
            raise ValueError(f"Provider returned invalid or non-positive price values for '{provider_sym}'.")

        # Save to snapshot cache
        target_path = self.snapshots_dir / f"{file_stem}.csv"
        clean_df.to_csv(target_path, index=False)

        # Update market manifest if present
        if self.manifest_path and self.manifest_path.exists():
            try:
                with open(target_path, "rb") as bf:
                    checksum = hashlib.sha256(bf.read()).hexdigest()
                with open(self.manifest_path, "r", encoding="utf-8") as mf:
                    manifest_data = json.load(mf)
                if "snapshots" not in manifest_data:
                    manifest_data["snapshots"] = {}
                rel_path = f"data\\market_snapshots\\{file_stem}.csv"
                manifest_data["snapshots"][canonical_sym] = {
                    "symbol": canonical_sym,
                    "provider_symbol": provider_sym,
                    "name": SYMBOL_CATALOGUE.get(canonical_sym, {}).get("name", canonical_sym),
                    "currency": norm["currency"],
                    "start_date": str(clean_df["date"].min()),
                    "end_date": str(clean_df["date"].max()),
                    "observations": len(clean_df),
                    "nan_sessions_dropped": 0,
                    "anomalies_flagged": [],
                    "file_path": rel_path,
                    "checksum": checksum,
                }
                if canonical_sym not in manifest_data.get("symbols", []):
                    manifest_data.setdefault("symbols", []).append(canonical_sym)
                with open(self.manifest_path, "w", encoding="utf-8") as mf:
                    json.dump(manifest_data, mf, indent=2)
            except (OSError, json.JSONDecodeError, ValueError) as e:
                logger.warning("Could not update market_manifest.json: %s", e)

        logger.info("Successfully fetched and cached live data for %s at %s", canonical_sym, target_path)

        return clean_df.rename(columns={"date": "Date"})

    def get_symbol_price_history(
        self,
        symbol: str,
        allow_live: bool = True
    ) -> tuple[pd.DataFrame, str]:
        """
        Retrieves price history for a single symbol.
        Checks cache first, then attempts live download if permitted and needed.
        Returns (DataFrame with ['Date', 'adj_close'], source_mode).
        """
        norm = normalize_ticker(symbol)
        canonical_sym = norm["canonical_symbol"]
        file_stem = norm["file_stem"]

        candidate_paths = [
            self.snapshots_dir / f"{file_stem}.csv",
            self.snapshots_dir / f"{canonical_sym}.csv",
            self.snapshots_dir / f"{canonical_sym.replace('^', '_')}.csv",
        ]
        existing_path = next((p for p in candidate_paths if p.exists()), None)

        if existing_path:
            try:
                cached_df = self._read_cached_file(existing_path, canonical_sym)
                if len(cached_df) >= 30:
                    return cached_df, "offline_snapshot"
            except (OSError, ValueError, KeyError) as e:
                logger.warning("Cached snapshot for %s invalid (%s); will attempt live refresh.", canonical_sym, e)

        # If not cached or snapshot was invalid, attempt live download
        if allow_live:
            try:
                live_df = self.fetch_live_price_history(symbol, period="2y")
                return live_df, "live_download"
            except Exception as exc:
                if existing_path:
                    logger.warning("Live download failed (%s), using existing snapshot for %s", exc, canonical_sym)
                    return self._read_cached_file(existing_path, canonical_sym), "offline_snapshot"
                raise FileNotFoundError(
                    f"Symbol '{symbol}' not found in local market snapshots and live retrieval failed ({exc}). "
                    f"Ensure the ticker is valid on Yahoo Finance (e.g., '.NS' for NSE equities)."
                ) from exc

        if existing_path:
            return self._read_cached_file(existing_path, canonical_sym), "offline_snapshot"

        raise FileNotFoundError(
            f"Market snapshot for symbol '{symbol}' not found in {self.snapshots_dir} and live retrieval is disabled."
        )

    def load_aligned_prices(
        self,
        symbols: list[str],
        allow_live: bool = True
    ) -> tuple[pd.DataFrame, str, dict[str, str]]:
        """
        Loads aligned daily price history for requested symbols.
        Strictly enforces:
        1. Single-currency uniformity across all assets.
        2. Strictly positive prices.
        3. Common overlapping dates (minimum 30 observations).
        Returns:
            aligned_prices_df: index=Date, columns=canonical_symbols
            data_source_mode: 'offline_snapshot' or 'live_download'
            currencies_map: {canonical_symbol: currency}
        """
        dfs = []
        currencies = {}
        sources = []

        canonical_symbols = []
        for raw_sym in symbols:
            norm = normalize_ticker(raw_sym)
            can_sym = norm["canonical_symbol"]
            curr = norm["currency"]
            canonical_symbols.append(can_sym)
            currencies[can_sym] = curr

            df, source = self.get_symbol_price_history(raw_sym, allow_live=allow_live)
            df = df.set_index("Date")[["adj_close"]].rename(columns={"adj_close": can_sym})
            dfs.append(df)
            sources.append(source)

        # Enforce single currency
        distinct_currencies = set(currencies.values())
        if len(distinct_currencies) > 1:
            raise ValueError(
                f"Mixed-currency portfolio detected: {currencies}. "
                "Portfolios must be strictly single-currency (all USD or all INR). "
                "Silent FX conversion is prohibited."
            )

        # Inner join across common trading dates
        aligned = dfs[0]
        for next_df in dfs[1:]:
            aligned = aligned.join(next_df, how="inner")

        aligned = aligned.dropna().sort_index()
        if len(aligned) < 30:
            raise ValueError(
                f"Insufficient common trading dates for portfolio {canonical_symbols}. "
                f"Found only {len(aligned)} aligned trading sessions; minimum required is 30."
            )

        overall_source = "live_download" if any(s == "live_download" for s in sources) else "offline_snapshot"
        return aligned, overall_source, currencies

    def validate_symbol(self, symbol: str, target_currency: str | None = None) -> dict[str, Any]:
        """
        Validates a candidate stock symbol and determines its exact availability state:
        1. 'verified_snapshot': A validated local CSV price snapshot already exists on disk.
        2. 'live_validated': Outside local snapshot catalogue, but successfully fetched, validated,
                             and cached from the live provider with sufficient history.
        3. 'not_available': Quote not found on exchange/provider, symbol delisted, insufficient
                            history (< 30 observations), or provider failure.
        """
        from backend.app.services.market_risk.ticker_normalizer import CORPORATE_ALIASES

        try:
            norm = normalize_ticker(symbol, currency_hint=target_currency)
        except ValueError as e:
            return {
                "symbol": symbol,
                "canonical_symbol": symbol,
                "name": symbol,
                "exchange": "UNKNOWN",
                "currency": target_currency or "USD",
                "state": "not_available",
                "is_cached": False,
                "error_reason": "invalid_symbol_format",
                "message": str(e),
            }

        canonical_sym = norm["canonical_symbol"]
        file_stem = norm["file_stem"]
        currency = norm["currency"]
        exchange = norm["exchange"]

        name = SYMBOL_CATALOGUE.get(canonical_sym, {}).get("name", canonical_sym)
        alias_note = None
        upper_raw = symbol.upper().strip()
        if upper_raw in CORPORATE_ALIASES:
            alias_note = CORPORATE_ALIASES[upper_raw]["note"]

        # State 1: Check existing local cached snapshot
        csv_path = self.snapshots_dir / f"{file_stem}.csv"
        if csv_path.exists():
            try:
                df = self._read_cached_file(csv_path, canonical_sym)
                return {
                    "symbol": canonical_sym,
                    "canonical_symbol": canonical_sym,
                    "name": name,
                    "exchange": exchange,
                    "currency": currency,
                    "state": "verified_snapshot",
                    "is_cached": True,
                    "observations_count": len(df),
                    "start_date": str(df["Date"].min()),
                    "end_date": str(df["Date"].max()),
                    "alias_note": alias_note,
                    "message": f"Verified snapshot available ({len(df)} validated observations).",
                }
            except (OSError, ValueError, KeyError, RuntimeError) as e:
                logger.warning("Existing snapshot for %s invalid: %s. Attempting live fetch.", canonical_sym, e)

        # State 2: Fetch on demand from live provider
        try:
            df = self.fetch_live_price_history(canonical_sym, period="2y")
            if len(df) < 30:
                return {
                    "symbol": canonical_sym,
                    "canonical_symbol": canonical_sym,
                    "name": name,
                    "exchange": exchange,
                    "currency": currency,
                    "state": "not_available",
                    "is_cached": False,
                    "error_reason": "insufficient_history",
                    "observations_count": len(df),
                    "message": f"Symbol '{canonical_sym}' has only {len(df)} trading observations (minimum required: 30).",
                }
            return {
                "symbol": canonical_sym,
                "canonical_symbol": canonical_sym,
                "name": name,
                "exchange": exchange,
                "currency": currency,
                "state": "live_validated",
                "is_cached": True,
                "observations_count": len(df),
                "start_date": str(df["Date"].min()),
                "end_date": str(df["Date"].max()),
                "alias_note": alias_note,
                "message": f"Live data validated: retrieved {len(df)} historical observations from provider.",
            }
        except (OSError, ValueError, KeyError, RuntimeError) as exc:
            err_msg = str(exc)
            if "not found" in err_msg.lower() or "delisted" in err_msg.lower() or "404" in err_msg:
                reason = "quote_not_found"
                msg = f"Symbol '{canonical_sym}' was not found on exchange ({exchange}) or may be delisted."
            elif "insufficient" in err_msg.lower():
                reason = "insufficient_history"
                msg = f"Symbol '{canonical_sym}' has insufficient trading history."
            else:
                reason = "provider_error"
                msg = f"Provider request failed: {err_msg}"

            return {
                "symbol": canonical_sym,
                "canonical_symbol": canonical_sym,
                "name": name,
                "exchange": exchange,
                "currency": currency,
                "state": "not_available",
                "is_cached": False,
                "error_reason": reason,
                "alias_note": alias_note,
                "message": msg,
            }

    def search_symbols(
        self, query: str, limit: int = 15, currency_hint: str | None = None
    ) -> list[dict[str, Any]]:
        """
        Dual-layer stock search:
        Layer 1: Local curated catalogue of NSE and US blue-chips + corporate aliases.
        Layer 2: Live provider search via yfinance for broad symbol discovery.
        """
        from backend.app.services.market_risk.ticker_normalizer import CORPORATE_ALIASES

        q = (query or "").strip()
        q_upper = q.upper()

        results: list[dict[str, Any]] = []
        seen_symbols: set[str] = set()

        # Check existing snapshot files
        cached_stems = set()
        if self.snapshots_dir.exists():
            for f in self.snapshots_dir.glob("*.csv"):
                if f.stem != "market_snapshot":
                    cached_stems.add(f.stem)

        # 0. Check corporate aliases first (e.g. 'ZOMATO' -> 'ETERNAL.NS')
        for alias_key, alias_info in CORPORATE_ALIASES.items():
            if q_upper in alias_key or q_upper in alias_info["note"].upper():
                target_sym = alias_info["target"]
                if target_sym not in seen_symbols:
                    meta = SYMBOL_CATALOGUE.get(target_sym, {})
                    file_stem = meta.get("file_stem", target_sym.replace("^", "_"))
                    is_cached = file_stem in cached_stems or target_sym in cached_stems
                    results.append({
                        "symbol": target_sym,
                        "name": meta.get("name", target_sym),
                        "exchange": meta.get("exchange", "NSE"),
                        "currency": meta.get("currency", "INR"),
                        "is_cached": is_cached,
                        "status": "verified" if is_cached else "known",
                        "alias_of": alias_key,
                        "note": alias_info["note"],
                    })
                    seen_symbols.add(target_sym)

        # 1. Match against local catalogue
        for sym_key, meta in SYMBOL_CATALOGUE.items():
            sym_upper = sym_key.upper()
            name_upper = meta["name"].upper()
            if not q or q_upper in sym_upper or q_upper in name_upper:
                if meta["symbol"] in seen_symbols:
                    continue
                file_stem = meta.get("file_stem", sym_key.replace("^", "_"))
                is_cached = file_stem in cached_stems or sym_key in cached_stems
                results.append({
                    "symbol": meta["symbol"],
                    "name": meta["name"],
                    "exchange": meta["exchange"],
                    "currency": meta["currency"],
                    "is_cached": is_cached,
                    "status": "verified" if is_cached else "known",
                })
                seen_symbols.add(meta["symbol"])

        # 2. Synthesize candidate NSE symbol if user query looks like a ticker and currency is INR
        if q_upper and len(q_upper) >= 2 and not q_upper.endswith(".NS") and not q_upper.endswith(".BO"):
            candidate_ns = f"{q_upper}.NS"
            if candidate_ns not in seen_symbols:
                is_cached = candidate_ns in cached_stems
                results.append({
                    "symbol": candidate_ns,
                    "name": f"{q_upper} (NSE Equity)",
                    "exchange": "NSE",
                    "currency": "INR",
                    "is_cached": is_cached,
                    "status": "verified" if is_cached else "valid_remote",
                })
                seen_symbols.add(candidate_ns)

        # 3. Live yfinance search if query is specific and results under limit
        if len(q) >= 2 and len(results) < limit:
            try:
                import yfinance as yf
                yf_search = yf.Search(q, max_results=limit)
                if yf_search and hasattr(yf_search, "quotes") and yf_search.quotes:
                    for quote in yf_search.quotes:
                        raw_s = quote.get("symbol")
                        if not raw_s or raw_s in seen_symbols:
                            continue

                        exch = str(quote.get("exchange", "")).upper()
                        short_name = quote.get("shortname") or quote.get("longname") or raw_s

                        try:
                            norm = normalize_ticker(raw_s, currency_hint=currency_hint)
                            can_sym = norm["canonical_symbol"]
                            if can_sym in seen_symbols:
                                continue

                            is_cached = norm["file_stem"] in cached_stems or can_sym in cached_stems
                            results.append({
                                "symbol": can_sym,
                                "name": short_name,
                                "exchange": norm["exchange"] if norm["exchange"] != "US" else exch,
                                "currency": norm["currency"],
                                "is_cached": is_cached,
                                "status": "verified" if is_cached else "valid_remote",
                            })
                            seen_symbols.add(can_sym)
                        except (ValueError, KeyError) as err:
                            logger.debug("Skipping invalid quote %s: %s", raw_s, err)
                            continue
            except (OSError, RuntimeError, ValueError) as e:
                logger.debug("Live symbol search encountered exception: %s", e)

        return results[:limit]

    def refresh_symbols(self, target_symbols: list[str] | None = None) -> dict[str, Any]:
        """
        Refreshes market data snapshots.
        Validates downloaded data before updating cache.
        Never replaces good cached data with empty failed responses.
        """
        refreshed: list[str] = []
        errors: dict[str, str] = {}

        # If no symbols specified, refresh all known symbols in snapshots dir + core presets
        if not target_symbols:
            symbols_to_refresh = set()
            if self.snapshots_dir.exists():
                for f in self.snapshots_dir.glob("*.csv"):
                    if f.stem != "market_snapshot":
                        # Convert stem to ticker if _NSEI
                        sym = "^NSEI" if f.stem == "_NSEI" else f.stem
                        symbols_to_refresh.add(sym)
            # Add core symbols
            symbols_to_refresh.update([
                "SPY", "AAPL", "MSFT", "GOOGL",
                "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "ICICIBANK.NS", "NIFTYBEES.NS", "^NSEI"
            ])
            symbols_list = sorted(symbols_to_refresh)
        else:
            symbols_list = [normalize_ticker(s)["canonical_symbol"] for s in target_symbols]

        for s in symbols_list:
            try:
                self.fetch_live_price_history(s, period="2y")
                refreshed.append(s)
            except (OSError, RuntimeError, ValueError) as e:
                errors[s] = str(e)
                logger.warning("Failed refreshing symbol %s: %s", s, e)

        # Audit snapshots
        snapshot_counts = {}
        if self.snapshots_dir.exists():
            for f in self.snapshots_dir.glob("*.csv"):
                if f.stem != "market_snapshot":
                    try:
                        df = pd.read_csv(f)
                        date_col = next((c for c in df.columns if c.lower() == "date"), None)
                        snapshot_counts[f.stem] = {
                            "row_count": len(df),
                            "start_date": str(df[date_col].min()) if date_col and not df.empty else None,
                            "end_date": str(df[date_col].max()) if date_col and not df.empty else None,
                        }
                    except (OSError, ValueError, KeyError) as err:
                        snapshot_counts[f.stem] = {"error": str(err)}

        return {
            "status": "ok" if refreshed else ("partial_errors" if snapshot_counts else "failed"),
            "refreshed_symbols": refreshed,
            "errors": errors,
            "data_source_mode": "live_refreshed" if refreshed else "offline_snapshot",
            "snapshot_details": snapshot_counts,
            "supported_symbols": sorted(snapshot_counts.keys()),
            "refreshed_at": datetime.now(UTC).isoformat(),
        }
