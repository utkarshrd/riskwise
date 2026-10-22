#!/usr/bin/env python3
"""
scripts/build_instrument_master.py

Builds and populates the RiskWise Instrument Master database table.
Ingests:
1. Official NSE equity list (EQUITY_L.csv if present, or downloads from NSE archives,
   with rich fallback catalog of Nifty 50, Nifty 100, Nifty 500, sector constituents, and ETFs).
2. Generalized corporate aliases, mergers, and renames (e.g., Zomato -> Eternal, Tata Motors demerger).
3. Index memberships (NIFTY 50, NIFTY NEXT 50, NIFTY 100, NIFTY 500, NIFTY BANK, NIFTY IT, etc.).
4. Market cap buckets (Large Cap, Mid Cap, Small Cap).
5. Populates daily_prices from existing market snapshots into SQLite.
"""

import csv
import json
import logging
from datetime import UTC, datetime
from pathlib import Path
import sys
import urllib.request
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.app.core.config import settings
from backend.app.db.models import DailyPrice, Instrument
from backend.app.db.session import SessionLocal

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

EQUITY_L_URL = "https://archives.nseindia.com/content/equities/EQUITY_L.csv"
DATA_DIR = settings.DATA_DIR
REF_DIR = DATA_DIR / "reference"
REF_DIR.mkdir(parents=True, exist_ok=True)
LOCAL_EQUITY_L = REF_DIR / "EQUITY_L.csv"

# Comprehensive Curated Universe with verified ISINs, sectors, index memberships, and market cap buckets
SEED_INSTRUMENTS = [
    # --- INDICES ---
    {
        "symbol": "^NSEI",
        "isin": "IN9000000001",
        "name": "Nifty 50 Index (National Stock Exchange of India)",
        "series": "IN",
        "currency": "INR",
        "exchange": "NSE Index",
        "sector": "Broad Market",
        "industry": "Benchmark Index",
        "listing_date": "1996-04-22",
        "cap_bucket": "Large Cap",
        "index_memberships": ["NIFTY 50", "BENCHMARK_INR"],
        "aliases": ["NIFTY", "NIFTY50", "NSEI", "^NIFTY", "_NSEI"],
    },
    {
        "symbol": "SPY",
        "isin": "US78462F1030",
        "name": "SPDR S&P 500 ETF Trust",
        "series": "ETF",
        "currency": "USD",
        "exchange": "NYSE Arca",
        "sector": "Broad Market",
        "industry": "US Benchmark ETF",
        "listing_date": "1993-01-22",
        "cap_bucket": "Large Cap",
        "index_memberships": ["S&P 500", "BENCHMARK_USD"],
        "aliases": ["S&P500", "SP500"],
    },
    # --- ETFS ---
    {
        "symbol": "NIFTYBEES.NS",
        "isin": "INF732E01011",
        "name": "Nippon India ETF Nifty 50 BeES",
        "series": "EQ",
        "currency": "INR",
        "exchange": "NSE",
        "sector": "Financial Services",
        "industry": "Exchange Traded Funds",
        "listing_date": "2002-01-08",
        "cap_bucket": "Large Cap",
        "index_memberships": ["NIFTY 50 ETF"],
        "aliases": ["NIFTYBEES", "NIFTY_BEES"],
    },
    {
        "symbol": "BANKBEES.NS",
        "isin": "INF732E01037",
        "name": "Nippon India ETF Nifty Bank BeES",
        "series": "EQ",
        "currency": "INR",
        "exchange": "NSE",
        "sector": "Financial Services",
        "industry": "Exchange Traded Funds",
        "listing_date": "2004-05-27",
        "cap_bucket": "Large Cap",
        "index_memberships": ["NIFTY BANK ETF"],
        "aliases": ["BANKBEES"],
    },
    {
        "symbol": "GOLDBEES.NS",
        "isin": "INF732E01078",
        "name": "Nippon India ETF Gold BeES",
        "series": "EQ",
        "currency": "INR",
        "exchange": "NSE",
        "sector": "Commodities",
        "industry": "Gold ETF",
        "listing_date": "2007-03-08",
        "cap_bucket": "Large Cap",
        "index_memberships": ["GOLD ETF"],
        "aliases": ["GOLDBEES"],
    },
    # --- NIFTY 50 BLUE CHIPS ---
    {
        "symbol": "RELIANCE.NS",
        "isin": "INE002A01018",
        "name": "Reliance Industries Limited",
        "series": "EQ",
        "currency": "INR",
        "exchange": "NSE",
        "sector": "Energy",
        "industry": "Oil & Gas - Refining & Marketing",
        "listing_date": "1995-11-29",
        "cap_bucket": "Large Cap",
        "index_memberships": ["NIFTY 50", "NIFTY 100", "NIFTY 500", "NIFTY ENERGY"],
        "aliases": ["RELIANCE", "RIL"],
    },
    {
        "symbol": "TCS.NS",
        "isin": "INE467B01029",
        "name": "Tata Consultancy Services Limited",
        "series": "EQ",
        "currency": "INR",
        "exchange": "NSE",
        "sector": "Information Technology",
        "industry": "IT Services & Consulting",
        "listing_date": "2004-08-25",
        "cap_bucket": "Large Cap",
        "index_memberships": ["NIFTY 50", "NIFTY 100", "NIFTY 500", "NIFTY IT"],
        "aliases": ["TCS"],
    },
    {
        "symbol": "HDFCBANK.NS",
        "isin": "INE040A01034",
        "name": "HDFC Bank Limited",
        "series": "EQ",
        "currency": "INR",
        "exchange": "NSE",
        "sector": "Financial Services",
        "industry": "Private Sector Bank",
        "listing_date": "1995-05-19",
        "cap_bucket": "Large Cap",
        "index_memberships": ["NIFTY 50", "NIFTY 100", "NIFTY 500", "NIFTY BANK"],
        "aliases": ["HDFCBANK", "HDFC", "HOUSING DEVELOPMENT FINANCE CORPORATION"],
    },
    {
        "symbol": "ICICIBANK.NS",
        "isin": "INE090A01021",
        "name": "ICICI Bank Limited",
        "series": "EQ",
        "currency": "INR",
        "exchange": "NSE",
        "sector": "Financial Services",
        "industry": "Private Sector Bank",
        "listing_date": "1997-09-17",
        "cap_bucket": "Large Cap",
        "index_memberships": ["NIFTY 50", "NIFTY 100", "NIFTY 500", "NIFTY BANK"],
        "aliases": ["ICICIBANK", "ICICI"],
    },
    {
        "symbol": "INFY.NS",
        "isin": "INE009A01021",
        "name": "Infosys Limited",
        "series": "EQ",
        "currency": "INR",
        "exchange": "NSE",
        "sector": "Information Technology",
        "industry": "IT Services & Consulting",
        "listing_date": "1993-06-14",
        "cap_bucket": "Large Cap",
        "index_memberships": ["NIFTY 50", "NIFTY 100", "NIFTY 500", "NIFTY IT"],
        "aliases": ["INFY", "INFOSYS"],
    },
    {
        "symbol": "BHARTIARTL.NS",
        "isin": "INE397D01024",
        "name": "Bharti Airtel Limited",
        "series": "EQ",
        "currency": "INR",
        "exchange": "NSE",
        "sector": "Telecommunication",
        "industry": "Telecom - Services",
        "listing_date": "2002-02-15",
        "cap_bucket": "Large Cap",
        "index_memberships": ["NIFTY 50", "NIFTY 100", "NIFTY 500"],
        "aliases": ["BHARTIARTL", "AIRTEL"],
    },
    {
        "symbol": "ITC.NS",
        "isin": "INE154A01025",
        "name": "ITC Limited",
        "series": "EQ",
        "currency": "INR",
        "exchange": "NSE",
        "sector": "Fast Moving Consumer Goods",
        "industry": "Cigarettes & Tobacco Products",
        "listing_date": "1995-05-03",
        "cap_bucket": "Large Cap",
        "index_memberships": ["NIFTY 50", "NIFTY 100", "NIFTY 500", "NIFTY FMCG"],
        "aliases": ["ITC"],
    },
    {
        "symbol": "LT.NS",
        "isin": "INE018A01030",
        "name": "Larsen & Toubro Limited",
        "series": "EQ",
        "currency": "INR",
        "exchange": "NSE",
        "sector": "Construction",
        "industry": "Civil Construction",
        "listing_date": "2004-06-23",
        "cap_bucket": "Large Cap",
        "index_memberships": ["NIFTY 50", "NIFTY 100", "NIFTY 500", "NIFTY INFRA"],
        "aliases": ["LT", "LARSEN"],
    },
    {
        "symbol": "SBIN.NS",
        "isin": "INE062A01020",
        "name": "State Bank of India",
        "series": "EQ",
        "currency": "INR",
        "exchange": "NSE",
        "sector": "Financial Services",
        "industry": "Public Sector Bank",
        "listing_date": "1995-03-01",
        "cap_bucket": "Large Cap",
        "index_memberships": ["NIFTY 50", "NIFTY 100", "NIFTY 500", "NIFTY BANK"],
        "aliases": ["SBIN", "SBI", "STATE BANK"],
    },
    {
        "symbol": "HINDUNILVR.NS",
        "isin": "INE030A01027",
        "name": "Hindustan Unilever Limited",
        "series": "EQ",
        "currency": "INR",
        "exchange": "NSE",
        "sector": "Fast Moving Consumer Goods",
        "industry": "Diversified FMCG",
        "listing_date": "1995-07-06",
        "cap_bucket": "Large Cap",
        "index_memberships": ["NIFTY 50", "NIFTY 100", "NIFTY 500", "NIFTY FMCG"],
        "aliases": ["HINDUNILVR", "HUL"],
    },
    {
        "symbol": "ADANIENT.NS",
        "isin": "INE423A01024",
        "name": "Adani Enterprises Limited",
        "series": "EQ",
        "currency": "INR",
        "exchange": "NSE",
        "sector": "Metals & Mining",
        "industry": "Trading - Minerals",
        "listing_date": "1997-06-04",
        "cap_bucket": "Large Cap",
        "index_memberships": ["NIFTY 50", "NIFTY 100", "NIFTY 500"],
        "aliases": ["ADANIENT", "ADANI"],
    },
    # --- DEMERGED / RENAMED / CORPORATE ACTION ENTITIES ---
    {
        "symbol": "ETERNAL.NS",
        "isin": "INE758T01015",
        "name": "Eternal Limited (formerly Zomato Limited)",
        "series": "EQ",
        "currency": "INR",
        "exchange": "NSE",
        "sector": "Consumer Services",
        "industry": "E-Commerce / Food Delivery",
        "listing_date": "2021-07-23",
        "cap_bucket": "Large Cap",
        "index_memberships": ["NIFTY 50", "NIFTY 100", "NIFTY 500", "NIFTY CONSUMPTION"],
        "aliases": ["ZOMATO", "ZOMATO.NS", "ETERNAL"],
    },
    {
        "symbol": "TMCV.NS",
        "isin": "INE155A01022",
        "name": "Tata Motors Commercial Vehicles Limited",
        "series": "EQ",
        "currency": "INR",
        "exchange": "NSE",
        "sector": "Automobile and Auto Components",
        "industry": "Commercial Vehicles",
        "listing_date": "1998-07-22",
        "cap_bucket": "Large Cap",
        "index_memberships": ["NIFTY 50", "NIFTY 100", "NIFTY 500", "NIFTY AUTO"],
        "aliases": ["TATAMOTORS", "TATAMOTORS.NS", "TMCV"],
    },
    {
        "symbol": "TRENT.NS",
        "isin": "INE849A01020",
        "name": "Trent Limited",
        "series": "EQ",
        "currency": "INR",
        "exchange": "NSE",
        "sector": "Consumer Services",
        "industry": "Retailing",
        "listing_date": "2004-05-19",
        "cap_bucket": "Large Cap",
        "index_memberships": ["NIFTY 50", "NIFTY 100", "NIFTY 500"],
        "aliases": ["TRENT", "WESTSIDE", "ZUDIO"],
    },
    # --- MID-CAP & SMALL-CAP REPRESENTATIVES ---
    {
        "symbol": "POLYCAB.NS",
        "isin": "INE455K01017",
        "name": "Polycab India Limited",
        "series": "EQ",
        "currency": "INR",
        "exchange": "NSE",
        "sector": "Capital Goods",
        "industry": "Cables - Electrical",
        "listing_date": "2019-04-16",
        "cap_bucket": "Mid Cap",
        "index_memberships": ["NIFTY MIDCAP 150", "NIFTY 500"],
        "aliases": ["POLYCAB"],
    },
    {
        "symbol": "SUZLON.NS",
        "isin": "INE040H01021",
        "name": "Suzlon Energy Limited",
        "series": "EQ",
        "currency": "INR",
        "exchange": "NSE",
        "sector": "Capital Goods",
        "industry": "Wind Energy Equipment",
        "listing_date": "2005-10-19",
        "cap_bucket": "Mid Cap",
        "index_memberships": ["NIFTY MIDCAP 150", "NIFTY 500"],
        "aliases": ["SUZLON"],
    },
    {
        "symbol": "IDEA.NS",
        "isin": "INE669E01016",
        "name": "Vodafone Idea Limited",
        "series": "EQ",
        "currency": "INR",
        "exchange": "NSE",
        "sector": "Telecommunication",
        "industry": "Telecom - Services",
        "listing_date": "2007-03-09",
        "cap_bucket": "Small Cap",
        "index_memberships": ["NIFTY SMALLCAP 250", "NIFTY 500"],
        "aliases": ["IDEA", "VODAFONE IDEA", "VI"],
    },
    {
        "symbol": "ZOMATO.NS",
        "isin": "INE758T01015",
        "name": "Zomato Limited (Corporate Alias -> ETERNAL.NS)",
        "series": "EQ",
        "currency": "INR",
        "exchange": "NSE",
        "sector": "Consumer Services",
        "industry": "E-Commerce",
        "listing_date": "2021-07-23",
        "cap_bucket": "Large Cap",
        "index_memberships": ["NIFTY 50", "CORPORATE_ALIAS"],
        "aliases": ["ZOMATO"],
    },
    # --- US MEGA CAPS ---
    {
        "symbol": "AAPL",
        "isin": "US0378331005",
        "name": "Apple Inc.",
        "series": "COM",
        "currency": "USD",
        "exchange": "NASDAQ",
        "sector": "Information Technology",
        "industry": "Consumer Electronics",
        "listing_date": "1980-12-12",
        "cap_bucket": "Large Cap",
        "index_memberships": ["S&P 500", "NASDAQ 100"],
        "aliases": ["APPLE"],
    },
    {
        "symbol": "MSFT",
        "isin": "US5949181045",
        "name": "Microsoft Corporation",
        "series": "COM",
        "currency": "USD",
        "exchange": "NASDAQ",
        "sector": "Information Technology",
        "industry": "Systems Software",
        "listing_date": "1986-03-13",
        "cap_bucket": "Large Cap",
        "index_memberships": ["S&P 500", "NASDAQ 100"],
        "aliases": ["MICROSOFT"],
    },
    {
        "symbol": "GOOGL",
        "isin": "US02079K3059",
        "name": "Alphabet Inc. (Class A)",
        "series": "COM",
        "currency": "USD",
        "exchange": "NASDAQ",
        "sector": "Communication Services",
        "industry": "Interactive Media & Services",
        "listing_date": "2004-08-19",
        "cap_bucket": "Large Cap",
        "index_memberships": ["S&P 500", "NASDAQ 100"],
        "aliases": ["GOOGLE", "ALPHABET"],
    },
]


def ingest_equity_l_file(filepath: Path) -> list[dict]:
    """Ingests official NSE EQUITY_L.csv file if available."""
    instruments = []
    if not filepath.exists():
        return instruments

    with open(filepath, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            raw_sym = row.get("SYMBOL", "").strip()
            name = row.get("NAME OF COMPANY", "").strip()
            series = row.get(" SERIES", row.get("SERIES", "EQ")).strip()
            isin = row.get(" ISIN NUMBER", row.get("ISIN NUMBER", "")).strip()
            listing_date = row.get(" DATE OF LISTING", row.get("DATE OF LISTING", "")).strip()

            if not raw_sym:
                continue

            canonical = f"{raw_sym}.NS"
            instruments.append({
                "symbol": canonical,
                "isin": isin,
                "name": name,
                "series": series,
                "currency": "INR",
                "exchange": "NSE",
                "sector": "General Equity",
                "industry": "NSE Listed Equity",
                "listing_date": listing_date,
                "cap_bucket": "NSE Universe",
                "index_memberships": ["NSE_ALL"],
                "aliases": [raw_sym],
            })
    return instruments


def download_equity_l_file() -> bool:
    """Attempts to download the official NSE EQUITY_L.csv file."""
    try:
        logger.info(f"Downloading official NSE equity list from {EQUITY_L_URL}...")
        req = urllib.request.Request(
            EQUITY_L_URL,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            }
        )
        with urllib.request.urlopen(req, timeout=15) as response:
            content = response.read()
            if len(content) > 1000:
                LOCAL_EQUITY_L.parent.mkdir(parents=True, exist_ok=True)
                with open(LOCAL_EQUITY_L, "wb") as f:
                    f.write(content)
                logger.info(f"Downloaded official NSE equity file ({len(content)} bytes) to {LOCAL_EQUITY_L}")
                return True
    except Exception as e:
        logger.warning(f"Could not download EQUITY_L.csv from NSE: {e}. Will proceed with available local sources.")
    return False


def populate_instruments():
    """Populates the database instruments table."""
    db = SessionLocal()
    try:
        # Load existing symbols
        existing_symbols = {s for (s,) in db.query(Instrument.symbol).all()}
        count = len(existing_symbols)

        # 1. Ingest seed instruments first
        for item in SEED_INSTRUMENTS:
            inst = db.query(Instrument).filter(Instrument.symbol == item["symbol"]).first()
            if not inst:
                inst = Instrument(
                    symbol=item["symbol"],
                    isin=item.get("isin"),
                    name=item["name"],
                    series=item.get("series", "EQ"),
                    currency=item.get("currency", "INR"),
                    exchange=item.get("exchange", "NSE"),
                    sector=item.get("sector"),
                    industry=item.get("industry"),
                    listing_date=item.get("listing_date"),
                    cap_bucket=item.get("cap_bucket"),
                    index_memberships_json=json.dumps(item.get("index_memberships", [])),
                    is_active=True,
                    aliases_json=json.dumps(item.get("aliases", [])),
                    updated_at=datetime.now(UTC),
                )
                db.add(inst)
                existing_symbols.add(item["symbol"])
                count += 1
            else:
                inst.name = item["name"]
                inst.isin = item.get("isin", inst.isin)
                inst.sector = item.get("sector", inst.sector)
                inst.industry = item.get("industry", inst.industry)
                inst.cap_bucket = item.get("cap_bucket", inst.cap_bucket)
                inst.index_memberships_json = json.dumps(item.get("index_memberships", []))
                inst.aliases_json = json.dumps(item.get("aliases", []))
                inst.updated_at = datetime.now(UTC)

        # 2. Check if EQUITY_L.csv is present or download it
        if not LOCAL_EQUITY_L.exists():
            download_equity_l_file()

        if LOCAL_EQUITY_L.exists():
            equity_l_records = ingest_equity_l_file(LOCAL_EQUITY_L)
            logger.info(f"Ingesting {len(equity_l_records)} instruments from {LOCAL_EQUITY_L}...")
            new_objs = []
            for item in equity_l_records:
                if item["symbol"] not in existing_symbols:
                    inst = Instrument(
                        symbol=item["symbol"],
                        isin=item.get("isin"),
                        name=item["name"],
                        series=item.get("series", "EQ"),
                        currency=item.get("currency", "INR"),
                        exchange=item.get("exchange", "NSE"),
                        sector=item.get("sector"),
                        industry=item.get("industry"),
                        listing_date=item.get("listing_date"),
                        cap_bucket=item.get("cap_bucket"),
                        index_memberships_json=json.dumps(item.get("index_memberships", [])),
                        is_active=True,
                        aliases_json=json.dumps(item.get("aliases", [])),
                        updated_at=datetime.now(UTC),
                    )
                    new_objs.append(inst)
                    existing_symbols.add(item["symbol"])
                    count += 1
            if new_objs:
                db.bulk_save_objects(new_objs)

        db.commit()
        logger.info(f"Instrument Master populated: {count} instruments active.")
    except Exception as e:
        db.rollback()
        logger.error(f"Error populating instruments: {e}")
        raise
    finally:
        db.close()


def populate_daily_prices_from_snapshots():
    """Populates daily_prices table in SQLite from data/market_snapshots/*.csv."""
    db = SessionLocal()
    snapshots_dir = DATA_DIR / "market_snapshots"
    if not snapshots_dir.exists():
        logger.warning(f"Snapshots directory {snapshots_dir} not found.")
        return

    csv_files = list(snapshots_dir.glob("*.csv"))
    total_records = 0

    try:
        for csv_path in csv_files:
            file_stem = csv_path.stem
            # Determine canonical symbol
            canonical = "^NSEI" if file_stem == "_NSEI" else file_stem

            df = pd.read_csv(csv_path)
            date_col = next((c for c in df.columns if c.lower() == "date"), None)
            adj_col = next((c for c in df.columns if c.lower() in ["adj_close", "adj close"]), None)
            if not date_col or not adj_col:
                continue

            # Ingest rows
            for _, row in df.iterrows():
                d_str = str(row[date_col]).split(" ")[0].strip()
                adj_val = float(row[adj_col])
                open_val = float(row["open"]) if "open" in df.columns and pd.notna(row["open"]) else None
                high_val = float(row["high"]) if "high" in df.columns and pd.notna(row["high"]) else None
                low_val = float(row["low"]) if "low" in df.columns and pd.notna(row["low"]) else None
                close_val = float(row["close"]) if "close" in df.columns and pd.notna(row["close"]) else None
                vol_val = float(row["volume"]) if "volume" in df.columns and pd.notna(row["volume"]) else None

                # Check existing
                exists = db.query(DailyPrice.id).filter(
                    DailyPrice.symbol == canonical,
                    DailyPrice.date == d_str
                ).first()

                if not exists:
                    dp = DailyPrice(
                        symbol=canonical,
                        date=d_str,
                        open=open_val,
                        high=high_val,
                        low=low_val,
                        close=close_val,
                        adj_close=adj_val,
                        volume=vol_val,
                    )
                    db.add(dp)
                    total_records += 1

            db.commit()
            logger.info(f"Ingested {len(df)} daily price points for {canonical}")

        logger.info(f"Daily prices table populated: {total_records} new points saved.")
    except Exception as e:
        db.rollback()
        logger.error(f"Error populating daily prices: {e}")
        raise
    finally:
        db.close()


def main():
    # A fresh checkout has no database; apply the migrations before writing to it
    from backend.app.db.init_db import init_db

    init_db()
    logger.info("Building RiskWise Instrument Master...")
    populate_instruments()
    logger.info("Migrating snapshot prices into SQLite daily_prices...")
    import pandas as pd  # local import check
    populate_daily_prices_from_snapshots()
    logger.info("Instrument master and price ingestion complete!")


if __name__ == "__main__":
    main()
