import hashlib
import json
import logging
import math
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd
from sqlalchemy import or_

from backend.app.core.config import settings
from backend.app.db.models import DailyPrice, Instrument
from backend.app.db.session import SessionLocal
from backend.app.services.market_risk.ticker_normalizer import (
    CORPORATE_ALIASES,
    SYMBOL_CATALOGUE,
    get_symbol_currency,
    normalize_ticker,
)

logger = logging.getLogger(__name__)


class MarketDataService:
    """
    Unified market data service for RiskWise.
    Handles symbol normalization, database-backed instruments search,
    lazy cached price retrieval (SQLite daily_prices + CSV snapshots),
    threaded live download with retry/backoff, and USD/INR FX conversion.
    """

    def __init__(self, snapshots_dir: Path | None = None, manifest_path: Path | None = None):
        if snapshots_dir is None:
            self.snapshots_dir = settings.DATA_DIR / "market_snapshots"
            self.manifest_path = settings.DATA_DIR / "manifests" / "market_manifest.json"
            self._is_default_snapshots_dir = True
        else:
            self.snapshots_dir = snapshots_dir
            self.manifest_path = manifest_path or (snapshots_dir.parent / "manifests" / "market_manifest.json")
            self._is_default_snapshots_dir = False

        self.snapshots_dir.mkdir(parents=True, exist_ok=True)

    def _read_cached_db(self, canonical_symbol: str) -> pd.DataFrame | None:
        """Reads validated daily prices from SQLite daily_prices table."""
        try:
            db = SessionLocal()
            try:
                rows = (
                    db.query(DailyPrice.date, DailyPrice.adj_close)
                    .filter(DailyPrice.symbol == canonical_symbol)
                    .order_by(DailyPrice.date.asc())
                    .all()
                )
                if len(rows) >= 30:
                    df = pd.DataFrame(rows, columns=["Date", "adj_close"])
                    df["Date"] = pd.to_datetime(df["Date"])
                    df["adj_close"] = pd.to_numeric(df["adj_close"], errors="coerce")
                    df = df.dropna().sort_values("Date").drop_duplicates(subset=["Date"])
                    if (df["adj_close"] > 0).all() and len(df) >= 30:
                        return df
            finally:
                db.close()
        except Exception as e:
            logger.debug("Database price lookup failed for %s: %s", canonical_symbol, e)
        return None

    def _save_prices_to_db(self, canonical_symbol: str, df: pd.DataFrame) -> int:
        """Saves price history DataFrame into SQLite daily_prices table."""
        saved_count = 0
        try:
            db = SessionLocal()
            try:
                date_col = next((c for c in df.columns if c.lower() == "date"), None)
                adj_col = next((c for c in df.columns if c.lower() in ["adj_close", "adj close"]), None)
                if not date_col or not adj_col:
                    return 0

                for _, row in df.iterrows():
                    d_str = str(row[date_col])[:10].strip()
                    val = float(row[adj_col])
                    if val <= 0 or math.isnan(val):
                        continue

                    open_val = float(row["open"]) if "open" in df.columns and pd.notna(row["open"]) else None
                    high_val = float(row["high"]) if "high" in df.columns and pd.notna(row["high"]) else None
                    low_val = float(row["low"]) if "low" in df.columns and pd.notna(row["low"]) else None
                    close_val = float(row["close"]) if "close" in df.columns and pd.notna(row["close"]) else None
                    vol_val = float(row["volume"]) if "volume" in df.columns and pd.notna(row["volume"]) else None

                    existing = (
                        db.query(DailyPrice.id)
                        .filter(DailyPrice.symbol == canonical_symbol, DailyPrice.date == d_str)
                        .first()
                    )
                    if not existing:
                        db.add(
                            DailyPrice(
                                symbol=canonical_symbol,
                                date=d_str,
                                open=open_val,
                                high=high_val,
                                low=low_val,
                                close=close_val,
                                adj_close=val,
                                volume=vol_val,
                            )
                        )
                        saved_count += 1
                db.commit()
            finally:
                db.close()
        except Exception as e:
            logger.warning("Could not persist daily prices to DB for %s: %s", canonical_symbol, e)
        return saved_count

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
            raise ValueError(
                f"Snapshot for '{canonical_symbol}' missing required dividend/split adjusted column 'adj_close'."
            )

        df[date_col] = pd.to_datetime(df[date_col])
        df = df.sort_values(date_col).drop_duplicates(subset=[date_col])

        prices = pd.to_numeric(df[price_col], errors="coerce").dropna()
        if (prices <= 0).any() or len(prices) == 0:
            raise ValueError(f"Non-positive price detected in snapshot for '{canonical_symbol}'.")

        result_df = pd.DataFrame({"Date": df[date_col], "adj_close": prices}).dropna().sort_values("Date")
        return result_df

    def fetch_live_price_history(
        self, symbol: str, period: str = "2y", max_retries: int = 3, backoff_factor: float = 1.5
    ) -> pd.DataFrame:
        """
        Retrieves historical market data from yfinance provider with exponential backoff retry.
        Parses MultiIndex columns, validates non-empty responses, verifies strictly positive prices,
        saves validated adjusted prices to local snapshot cache, and updates manifest and DB.
        """
        import yfinance as yf

        norm = normalize_ticker(symbol)
        provider_sym = norm["provider_symbol"]
        canonical_sym = norm["canonical_symbol"]
        file_stem = norm["file_stem"]

        raw_df = None
        last_exc = None

        for attempt in range(max_retries):
            try:
                raw_df = yf.download(provider_sym, period=period, auto_adjust=False, progress=False)
                if raw_df is not None and not raw_df.empty:
                    break
            except Exception as exc:
                last_exc = exc
                sleep_sec = backoff_factor**attempt
                logger.info(
                    "Retry %d/%d for '%s' after error: %s (sleeping %.1fs)",
                    attempt + 1,
                    max_retries,
                    provider_sym,
                    exc,
                    sleep_sec,
                )
                time.sleep(sleep_sec)

        if raw_df is None or raw_df.empty:
            err_msg = f"Provider returned empty price history for '{provider_sym}'."
            if last_exc:
                err_msg += f" Error: {last_exc}"
            raise ValueError(err_msg)

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
        open_col = next((c for c in ["open"] if c in raw_df.columns), None)
        high_col = next((c for c in ["high"] if c in raw_df.columns), None)
        low_col = next((c for c in ["low"] if c in raw_df.columns), None)

        if not adj_close_col:
            raise ValueError(
                f"Provider response for '{provider_sym}' missing required dividend/split adjusted column 'adj_close'."
            )

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
        volumes = (
            pd.to_numeric(raw_df[vol_col], errors="coerce").fillna(0)
            if vol_col
            else pd.Series(0, index=adj_prices.index)
        )

        clean_dict: dict[str, Any] = {
            "date": date_strings,
            "close": raw_prices.values,
            "adj_close": adj_prices.values,
            "volume": volumes.values,
        }
        if open_col:
            clean_dict["open"] = pd.to_numeric(raw_df[open_col], errors="coerce").values
        if high_col:
            clean_dict["high"] = pd.to_numeric(raw_df[high_col], errors="coerce").values
        if low_col:
            clean_dict["low"] = pd.to_numeric(raw_df[low_col], errors="coerce").values

        clean_df = pd.DataFrame(clean_dict).dropna(subset=["date", "adj_close"])
        clean_df = clean_df.reset_index(drop=True)
        clean_df = clean_df[clean_df["adj_close"] > 0]
        clean_df = clean_df.sort_values("date").drop_duplicates(subset=["date"])

        if (clean_df["adj_close"] <= 0).any() or len(clean_df) < 10:
            raise ValueError(f"Provider returned invalid or non-positive price values for '{provider_sym}'.")

        # Gap and staleness validation
        dates_dt = pd.to_datetime(clean_df["date"]).sort_values()
        diffs = dates_dt.diff().dt.days
        max_gap = int(diffs.max()) if len(diffs) > 1 and pd.notna(diffs.max()) else 0
        anomalies: list[str] = []
        if max_gap > 45:
            raise ValueError(
                f"Excessive price gap detected for '{provider_sym}': {max_gap} calendar days between trading observations exceeds 45-day threshold."
            )
        elif max_gap > 14:
            anomalies.append(f"Trading gap: {max_gap} calendar days")

        latest_date = dates_dt.max()
        days_stale = (pd.Timestamp.now().normalize() - latest_date.normalize()).days
        if days_stale > 180:
            anomalies.append(f"Stale price data: {days_stale} calendar days since latest observation {latest_date.date()}")
        freshness_status = "stale" if days_stale > 30 else "fresh"

        # 1. Save to CSV snapshot
        target_path = self.snapshots_dir / f"{file_stem}.csv"
        clean_df.to_csv(target_path, index=False)

        # 2. Save to SQLite DB
        self._save_prices_to_db(canonical_sym, clean_df)

        # 3. Update Instrument record freshness in DB
        try:
            db_inst = SessionLocal()
            inst_obj = db_inst.query(Instrument).filter(Instrument.symbol == canonical_sym).first()
            if inst_obj:
                inst_obj.updated_at = datetime.now(UTC)
                db_inst.commit()
            db_inst.close()
        except Exception as e:
            logger.warning("Could not update Instrument freshness in DB for %s: %s", canonical_sym, e)

        # 4. Update market manifest with freshness and anomaly metrics
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
                    "anomalies_flagged": anomalies,
                    "max_gap_days": max_gap,
                    "freshness_status": freshness_status,
                    "last_sync_timestamp": datetime.now(UTC).isoformat(),
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
        out_df = clean_df.rename(columns={"date": "Date"})
        out_df["Date"] = pd.to_datetime(out_df["Date"])
        return out_df[["Date", "adj_close"]]

    def get_symbol_price_history(
        self, symbol: str, allow_live: bool = True
    ) -> tuple[pd.DataFrame, str]:
        """
        Retrieves price history for a single symbol.
        Order of precedence:
        1. Local CSV snapshot on disk (respects snapshots_dir override for test isolation).
        2. SQLite daily_prices table (fast indexed query for production).
        3. Live yfinance download with retry/backoff if permitted.
        Returns (DataFrame with ['Date', 'adj_close'], source_mode).
        """
        norm = normalize_ticker(symbol)
        canonical_sym = norm["canonical_symbol"]
        file_stem = norm["file_stem"]

        # 1. Check local CSV snapshot first (preserves snapshots_dir isolation in tests)
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
                    # Backfill to DB for future fast lookups
                    self._save_prices_to_db(canonical_sym, cached_df)
                    return cached_df, "offline_snapshot"
            except (OSError, ValueError, KeyError) as e:
                logger.warning(
                    "Cached snapshot for %s invalid (%s); will attempt DB or live refresh.",
                    canonical_sym,
                    e,
                )

        # 2. Check SQLite DB (production fast path when using default production directory and no local CSV)
        if self._is_default_snapshots_dir:
            db_df = self._read_cached_db(canonical_sym)
            if db_df is not None and len(db_df) >= 30:
                return db_df, "offline_snapshot"

        # 3. Live fetch via yfinance
        if allow_live:
            try:
                live_df = self.fetch_live_price_history(symbol, period="2y")
                return live_df, "live_download"
            except Exception as exc:
                if existing_path:
                    logger.warning(
                        "Live download failed (%s), using existing snapshot for %s",
                        exc,
                        canonical_sym,
                    )
                    return self._read_cached_file(existing_path, canonical_sym), "offline_snapshot"
                raise FileNotFoundError(
                    f"Symbol '{symbol}' not found in local market snapshots or database, "
                    f"and live retrieval failed ({exc})."
                ) from exc

        if existing_path:
            return self._read_cached_file(existing_path, canonical_sym), "offline_snapshot"

        raise FileNotFoundError(
            f"Market snapshot for symbol '{symbol}' not found in database or {self.snapshots_dir} and live retrieval is disabled."
        )

    def load_aligned_prices(
        self,
        symbols: list[str],
        allow_live: bool = True,
        fx_conversion: bool = False,
        base_currency: str | None = None,
    ) -> tuple[pd.DataFrame, str, dict[str, str], dict[str, Any]]:
        """
        Loads aligned daily price history for requested symbols.
        Supports:
        1. Single-currency uniformity by default (strict rejection of mixed currency).
        2. Explicit opt-in FX conversion mode (fx_conversion=True) using USD/INR series (USDINR=X).
        Returns:
            aligned_prices_df: index=Date, columns=canonical_symbols
            data_source_mode: 'offline_snapshot' or 'live_download'
            currencies_map: {canonical_symbol: currency}
            fx_info: dict detailing FX conversion assumption and pairs
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

        distinct_currencies = set(currencies.values())
        fx_info: dict[str, Any] = {"fx_converted": False}

        # Check currency uniformity
        if len(distinct_currencies) > 1:
            if not fx_conversion:
                raise ValueError(
                    f"Mixed-currency portfolio detected: {currencies}. "
                    "Portfolios must be strictly single-currency (all USD or all INR). "
                    "Silent FX conversion is prohibited. Set fx_conversion=True to opt into explicit base-currency conversion."
                )

            # Explicit FX conversion mode
            target_curr = (base_currency or "INR").upper()
            fx_df, fx_source = self.get_symbol_price_history("USDINR=X", allow_live=allow_live)
            fx_series = fx_df.set_index("Date")["adj_close"]
            sources.append(fx_source)

            converted_symbols = []
            for i, can_sym in enumerate(canonical_symbols):
                asset_curr = currencies[can_sym]
                if asset_curr != target_curr:
                    aligned_asset = dfs[i].join(fx_series.rename("fx_rate"), how="inner").dropna()
                    if asset_curr == "USD" and target_curr == "INR":
                        # USD to INR: multiply by USD/INR rate
                        aligned_asset[can_sym] = aligned_asset[can_sym] * aligned_asset["fx_rate"]
                    elif asset_curr == "INR" and target_curr == "USD":
                        # INR to USD: divide by USD/INR rate
                        aligned_asset[can_sym] = aligned_asset[can_sym] / aligned_asset["fx_rate"]
                    dfs[i] = aligned_asset[[can_sym]]
                    currencies[can_sym] = target_curr
                    converted_symbols.append(can_sym)

            fx_info = {
                "fx_converted": True,
                "base_currency": target_curr,
                "fx_pair": "USDINR=X",
                "converted_symbols": converted_symbols,
                "note": (
                    f"Converted {len(converted_symbols)} asset(s) ({converted_symbols}) into {target_curr} "
                    f"using historical daily USD/INR exchange rates from USDINR=X."
                ),
            }

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
        return aligned, overall_source, currencies, fx_info

    def validate_symbol(self, symbol: str, target_currency: str | None = None) -> dict[str, Any]:
        """Validates symbol availability and status."""
        norm = normalize_ticker(symbol, currency_hint=target_currency)
        can_sym = norm["canonical_symbol"]
        prov_sym = norm["provider_symbol"]
        exchange = norm["exchange"]
        currency = norm["currency"]
        file_stem = norm["file_stem"]

        # Check DB or CSV
        db_df = self._read_cached_db(can_sym)
        if db_df is not None and len(db_df) >= 30:
            return {
                "symbol": symbol,
                "canonical_symbol": can_sym,
                "name": SYMBOL_CATALOGUE.get(can_sym, {}).get("name", can_sym),
                "exchange": exchange,
                "currency": currency,
                "state": "verified_snapshot",
                "is_cached": True,
                "observations_count": len(db_df),
                "start_date": str(db_df["Date"].min().date()),
                "end_date": str(db_df["Date"].max().date()),
                "message": f"Symbol '{can_sym}' is verified and cached in database ({len(db_df)} sessions).",
            }

        candidate_paths = [
            self.snapshots_dir / f"{file_stem}.csv",
            self.snapshots_dir / f"{can_sym}.csv",
            self.snapshots_dir / f"{can_sym.replace('^', '_')}.csv",
        ]
        existing_path = next((p for p in candidate_paths if p.exists()), None)
        if existing_path:
            try:
                df = self._read_cached_file(existing_path, can_sym)
                return {
                    "symbol": symbol,
                    "canonical_symbol": can_sym,
                    "name": SYMBOL_CATALOGUE.get(can_sym, {}).get("name", can_sym),
                    "exchange": exchange,
                    "currency": currency,
                    "state": "verified_snapshot",
                    "is_cached": True,
                    "observations_count": len(df),
                    "start_date": str(df["Date"].min().date()),
                    "end_date": str(df["Date"].max().date()),
                    "message": f"Symbol '{can_sym}' is verified and available offline ({len(df)} sessions).",
                }
            except Exception as e:
                logger.warning("Snapshot read error during validation for %s: %s", can_sym, e)

        # Live probe
        try:
            live_df = self.fetch_live_price_history(can_sym, period="1y")
            return {
                "symbol": symbol,
                "canonical_symbol": can_sym,
                "name": SYMBOL_CATALOGUE.get(can_sym, {}).get("name", can_sym),
                "exchange": exchange,
                "currency": currency,
                "state": "live_validated",
                "is_cached": True,
                "observations_count": len(live_df),
                "start_date": str(live_df["Date"].min().date()),
                "end_date": str(live_df["Date"].max().date()),
                "message": f"Successfully validated and cached '{can_sym}' from market data provider.",
            }
        except Exception as e:
            return {
                "symbol": symbol,
                "canonical_symbol": can_sym,
                "name": can_sym,
                "exchange": exchange,
                "currency": currency,
                "state": "not_available",
                "is_cached": False,
                "error_reason": str(e),
                "message": f"Validation failed for '{can_sym}': {e}",
            }

    def search_symbols(
        self,
        query: str = "",
        limit: int = 15,
        page: int = 1,
        currency_hint: str | None = None,
        sector: str | None = None,
        index: str | None = None,
        cap_bucket: str | None = None,
        return_total: bool = False,
        db: Any = None,
    ) -> list[dict[str, Any]] | tuple[list[dict[str, Any]], int]:
        """
        Database-backed fuzzy search across full instrument universe.
        Ranked by exact symbol match, prefix match, and index memberships.
        Supports pagination (page, limit) and filters (sector, index, cap_bucket, currency).
        """
        q = (query or "").strip()
        q_upper = q.upper()

        session = db or SessionLocal()
        should_close = db is None

        results: list[dict[str, Any]] = []
        total_count = 0
        seen_symbols: set[str] = set()

        try:
            # Check DB count
            inst_query = session.query(Instrument).filter(Instrument.is_active == True)

            # Apply filters
            if currency_hint:
                inst_query = inst_query.filter(Instrument.currency == currency_hint.upper())
            if sector:
                inst_query = inst_query.filter(Instrument.sector.ilike(f"%{sector}%"))
            if cap_bucket:
                inst_query = inst_query.filter(Instrument.cap_bucket.ilike(f"%{cap_bucket}%"))
            if index:
                inst_query = inst_query.filter(Instrument.index_memberships_json.ilike(f"%{index}%"))

            # Apply text search if query is given
            if q:
                inst_query = inst_query.filter(
                    or_(
                        Instrument.symbol.ilike(f"%{q}%"),
                        Instrument.name.ilike(f"%{q}%"),
                        Instrument.isin.ilike(f"%{q}%"),
                        Instrument.aliases_json.ilike(f"%{q}%"),
                    )
                )

            all_matched = inst_query.all()

            if all_matched:
                total_count = len(all_matched)

                # Score / Rank matched instruments
                def rank_score(item: Instrument) -> int:
                    score = 0
                    sym_up = item.symbol.upper()
                    name_up = item.name.upper()

                    # Exact match
                    if q_upper and (sym_up == q_upper or sym_up.replace(".NS", "") == q_upper):
                        score += 100
                    # Prefix match on symbol
                    elif q_upper and sym_up.startswith(q_upper):
                        score += 80
                    # Prefix match on name
                    elif q_upper and name_up.startswith(q_upper):
                        score += 60
                    else:
                        score += 30

                    # Boost by index membership
                    idx_json = item.index_memberships_json or "[]"
                    if "NIFTY 50" in idx_json or "S&P 500" in idx_json:
                        score += 40
                    elif "NIFTY 100" in idx_json:
                        score += 20
                    elif "NIFTY 500" in idx_json:
                        score += 10

                    return score

                sorted_insts = sorted(all_matched, key=rank_score, reverse=True)

                # Pagination
                start_idx = max(0, (page - 1) * limit)
                page_items = sorted_insts[start_idx : start_idx + limit]

                # Check cache for returned items
                for inst in page_items:
                    is_cached = (self.snapshots_dir / f"{inst.symbol}.csv").exists() or (
                        self.snapshots_dir / f"{inst.symbol.replace('^', '_')}.csv"
                    ).exists()
                    idx_memberships = []
                    try:
                        idx_memberships = json.loads(inst.index_memberships_json or "[]")
                    except Exception:
                        pass

                    alias_note = None
                    if inst.symbol in CORPORATE_ALIASES:
                        alias_note = CORPORATE_ALIASES[inst.symbol].get("note")

                    results.append({
                        "symbol": inst.symbol,
                        "name": inst.name,
                        "exchange": inst.exchange,
                        "currency": inst.currency,
                        "is_cached": is_cached,
                        "status": "verified" if is_cached else "known",
                        "isin": inst.isin,
                        "sector": inst.sector,
                        "industry": inst.industry,
                        "cap_bucket": inst.cap_bucket,
                        "index_memberships": idx_memberships,
                        "note": alias_note,
                    })
                    seen_symbols.add(inst.symbol)

            else:
                # Fallback to local catalog and corporate aliases if DB empty
                for alias_key, alias_info in CORPORATE_ALIASES.items():
                    if q_upper in alias_key or q_upper in alias_info["note"].upper():
                        target_sym = alias_info["target"]
                        if target_sym not in seen_symbols:
                            meta = SYMBOL_CATALOGUE.get(target_sym, {})
                            results.append({
                                "symbol": target_sym,
                                "name": meta.get("name", target_sym),
                                "exchange": meta.get("exchange", "NSE"),
                                "currency": meta.get("currency", "INR"),
                                "is_cached": (self.snapshots_dir / f"{target_sym}.csv").exists(),
                                "status": "known",
                                "alias_of": alias_key,
                                "note": alias_info["note"],
                            })
                            seen_symbols.add(target_sym)

                for sym_key, meta in SYMBOL_CATALOGUE.items():
                    if not q or q_upper in sym_key.upper() or q_upper in meta["name"].upper():
                        if meta["symbol"] not in seen_symbols:
                            results.append({
                                "symbol": meta["symbol"],
                                "name": meta["name"],
                                "exchange": meta["exchange"],
                                "currency": meta["currency"],
                                "is_cached": (self.snapshots_dir / f"{meta['symbol']}.csv").exists(),
                                "status": "known",
                            })
                            seen_symbols.add(meta["symbol"])

                total_count = len(results)
                results = results[:limit]

        finally:
            if should_close:
                session.close()

        if return_total:
            return results, total_count
        return results

    def refresh_symbols(self, target_symbols: list[str] | None = None) -> dict[str, Any]:
        """Refreshes market data snapshots using threaded requests with retry/backoff."""
        refreshed: list[str] = []
        errors: dict[str, str] = {}

        if not target_symbols:
            symbols_to_refresh = set()
            if self.snapshots_dir.exists():
                for f in self.snapshots_dir.glob("*.csv"):
                    if f.stem != "market_snapshot":
                        sym = "^NSEI" if f.stem == "_NSEI" else f.stem
                        symbols_to_refresh.add(sym)
            symbols_to_refresh.update([
                "SPY", "AAPL", "MSFT", "GOOGL", "USDINR=X",
                "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "ICICIBANK.NS", "NIFTYBEES.NS", "^NSEI"
            ])
            symbols_list = sorted(symbols_to_refresh)
        else:
            symbols_list = [normalize_ticker(s)["canonical_symbol"] for s in target_symbols]

        def _fetch_one(s: str) -> tuple[str, bool, str | None]:
            try:
                self.fetch_live_price_history(s, period="2y")
                return (s, True, None)
            except Exception as e:
                return (s, False, str(e))

        with ThreadPoolExecutor(max_workers=4) as executor:
            future_to_sym = {executor.submit(_fetch_one, s): s for s in symbols_list}
            for future in as_completed(future_to_sym):
                s, success, err = future.result()
                if success:
                    refreshed.append(s)
                else:
                    errors[s] = err or "Unknown error"

        return {
            "status": "ok" if refreshed else ("partial_errors" if errors else "failed"),
            "refreshed_symbols": sorted(refreshed),
            "errors": errors,
            "data_source_mode": "live_refreshed" if refreshed else "offline_snapshot",
            "refreshed_at": datetime.now(UTC).isoformat(),
        }
