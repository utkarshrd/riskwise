"""
backend/tests/unit/test_market_provenance.py

Automated test validating that:
1. All market snapshots are real, point-in-time Yahoo Finance downloads (via yfinance).
2. data/manifests/market_manifest.json explicitly records real provenance, retrieval timestamps,
   and exact SHA-256 hashes.
3. No synthetic generator signatures or simulated random-walk files exist.
4. Checksums match the on-disk CSV files bit-for-bit.
"""

import hashlib
import json
from datetime import datetime
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
SNAPSHOT_DIR = REPO_ROOT / "data" / "market_snapshots"
MANIFEST_FILE = REPO_ROOT / "data" / "manifests" / "market_manifest.json"


def compute_file_sha256(filepath: Path) -> str:
    sha = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            sha.update(chunk)
    return sha.hexdigest()


def test_market_manifest_provenance_and_anti_fabrication():
    assert MANIFEST_FILE.exists(), f"Market manifest missing at {MANIFEST_FILE}"

    with open(MANIFEST_FILE, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    # 1. Manifest structure and source verification
    assert manifest.get("manifest_version") == "2.0"
    assert "yfinance" in manifest.get("source", "").lower()
    assert manifest.get("retrieval_timestamp") is not None

    # Check timestamp is valid ISO format
    ts = datetime.fromisoformat(manifest["retrieval_timestamp"])
    assert ts.year >= 2024

    # 2. Check each registered snapshot
    snapshots = manifest.get("snapshots", {})
    assert len(snapshots) >= 10, f"Expected at least 10 real instruments, found {len(snapshots)}"

    for sym, meta in snapshots.items():
        # Check metadata attributes
        assert meta["currency"] in ["INR", "USD"]
        assert meta["observations"] >= 200, f"Observations too short for {sym}: {meta['observations']}"
        assert meta.get("checksum") is not None

        # Verify on-disk file
        file_path = REPO_ROOT / meta["file_path"]
        assert file_path.exists(), f"Snapshot file for {sym} missing at {file_path}"

        # Bit-for-bit SHA-256 checksum match
        disk_checksum = compute_file_sha256(file_path)
        assert disk_checksum == meta["checksum"], (
            f"Checksum mismatch for {sym}: expected {meta['checksum']}, got {disk_checksum}"
        )

        # Inspect content
        df = pd.read_csv(file_path)
        assert len(df) == meta["observations"]
        assert "date" in df.columns
        assert "close" in df.columns
        assert "adj_close" in df.columns
        assert "volume" in df.columns

        # Verify no non-positive prices
        assert (df["close"] > 0).all(), f"Non-positive close prices in {sym}"
        assert (df["adj_close"] > 0).all(), f"Non-positive adj_close prices in {sym}"

        # Verify dates are sorted and unique
        dates = pd.to_datetime(df["date"])
        assert dates.is_monotonic_increasing, f"Dates not strictly increasing for {sym}"
        assert df["date"].is_unique, f"Duplicate dates found in {sym}"

    # 3. Bidirectional Parity: Check for unmanifested or stray CSV files
    manifested_filenames = {Path(meta["file_path"]).name for meta in snapshots.values()}
    disk_csv_filenames = {f.name for f in SNAPSHOT_DIR.glob("*.csv")}

    stray_files = disk_csv_filenames - manifested_filenames
    assert stray_files == set(), f"Unmanifested or stray CSV files detected in {SNAPSHOT_DIR}: {stray_files}"

    missing_files = manifested_filenames - disk_csv_filenames
    assert missing_files == set(), f"Manifest references missing CSV files on disk: {missing_files}"


def test_no_synthetic_generator_residuals():
    """
    Ensures that scripts/build_market_snapshot.py does not contain any random-walk
    or synthetic price generation logic.
    """
    script_path = REPO_ROOT / "scripts" / "build_market_snapshot.py"
    content = script_path.read_text(encoding="utf-8")

    forbidden_tokens = [
        "np.random.normal",
        "np.random.seed(42)",
        "np.cumprod",
        "generate_deterministic_market_snapshot",
        "symbol_configs = {"
    ]
    for token in forbidden_tokens:
        assert token not in content, f"Forbidden synthetic generator artifact found: '{token}'"
