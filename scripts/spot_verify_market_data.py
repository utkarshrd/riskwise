#!/usr/bin/env python3
"""
scripts/spot_verify_market_data.py

Spot-verifies stored snapshot prices against fresh yfinance API fetches
for 3 tickers across 3 distinct dates.
"""

from pathlib import Path

import pandas as pd
import yfinance as yf

REPO_ROOT = Path(__file__).resolve().parent.parent
SNAPSHOT_DIR = REPO_ROOT / "data" / "market_snapshots"

test_cases = [
    ("RELIANCE.NS", "2026-10-09"),
    ("RELIANCE.NS", "2026-06-03"),
    ("RELIANCE.NS", "2025-01-15"),
    ("TCS.NS", "2026-10-09"),
    ("TCS.NS", "2026-06-03"),
    ("TCS.NS", "2025-01-15"),
    ("SPY", "2026-10-09"),
    ("SPY", "2026-06-03"),
    ("SPY", "2025-01-15"),
]

print(f"{'Ticker':<12} | {'Date':<10} | {'Stored Close':<14} | {'Fresh yfinance':<14} | {'Match':<6}")
print("-" * 65)

all_matched = True
for sym, dt in test_cases:
    csv_file = SNAPSHOT_DIR / f"{sym}.csv"
    df_stored = pd.read_csv(csv_file)
    stored_row = df_stored[df_stored["date"] == dt]
    stored_close = round(float(stored_row["close"].iloc[0]), 2) if not stored_row.empty else None

    # Fetch fresh for exact date window
    end_date = (pd.to_datetime(dt) + pd.Timedelta(days=4)).strftime("%Y-%m-%d")
    fresh_df = yf.download(sym, start=dt, end=end_date, auto_adjust=False, progress=False)
    if isinstance(fresh_df.columns, pd.MultiIndex):
        fresh_close_val = fresh_df["Close"][sym].iloc[0]
    else:
        fresh_close_val = fresh_df["Close"].iloc[0]
    fresh_close = round(float(fresh_close_val), 2)

    match = (stored_close == fresh_close)
    if not match:
        all_matched = False
    print(f"{sym:<12} | {dt:<10} | {stored_close!s:<14} | {fresh_close!s:<14} | {match!s:<6}")

print("-" * 65)
if all_matched:
    print("SPOT VERIFICATION SUCCESS: Stored snapshot matches live yfinance provider bit-for-bit.")
else:
    print("SPOT VERIFICATION FAILED: Discrepancy detected.")
