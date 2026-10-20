from typing import Any

# Curated catalogue of prominent NSE, BSE and US benchmark assets
SYMBOL_CATALOGUE: dict[str, dict[str, Any]] = {
    # NSE Equities & Indices
    "^NSEI": {
        "symbol": "^NSEI",
        "name": "NSE Nifty 50 Index",
        "exchange": "NSE Index",
        "currency": "INR",
        "file_stem": "_NSEI",
    },
    "NIFTYBEES.NS": {
        "symbol": "NIFTYBEES.NS",
        "name": "Nippon India ETF Nifty BeES",
        "exchange": "NSE",
        "currency": "INR",
        "file_stem": "NIFTYBEES.NS",
    },
    "RELIANCE.NS": {
        "symbol": "RELIANCE.NS",
        "name": "Reliance Industries Limited",
        "exchange": "NSE",
        "currency": "INR",
        "file_stem": "RELIANCE.NS",
    },
    "TCS.NS": {
        "symbol": "TCS.NS",
        "name": "Tata Consultancy Services Limited",
        "exchange": "NSE",
        "currency": "INR",
        "file_stem": "TCS.NS",
    },
    "HDFCBANK.NS": {
        "symbol": "HDFCBANK.NS",
        "name": "HDFC Bank Limited",
        "exchange": "NSE",
        "currency": "INR",
        "file_stem": "HDFCBANK.NS",
    },
    "INFY.NS": {
        "symbol": "INFY.NS",
        "name": "Infosys Limited",
        "exchange": "NSE",
        "currency": "INR",
        "file_stem": "INFY.NS",
    },
    "ICICIBANK.NS": {
        "symbol": "ICICIBANK.NS",
        "name": "ICICI Bank Limited",
        "exchange": "NSE",
        "currency": "INR",
        "file_stem": "ICICIBANK.NS",
    },
    "SBIN.NS": {
        "symbol": "SBIN.NS",
        "name": "State Bank of India",
        "exchange": "NSE",
        "currency": "INR",
        "file_stem": "SBIN.NS",
    },
    "BHARTIARTL.NS": {
        "symbol": "BHARTIARTL.NS",
        "name": "Bharti Airtel Limited",
        "exchange": "NSE",
        "currency": "INR",
        "file_stem": "BHARTIARTL.NS",
    },
    "ITC.NS": {
        "symbol": "ITC.NS",
        "name": "ITC Limited",
        "exchange": "NSE",
        "currency": "INR",
        "file_stem": "ITC.NS",
    },
    "KOTAKBANK.NS": {
        "symbol": "KOTAKBANK.NS",
        "name": "Kotak Mahindra Bank Limited",
        "exchange": "NSE",
        "currency": "INR",
        "file_stem": "KOTAKBANK.NS",
    },
    "LT.NS": {
        "symbol": "LT.NS",
        "name": "Larsen & Toubro Limited",
        "exchange": "NSE",
        "currency": "INR",
        "file_stem": "LT.NS",
    },
    "AXISBANK.NS": {
        "symbol": "AXISBANK.NS",
        "name": "Axis Bank Limited",
        "exchange": "NSE",
        "currency": "INR",
        "file_stem": "AXISBANK.NS",
    },
    "HINDUNILVR.NS": {
        "symbol": "HINDUNILVR.NS",
        "name": "Hindustan Unilever Limited",
        "exchange": "NSE",
        "currency": "INR",
        "file_stem": "HINDUNILVR.NS",
    },
    "BAJFINANCE.NS": {
        "symbol": "BAJFINANCE.NS",
        "name": "Bajaj Finance Limited",
        "exchange": "NSE",
        "currency": "INR",
        "file_stem": "BAJFINANCE.NS",
    },
    "MARUTI.NS": {
        "symbol": "MARUTI.NS",
        "name": "Maruti Suzuki India Limited",
        "exchange": "NSE",
        "currency": "INR",
        "file_stem": "MARUTI.NS",
    },
    "TATAMOTORS.NS": {
        "symbol": "TATAMOTORS.NS",
        "name": "Tata Motors Limited",
        "exchange": "NSE",
        "currency": "INR",
        "file_stem": "TATAMOTORS.NS",
    },
    "SUNPHARMA.NS": {
        "symbol": "SUNPHARMA.NS",
        "name": "Sun Pharmaceutical Industries Limited",
        "exchange": "NSE",
        "currency": "INR",
        "file_stem": "SUNPHARMA.NS",
    },
    "TITAN.NS": {
        "symbol": "TITAN.NS",
        "name": "Titan Company Limited",
        "exchange": "NSE",
        "currency": "INR",
        "file_stem": "TITAN.NS",
    },
    "WIPRO.NS": {
        "symbol": "WIPRO.NS",
        "name": "Wipro Limited",
        "exchange": "NSE",
        "currency": "INR",
        "file_stem": "WIPRO.NS",
    },
    "ASIANPAINT.NS": {
        "symbol": "ASIANPAINT.NS",
        "name": "Asian Paints Limited",
        "exchange": "NSE",
        "currency": "INR",
        "file_stem": "ASIANPAINT.NS",
    },
    "HCLTECH.NS": {
        "symbol": "HCLTECH.NS",
        "name": "HCL Technologies Limited",
        "exchange": "NSE",
        "currency": "INR",
        "file_stem": "HCLTECH.NS",
    },
    "ULTRACEMCO.NS": {
        "symbol": "ULTRACEMCO.NS",
        "name": "UltraTech Cement Limited",
        "exchange": "NSE",
        "currency": "INR",
        "file_stem": "ULTRACEMCO.NS",
    },
    "NTPC.NS": {
        "symbol": "NTPC.NS",
        "name": "NTPC Limited",
        "exchange": "NSE",
        "currency": "INR",
        "file_stem": "NTPC.NS",
    },
    "POWERGRID.NS": {
        "symbol": "POWERGRID.NS",
        "name": "Power Grid Corporation of India",
        "exchange": "NSE",
        "currency": "INR",
        "file_stem": "POWERGRID.NS",
    },
    "TATASTEEL.NS": {
        "symbol": "TATASTEEL.NS",
        "name": "Tata Steel Limited",
        "exchange": "NSE",
        "currency": "INR",
        "file_stem": "TATASTEEL.NS",
    },
    "ADANIENT.NS": {
        "symbol": "ADANIENT.NS",
        "name": "Adani Enterprises Limited",
        "exchange": "NSE",
        "currency": "INR",
        "file_stem": "ADANIENT.NS",
    },
    "TRENT.NS": {
        "symbol": "TRENT.NS",
        "name": "Trent Limited",
        "exchange": "NSE",
        "currency": "INR",
        "file_stem": "TRENT.NS",
    },
    "ETERNAL.NS": {
        "symbol": "ETERNAL.NS",
        "name": "Eternal Limited (formerly Zomato)",
        "exchange": "NSE",
        "currency": "INR",
        "file_stem": "ETERNAL.NS",
    },
    "TMCV.NS": {
        "symbol": "TMCV.NS",
        "name": "Tata Motors Commercial Vehicles Ltd",
        "exchange": "NSE",
        "currency": "INR",
        "file_stem": "TMCV.NS",
    },
    "TMPV.NS": {
        "symbol": "TMPV.NS",
        "name": "Tata Motors Passenger Vehicles Ltd",
        "exchange": "NSE",
        "currency": "INR",
        "file_stem": "TMPV.NS",
    },
    "BAJAJ-AUTO.NS": {
        "symbol": "BAJAJ-AUTO.NS",
        "name": "Bajaj Auto Limited",
        "exchange": "NSE",
        "currency": "INR",
        "file_stem": "BAJAJ-AUTO.NS",
    },
    "COALINDIA.NS": {
        "symbol": "COALINDIA.NS",
        "name": "Coal India Limited",
        "exchange": "NSE",
        "currency": "INR",
        "file_stem": "COALINDIA.NS",
    },
    "JSWSTEEL.NS": {
        "symbol": "JSWSTEEL.NS",
        "name": "JSW Steel Limited",
        "exchange": "NSE",
        "currency": "INR",
        "file_stem": "JSWSTEEL.NS",
    },
    "M&M.NS": {
        "symbol": "M&M.NS",
        "name": "Mahindra & Mahindra Limited",
        "exchange": "NSE",
        "currency": "INR",
        "file_stem": "M&M.NS",
    },
    "ONGC.NS": {
        "symbol": "ONGC.NS",
        "name": "Oil and Natural Gas Corporation",
        "exchange": "NSE",
        "currency": "INR",
        "file_stem": "ONGC.NS",
    },
    "GRASIM.NS": {
        "symbol": "GRASIM.NS",
        "name": "Grasim Industries Limited",
        "exchange": "NSE",
        "currency": "INR",
        "file_stem": "GRASIM.NS",
    },
    "BEL.NS": {
        "symbol": "BEL.NS",
        "name": "Bharat Electronics Limited",
        "exchange": "NSE",
        "currency": "INR",
        "file_stem": "BEL.NS",
    },
    "HAL.NS": {
        "symbol": "HAL.NS",
        "name": "Hindustan Aeronautics Limited",
        "exchange": "NSE",
        "currency": "INR",
        "file_stem": "HAL.NS",
    },
    "CIPLA.NS": {
        "symbol": "CIPLA.NS",
        "name": "Cipla Limited",
        "exchange": "NSE",
        "currency": "INR",
        "file_stem": "CIPLA.NS",
    },
    "DRREDDY.NS": {
        "symbol": "DRREDDY.NS",
        "name": "Dr. Reddy's Laboratories Limited",
        "exchange": "NSE",
        "currency": "INR",
        "file_stem": "DRREDDY.NS",
    },
    "DIVISLAB.NS": {
        "symbol": "DIVISLAB.NS",
        "name": "Divi's Laboratories Limited",
        "exchange": "NSE",
        "currency": "INR",
        "file_stem": "DIVISLAB.NS",
    },
    "APOLLOHOSP.NS": {
        "symbol": "APOLLOHOSP.NS",
        "name": "Apollo Hospitals Enterprise Limited",
        "exchange": "NSE",
        "currency": "INR",
        "file_stem": "APOLLOHOSP.NS",
    },
    "SHRIRAMFIN.NS": {
        "symbol": "SHRIRAMFIN.NS",
        "name": "Shriram Finance Limited",
        "exchange": "NSE",
        "currency": "INR",
        "file_stem": "SHRIRAMFIN.NS",
    },
    "TECHM.NS": {
        "symbol": "TECHM.NS",
        "name": "Tech Mahindra Limited",
        "exchange": "NSE",
        "currency": "INR",
        "file_stem": "TECHM.NS",
    },
    "INDUSINDBK.NS": {
        "symbol": "INDUSINDBK.NS",
        "name": "IndusInd Bank Limited",
        "exchange": "NSE",
        "currency": "INR",
        "file_stem": "INDUSINDBK.NS",
    },
    "NESTLEIND.NS": {
        "symbol": "NESTLEIND.NS",
        "name": "Nestle India Limited",
        "exchange": "NSE",
        "currency": "INR",
        "file_stem": "NESTLEIND.NS",
    },
    "BRITANNIA.NS": {
        "symbol": "BRITANNIA.NS",
        "name": "Britannia Industries Limited",
        "exchange": "NSE",
        "currency": "INR",
        "file_stem": "BRITANNIA.NS",
    },
    "SBILIFE.NS": {
        "symbol": "SBILIFE.NS",
        "name": "SBI Life Insurance Company Limited",
        "exchange": "NSE",
        "currency": "INR",
        "file_stem": "SBILIFE.NS",
    },
    "HDFCLIFE.NS": {
        "symbol": "HDFCLIFE.NS",
        "name": "HDFC Life Insurance Company Limited",
        "exchange": "NSE",
        "currency": "INR",
        "file_stem": "HDFCLIFE.NS",
    },
    # US Equities & Benchmarks
    "SPY": {
        "symbol": "SPY",
        "name": "SPDR S&P 500 ETF Trust",
        "exchange": "NYSE Arca",
        "currency": "USD",
        "file_stem": "SPY",
    },
    "AAPL": {
        "symbol": "AAPL",
        "name": "Apple Inc.",
        "exchange": "NASDAQ",
        "currency": "USD",
        "file_stem": "AAPL",
    },
    "MSFT": {
        "symbol": "MSFT",
        "name": "Microsoft Corporation",
        "exchange": "NASDAQ",
        "currency": "USD",
        "file_stem": "MSFT",
    },
    "GOOGL": {
        "symbol": "GOOGL",
        "name": "Alphabet Inc.",
        "exchange": "NASDAQ",
        "currency": "USD",
        "file_stem": "GOOGL",
    },
    "AMZN": {
        "symbol": "AMZN",
        "name": "Amazon.com, Inc.",
        "exchange": "NASDAQ",
        "currency": "USD",
        "file_stem": "AMZN",
    },
    "NVDA": {
        "symbol": "NVDA",
        "name": "NVIDIA Corporation",
        "exchange": "NASDAQ",
        "currency": "USD",
        "file_stem": "NVDA",
    },
    "META": {
        "symbol": "META",
        "name": "Meta Platforms, Inc.",
        "exchange": "NASDAQ",
        "currency": "USD",
        "file_stem": "META",
    },
    "TSLA": {
        "symbol": "TSLA",
        "name": "Tesla, Inc.",
        "exchange": "NASDAQ",
        "currency": "USD",
        "file_stem": "TSLA",
    },
}

# Base name lookup mapping (e.g. 'RELIANCE' -> 'RELIANCE.NS')
_BASE_NSE_MAP: dict[str, str] = {
    k.replace(".NS", ""): k for k in SYMBOL_CATALOGUE if k.endswith(".NS")
}
_BASE_NSE_MAP["NIFTY"] = "^NSEI"
_BASE_NSE_MAP["NIFTY50"] = "^NSEI"
_BASE_NSE_MAP["NSEI"] = "^NSEI"

# Well-known corporate aliases / demergers / renames
CORPORATE_ALIASES: dict[str, dict[str, str]] = {
    "ZOMATO": {
        "target": "ETERNAL.NS",
        "note": "Zomato renamed to Eternal Limited on stock exchanges (ETERNAL.NS)",
    },
    "ZOMATO.NS": {
        "target": "ETERNAL.NS",
        "note": "Zomato renamed to Eternal Limited on stock exchanges (ETERNAL.NS)",
    },
    "TATAMOTORS": {
        "target": "TMCV.NS",
        "note": "Tata Motors demerged into Commercial Vehicles (TMCV.NS) and Passenger Vehicles (TMPV.NS)",
    },
    "TATAMOTORS.NS": {
        "target": "TMCV.NS",
        "note": "Tata Motors demerged into Commercial Vehicles (TMCV.NS) and Passenger Vehicles (TMPV.NS)",
    },
    "INFOSYS": {
        "target": "INFY.NS",
        "note": "Infosys traded under ticker INFY.NS",
    },
    "RELIANCE": {
        "target": "RELIANCE.NS",
        "note": "Reliance Industries traded under ticker RELIANCE.NS",
    },
    "ADANI": {
        "target": "ADANIENT.NS",
        "note": "Adani Enterprises traded under ticker ADANIENT.NS",
    },
}


def normalize_ticker(symbol: str, currency_hint: str | None = None) -> dict[str, str]:
    """
    Normalizes a user-entered stock ticker into a canonical symbol, currency, exchange,
    and safe filesystem stem.
    
    Rules:
    - Trims whitespace and converts to uppercase.
    - Preserves existing provider suffixes (.NS, .BO). Does not duplicate suffixes.
    - Distinguishes BSE (.BO) from NSE (.NS).
    - Normalizes NIFTY/NSEI index references to '^NSEI' with safe stem '_NSEI'.
    - Checks corporate aliases (e.g. ZOMATO -> ETERNAL.NS, TATAMOTORS -> TMCV.NS).
    - If user enters an un-suffixed symbol that matches known Indian blue-chips, canonicalizes to '.NS'.
    - If currency_hint is 'INR' and symbol has no suffix, normalizes to '.NS'.
    - Infers currency: INR for .NS, .BO, ^NSEI; USD for standard US equities.
    """
    raw = (symbol or "").strip()
    if not raw:
        raise ValueError("Ticker symbol cannot be empty.")

    upper = raw.upper()

    # Index handling
    if upper in ["^NSEI", "_NSEI", "NIFTY", "NIFTY50", "NSEI", "^NIFTY"]:
        return {
            "canonical_symbol": "^NSEI",
            "provider_symbol": "^NSEI",
            "currency": "INR",
            "exchange": "NSE Index",
            "file_stem": "_NSEI",
        }

    # Already has .NS suffix
    if upper.endswith(".NS"):
        clean = upper
        while clean.endswith(".NS.NS"):
            clean = clean[:-3]
        # Check alias for clean symbol (e.g. ZOMATO.NS -> ETERNAL.NS)
        if clean in CORPORATE_ALIASES:
            target = CORPORATE_ALIASES[clean]["target"]
            return normalize_ticker(target)
        return {
            "canonical_symbol": clean,
            "provider_symbol": clean,
            "currency": "INR",
            "exchange": "NSE",
            "file_stem": clean,
        }

    # BSE suffix .BO
    if upper.endswith(".BO"):
        clean = upper
        while clean.endswith(".BO.BO"):
            clean = clean[:-3]
        return {
            "canonical_symbol": clean,
            "provider_symbol": clean,
            "currency": "INR",
            "exchange": "BSE",
            "file_stem": clean,
        }

    # Check corporate aliases first (e.g. ZOMATO -> ETERNAL.NS)
    if upper in CORPORATE_ALIASES:
        target = CORPORATE_ALIASES[upper]["target"]
        return normalize_ticker(target)

    # Check if symbol without suffix is known Indian stock
    if upper in _BASE_NSE_MAP:
        canonical = _BASE_NSE_MAP[upper]
        if canonical == "^NSEI":
            return {
                "canonical_symbol": "^NSEI",
                "provider_symbol": "^NSEI",
                "currency": "INR",
                "exchange": "NSE Index",
                "file_stem": "_NSEI",
            }
        return {
            "canonical_symbol": canonical,
            "provider_symbol": canonical,
            "currency": "INR",
            "exchange": "NSE",
            "file_stem": canonical,
        }

    # Check catalogue directly
    if upper in SYMBOL_CATALOGUE:
        meta = SYMBOL_CATALOGUE[upper]
        return {
            "canonical_symbol": meta["symbol"],
            "provider_symbol": meta["symbol"],
            "currency": meta["currency"],
            "exchange": meta["exchange"],
            "file_stem": meta.get("file_stem", meta["symbol"].replace("^", "_")),
        }

    # If currency_hint is explicitly 'INR', treat un-suffixed symbol as candidate NSE equity
    if currency_hint == "INR":
        canonical = f"{upper}.NS"
        return {
            "canonical_symbol": canonical,
            "provider_symbol": canonical,
            "currency": "INR",
            "exchange": "NSE",
            "file_stem": canonical,
        }

    # Default fallback for arbitrary ticker (e.g. US equity like NVDA or AMD)
    file_stem = upper.replace("^", "_")
    return {
        "canonical_symbol": upper,
        "provider_symbol": upper,
        "currency": "USD",
        "exchange": "US",
        "file_stem": file_stem,
    }


def get_symbol_currency(symbol: str, currency_hint: str | None = None) -> str:
    """Convenience helper to extract currency for a symbol."""
    norm = normalize_ticker(symbol, currency_hint=currency_hint)
    return norm["currency"]


def get_safe_file_stem(symbol: str) -> str:
    """Returns safe filesystem stem for caching CSV snapshots."""
    norm = normalize_ticker(symbol)
    return norm["file_stem"]
