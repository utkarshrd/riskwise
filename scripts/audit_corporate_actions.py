#!/usr/bin/env python3
"""
scripts/audit_corporate_actions.py

Audits all market snapshots for daily |returns| > 15% on both close and adj_close,
and inspects corporate actions (splits, dividends) from Yahoo Finance.
"""

import json
from pathlib import Path

import pandas as pd
import yfinance as yf

REPO_ROOT = Path(__file__).resolve().parent.parent
MANIFEST_FILE = REPO_ROOT / "data" / "manifests" / "market_manifest.json"

with open(MANIFEST_FILE, "r", encoding="utf-8") as f:
    manifest = json.load(f)

print("=" * 80)
print("AUDIT OF DAILY |RETURNS| > 15% ACROSS ALL REAL MARKET SNAPSHOTS")
print("=" * 80)

audit_findings = []

for sym, meta in manifest["snapshots"].items():
    csv_file = REPO_ROOT / meta["file_path"]
    df = pd.read_csv(csv_file)
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").reset_index(drop=True)

    df["close_ret"] = df["close"].pct_change()
    df["adj_ret"] = df["adj_close"].pct_change()

    extreme_close = df[df["close_ret"].abs() > 0.15]
    extreme_adj = df[df["adj_ret"].abs() > 0.15]

    has_extreme = not extreme_close.empty or not extreme_adj.empty

    if has_extreme:
        print(f"\n[FLAGGED] Ticker: {sym} ({meta['currency']})")
        for _, row in extreme_close.iterrows():
            dt_str = row["date"].strftime("%Y-%m-%d")
            c = row["close"]
            ac = row["adj_close"]
            cr = row["close_ret"]
            ar = row["adj_ret"]
            msg = f"  Date {dt_str}: Close={c:.2f} ({cr:+.2%}), AdjClose={ac:.2f} ({ar:+.2%})"
            print(msg)
            audit_findings.append({"symbol": sym, "date": dt_str, "close": c, "close_ret": cr, "adj_close": ac, "adj_ret": ar})
    else:
        print(f"[CLEAN]   Ticker: {sym} -> Max |close_ret|: {df['close_ret'].abs().max():.2%}, Max |adj_ret|: {df['adj_ret'].abs().max():.2%}")

print("\n" + "=" * 80)
print("INSPECTING TCS.NS ACTIONS & PRICE ANOMALY")
print("=" * 80)

tcs = yf.Ticker("TCS.NS")
actions = tcs.actions
if actions is not None and not actions.empty:
    print("\nTCS Corporate Actions (Dividends & Splits):")
    print(actions.tail(15))
else:
    print("No actions returned for TCS.NS.")

# Also inspect price history of TCS around 2025 and 2026
tcs_df = pd.read_csv(REPO_ROOT / manifest["snapshots"]["TCS.NS"]["file_path"])
tcs_df["date"] = pd.to_datetime(tcs_df["date"])
print("\nTCS Price Sample Around 2025-01-15:")
p2025 = tcs_df[tcs_df["date"] == "2025-01-15"]
print(p2025)
print("\nTCS Price Sample Around 2026-06-03:")
p2026 = tcs_df[tcs_df["date"] == "2026-06-03"]
print(p2026)

# Check TCS min and max close and daily jumps
print("\nTCS Price Range:")
print(f"  Min Close: {tcs_df['close'].min()} on {tcs_df.loc[tcs_df['close'].idxmin(), 'date']}")
print(f"  Max Close: {tcs_df['close'].max()} on {tcs_df.loc[tcs_df['close'].idxmax(), 'date']}")
