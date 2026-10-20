#!/usr/bin/env python3
"""
scripts/package_zip.py

Creates a clean, portable distribution ZIP of RiskWise for sharing.
Excludes local virtualenvs (backend/venv), node_modules, build caches,
and git files, keeping the zip under ~50MB instead of ~1.5GB.
"""

import os
import zipfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_ZIP = REPO_ROOT / "riskwise_clean.zip"

EXCLUDE_DIRS = {
    "venv",
    ".venv",
    "node_modules",
    ".next",
    ".git",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    ".idea",
    ".vscode",
}

EXCLUDE_EXTS = {
    ".pyc",
    ".pyo",
    ".coverage",
    ".shm",
    ".wal",
}

EXCLUDE_FILES = {
    "riskwise_clean.zip",
    ".coverage",
}


def create_clean_zip():
    print(f"Creating clean distribution ZIP at: {OUTPUT_ZIP} ...")
    total_files = 0
    total_uncompressed_bytes = 0

    with zipfile.ZipFile(OUTPUT_ZIP, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        for root, dirs, files in os.walk(REPO_ROOT):
            # Prune excluded directories in-place
            dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]

            for file in files:
                file_path = Path(root) / file
                rel_path = file_path.relative_to(REPO_ROOT)

                # Skip excluded extensions or specific files
                if file_path.suffix in EXCLUDE_EXTS or file in EXCLUDE_FILES:
                    continue

                zf.write(file_path, arcname=str(rel_path))
                total_files += 1
                total_uncompressed_bytes += file_path.stat().st_size

    zip_size_mb = OUTPUT_ZIP.stat().st_size / (1024 * 1024)
    raw_size_mb = total_uncompressed_bytes / (1024 * 1024)
    print(f"SUCCESS: Packaged {total_files} files.")
    print(f"Uncompressed: {raw_size_mb:.1f} MB -> Clean ZIP: {zip_size_mb:.1f} MB")
    print(f"Archive saved to: {OUTPUT_ZIP}")


if __name__ == "__main__":
    create_clean_zip()
