"""
Data Setup and Verification Utility for RiskWise

This script guides the download, checksum verification, and placement of
the UCI Credit Card Default benchmark dataset and the offline market snapshots.

Usage:
    python scripts/setup_data.py --info
    python scripts/setup_data.py --download-uci
"""

import argparse
import hashlib
import sys
import urllib.error
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
SNAPSHOT_DIR = DATA_DIR / "market_snapshots"
MANIFEST_DIR = DATA_DIR / "manifests"

UCI_URL = "https://archive.ics.uci.edu/static/public/350/default+of+credit+card+clients.zip"
TARGET_RAW_ZIP = RAW_DIR / "default_of_credit_card_clients.zip"


def print_info():
    print("=" * 60)
    print("RiskWise Data Setup & Provenance Status")
    print("=" * 60)
    print(f"Data Root Directory: {DATA_DIR}")
    print(f"Raw Datasets:        {RAW_DIR}")
    print(f"Market Snapshots:    {SNAPSHOT_DIR}")
    print("\nDataset Requirements:")
    print("  1. Credit Benchmark: UCI Default of Credit Card Clients (Taiwan 2005)")
    print(f"     Source URL: {UCI_URL}")
    print(f"     Status: {'Present' if TARGET_RAW_ZIP.exists() else 'Not downloaded (run with --download-uci)'}")
    print("\n  2. Market Historical Prices:")
    print("     Offline Snapshot file: data/market_snapshots/market_snapshot.csv")
    print("     Status: " + ("Present" if (SNAPSHOT_DIR / "market_snapshot.csv").exists() else "Not yet generated (run scripts/build_market_snapshot.py in Milestone 4)"))
    print("=" * 60)


def download_uci():
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Downloading UCI Credit Card Clients dataset from {UCI_URL}...")
    try:
        urllib.request.urlretrieve(UCI_URL, TARGET_RAW_ZIP)
        print(f"Successfully downloaded to {TARGET_RAW_ZIP}")
        # Compute sha256
        sha256 = hashlib.sha256()
        with open(TARGET_RAW_ZIP, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256.update(chunk)
        digest = sha256.hexdigest()
        print(f"SHA-256 Checksum: {digest}")
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        print(f"Error downloading dataset: {e}", file=sys.stderr)
        print("Manual download instructions:")
        print(f"  Download zip from {UCI_URL} and extract into {RAW_DIR}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="RiskWise Data Setup Utility")
    parser.add_argument("--info", action="store_true", help="Display data status and setup instructions")
    parser.add_argument("--download-uci", action="store_true", help="Download UCI Credit dataset to data/raw/")
    args = parser.parse_args()

    if args.download_uci:
        download_uci()
    else:
        print_info()


if __name__ == "__main__":
    main()
