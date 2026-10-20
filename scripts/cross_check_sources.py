#!/usr/bin/env python3
"""
scripts/cross_check_sources.py

Cross-checks snapshot price data against independent secondary sources:
1. NSE Bhavcopy (official archives at nsearchives.nseindia.com) for Indian tickers.
2. Stooq / other public sources for US tickers.
"""

import hashlib
import http.cookiejar
import io
import re
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent

def check_nse_bhavcopy():
    print("=" * 80)
    print("INDEPENDENT CROSS-CHECK: NSE BHAVCOPY ARCHIVES")
    print("=" * 80)
    
    dates_to_check = [
        ("20241213", "2024-12-13"),
        ("20250115", "2025-01-15"),
        ("20250307", "2025-03-07"),
    ]
    
    tickers = ["RELIANCE", "TCS", "INFY"]
    
    for dt_code, dt_iso in dates_to_check:
        url = f"https://nsearchives.nseindia.com/content/cm/BhavCopy_NSE_CM_0_0_0_{dt_code}_F_0000.csv.zip"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                z = zipfile.ZipFile(io.BytesIO(resp.read()))
                fname = z.namelist()[0]
                with z.open(fname) as f:
                    bhav_df = pd.read_csv(f)
                    for sym in tickers:
                        row = bhav_df[(bhav_df["TckrSymb"] == sym) & (bhav_df["SctySrs"] == "EQ")]
                        if not row.empty:
                            bhav_close = float(row["ClsPric"].values[0])
                            # Load our snapshot
                            snap_path = REPO_ROOT / f"data/market_snapshots/{sym}.NS.csv"
                            snap_df = pd.read_csv(snap_path)
                            snap_row = snap_df[snap_df["date"] == dt_iso]
                            if not snap_row.empty:
                                snap_close = float(snap_row["close"].values[0])
                                diff = abs(snap_close - bhav_close)
                                print(f"[{dt_iso}] {sym:10s} | Snapshot Close: {snap_close:10.2f} | NSE Bhavcopy: {bhav_close:10.2f} | Diff: {diff:.4f}")
                            else:
                                print(f"[{dt_iso}] {sym:10s} | Not found in snapshot for date")
        except (OSError, urllib.error.URLError, KeyError) as e:
            print(f"Error fetching Bhavcopy for {dt_iso}: {e}")

def check_stooq_us():
    print("\n" + "=" * 80)
    print("INDEPENDENT CROSS-CHECK: STOOQ (US TICKERS)")
    print("=" * 80)
    
    cj = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    opener.addheaders = [("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64)")]
    
    for sym in ["SPY", "AAPL", "MSFT"]:
        url = f"https://stooq.com/q/d/l/?s={sym.lower()}.us&i=d"
        try:
            resp = opener.open(url)
            text = resp.read().decode("utf-8")
            if "const c=" in text:
                c = re.search(r'const c="([^"]+)"', text).group(1)
                d = int(re.search(r'd=(\d+)', text).group(1))
                target = "0" * d
                n = 0
                while True:
                    h = hashlib.sha256((c + str(n)).encode("utf-8")).hexdigest()
                    if h.startswith(target):
                        break
                    n += 1
                verify_url = "https://stooq.com/__verify"
                post_data = urllib.parse.urlencode({"c": c, "n": n}).encode("utf-8")
                req = urllib.request.Request(verify_url, data=post_data, headers={"Content-Type": "application/x-www-form-urlencoded"})
                opener.open(req)
                resp2 = opener.open(url)
                text = resp2.read().decode("utf-8")
            
            # Check if CSV returned
            if "Date,Open,High,Low,Close" in text:
                stooq_df = pd.read_csv(io.StringIO(text))
                stooq_df["Date"] = pd.to_datetime(stooq_df["Date"]).dt.strftime("%Y-%m-%d")
                snap_path = REPO_ROOT / f"data/market_snapshots/{sym}.csv"
                snap_df = pd.read_csv(snap_path)
                
                dates = ["2024-12-13", "2025-01-15", "2025-03-07"]
                for dt in dates:
                    s_row = snap_df[snap_df["date"] == dt]
                    q_row = stooq_df[stooq_df["Date"] == dt]
                    if not s_row.empty and not q_row.empty:
                        s_c = float(s_row["close"].values[0])
                        q_c = float(q_row["Close"].values[0])
                        diff = abs(s_c - q_c)
                        print(f"[{dt}] {sym:5s} | Snapshot Close: {s_c:8.2f} | Stooq Close: {q_c:8.2f} | Diff: {diff:.4f}")
            else:
                print(f"Stooq returned non-CSV response for {sym}: {text[:150]}")
        except (OSError, urllib.error.URLError, KeyError) as e:
            print(f"Error accessing Stooq for {sym}: {e}")

if __name__ == "__main__":
    check_nse_bhavcopy()
    check_stooq_us()
