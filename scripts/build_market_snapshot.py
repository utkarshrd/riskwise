#!/usr/bin/env python3
"""
scripts/build_market_snapshot.py

Downloads and validates REAL point-in-time daily market history from Yahoo Finance
via yfinance for both the primary INR universe (NSE equities & NIFTY benchmark)
and the secondary USD universe (S&P 500 & US equities).

Adheres strictly to PRD §0.6, §5.2, and ADR-008:
- NO synthetic fallbacks, random walks, or invented prices.
- Preserves provider's Close and Adj Close (auto_adjust=False) with real trading volume.
- Enforces strict validation: non-positive prices rejected, sorted unique dates,
  and anomalies flagged without silent clipping.
- Atomically writes CSVs and updates data/manifests/market_manifest.json with SHA-256 hashes.
"""

import hashlib
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
import yfinance as yf

REPO_ROOT = Path(__file__).resolve().parent.parent
SNAPSHOT_DIR = REPO_ROOT / "data" / "market_snapshots"
MANIFEST_FILE = REPO_ROOT / "data" / "manifests" / "market_manifest.json"

# Universe definitions per ADR-008 and PRD §5.2
UNIVERSE = [
    # Primary INR Universe (NSE Equities and Benchmark)
    {"symbol": "NIFTYBEES.NS", "provider_symbol": "NIFTYBEES.NS", "currency": "INR", "name": "Nippon India ETF Nifty BeES Benchmark"},
    {"symbol": "^NSEI", "provider_symbol": "^NSEI", "currency": "INR", "name": "NSE Nifty 50 Index"},
    {"symbol": "RELIANCE.NS", "provider_symbol": "RELIANCE.NS", "currency": "INR", "name": "Reliance Industries Limited"},
    {"symbol": "TCS.NS", "provider_symbol": "TCS.NS", "currency": "INR", "name": "Tata Consultancy Services Limited"},
    {"symbol": "HDFCBANK.NS", "provider_symbol": "HDFCBANK.NS", "currency": "INR", "name": "HDFC Bank Limited"},
    {"symbol": "INFY.NS", "provider_symbol": "INFY.NS", "currency": "INR", "name": "Infosys Limited"},
    {"symbol": "ICICIBANK.NS", "provider_symbol": "ICICIBANK.NS", "currency": "INR", "name": "ICICI Bank Limited"},

    # Secondary USD Universe (S&P 500 and Large-Cap Tech)
    {"symbol": "SPY", "provider_symbol": "SPY", "currency": "USD", "name": "SPDR S&P 500 ETF Trust"},
    {"symbol": "AAPL", "provider_symbol": "AAPL", "currency": "USD", "name": "Apple Inc."},
    {"symbol": "MSFT", "provider_symbol": "MSFT", "currency": "USD", "name": "Microsoft Corporation"},
    {"symbol": "GOOGL", "provider_symbol": "GOOGL", "currency": "USD", "name": "Alphabet Inc."}
]


def compute_file_sha256(filepath: Path) -> str:
    sha = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            sha.update(chunk)
    return sha.hexdigest()


def fetch_and_validate_ticker(item: dict, period: str = "2y") -> tuple[pd.DataFrame, dict]:
    sym = item["symbol"]
    prov_sym = item["provider_symbol"]
    print(f"Fetching real market history for {sym} ({item['currency']}) from Yahoo Finance...")

    # Fetch using yfinance with auto_adjust=False to retain both Close and Adj Close
    raw_df = yf.download(prov_sym, period=period, auto_adjust=False, progress=False)
    if raw_df is None or raw_df.empty:
        raise RuntimeError(f"FATAL: yfinance download returned empty data for ticker '{prov_sym}'. Aborting.")

    # Flatten MultiIndex columns if present
    if isinstance(raw_df.columns, pd.MultiIndex):
        raw_df.columns = [c[0].lower() for c in raw_df.columns]
    else:
        raw_df.columns = [str(c).lower() for c in raw_df.columns]

    # Required columns
    col_map = {
        "adj close": "adj_close",
        "close": "close",
        "open": "open",
        "high": "high",
        "low": "low",
        "volume": "volume"
    }
    renamed = {}
    for orig, standard in col_map.items():
        matched = next((c for c in raw_df.columns if c.replace("_", " ") == orig), None)
        if matched:
            renamed[matched] = standard
    clean_df = raw_df.rename(columns=renamed).copy()

    if "adj_close" not in clean_df.columns or "close" not in clean_df.columns:
        raise ValueError(f"Ticker {sym} missing close/adj_close columns in provider output: {list(clean_df.columns)}")

    # Format date index
    clean_df.index = pd.to_datetime(clean_df.index)
    clean_df["date"] = clean_df.index.strftime("%Y-%m-%d")

    # Drop unfinalized sessions or NaN price entries
    nan_count = int(clean_df["adj_close"].isna().sum())
    clean_df = clean_df.dropna(subset=["adj_close", "close"])

    # Ensure sorted unique dates
    clean_df = clean_df.sort_values("date").drop_duplicates(subset=["date"])

    # 1. Validation: No non-positive prices
    if (clean_df["close"] <= 0).any() or (clean_df["adj_close"] <= 0).any():
        bad_prices = clean_df[(clean_df["close"] <= 0) | (clean_df["adj_close"] <= 0)]
        raise ValueError(f"Data corruption detected: Non-positive prices found in {sym}:\n{bad_prices}")

    # 2. Validation: Minimum observation count (at least 200 trading days)
    obs = len(clean_df)
    if obs < 200:
        raise ValueError(f"Insufficient history for {sym}: expected >= 200 observations, got {obs}")

    # 3. Validation: Return bound check
    daily_returns = clean_df["adj_close"].pct_change().dropna()
    anomalies = []
    extreme = daily_returns[daily_returns.abs() > 0.25]
    if not extreme.empty:
        for dt, ret in extreme.items():
            anomalies.append(f"Date {dt}: return {ret:.1%}")

    # Standardize column order
    cols_to_save = ["date", "close", "adj_close", "volume"]
    if "open" in clean_df.columns:
        cols_to_save.extend(["open", "high", "low"])
    final_df = clean_df[cols_to_save]

    meta = {
        "symbol": sym,
        "provider_symbol": prov_sym,
        "name": item["name"],
        "currency": item["currency"],
        "start_date": final_df["date"].iloc[0],
        "end_date": final_df["date"].iloc[-1],
        "observations": obs,
        "nan_sessions_dropped": nan_count,
        "anomalies_flagged": anomalies
    }

    return final_df, meta


def build_real_market_snapshots():
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    MANIFEST_FILE.parent.mkdir(parents=True, exist_ok=True)

    fetched_dfs = {}
    fetched_metas = {}

    retrieval_timestamp = datetime.now(UTC).isoformat()

    # Step 1: Fetch all tickers first. If ANY fails, fail completely without overwriting!
    for item in UNIVERSE:
        df, meta = fetch_and_validate_ticker(item)
        fetched_dfs[item["symbol"]] = df
        fetched_metas[item["symbol"]] = meta

    # Step 2: Write all CSVs and compute SHA-256
    manifest_data = {
        "manifest_version": "2.0",
        "retrieval_timestamp": retrieval_timestamp,
        "source": "yfinance (Yahoo Finance Public API)",
        "adjustment_method": "auto_adjust=False; provider close and dividend/split adjusted adj_close both preserved",
        "missing_data_policy": "Unfinalized sessions with NaN close dropped; zero forward-fill or synthetic interpolation applied",
        "symbols": [u["symbol"] for u in UNIVERSE],
        "snapshots": {}
    }

    for sym, df in fetched_dfs.items():
        # Sanitize symbol for filename (e.g. ^NSEI -> _NSEI.csv)
        safe_name = sym.replace("^", "_")
        csv_path = SNAPSHOT_DIR / f"{safe_name}.csv"
        df.to_csv(csv_path, index=False)

        chk = compute_file_sha256(csv_path)
        meta = fetched_metas[sym]
        meta["file_path"] = str(csv_path.relative_to(REPO_ROOT))
        meta["checksum"] = chk
        manifest_data["snapshots"][sym] = meta
        print(f"  [SAVED] {sym} -> {csv_path.name} ({meta['observations']} obs, SHA: {chk[:12]}...)")

    # Step 3: Write manifest atomically
    temp_manifest = MANIFEST_FILE.with_suffix(".tmp")
    with open(temp_manifest, "w", encoding="utf-8") as f:
        json.dump(manifest_data, f, indent=2)
    temp_manifest.replace(MANIFEST_FILE)

    print(f"\nSuccessfully generated REAL market snapshots for {len(UNIVERSE)} symbols.")
    print(f"Manifest written to {MANIFEST_FILE}")


if __name__ == "__main__":
    try:
        build_real_market_snapshots()
    except (RuntimeError, ValueError, OSError) as e:
        print(f"\n[BUILD MARKET SNAPSHOT FAILED]: {e}", file=sys.stderr)
        sys.exit(1)
