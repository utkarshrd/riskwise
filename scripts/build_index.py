#!/usr/bin/env python3
"""
scripts/build_index.py

Builds a deterministic, offline-capable vector/retrieval index over the curated
knowledge corpus in knowledge/sources/.
Persists chunks, TF-IDF vectorizer, and document vectors to artifacts/vector_index/.
Adheres to ADR-002 and ADR-006: 100% local, zero-download, reproducible.
"""

import csv
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

import joblib
from sklearn.feature_extraction.text import TfidfVectorizer

REPO_ROOT = Path(__file__).resolve().parent.parent
KNOWLEDGE_DIR = REPO_ROOT / "knowledge"
SOURCES_DIR = KNOWLEDGE_DIR / "sources"
MANIFEST_PATH = KNOWLEDGE_DIR / "manifest.csv"
INDEX_DIR = REPO_ROOT / "artifacts" / "vector_index"


def compute_sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def chunk_markdown_file(source_id: str, title: str, publisher: str, url: str, filepath: Path) -> list[dict]:
    text = filepath.read_text(encoding="utf-8")
    lines = text.split("\n")
    chunks = []
    current_section = "Overview"
    current_lines = []

    def flush_chunk(idx: int):
        content = "\n".join(current_lines).strip()
        if content:
            chunk_id = f"src_{source_id}_chunk_{idx}"
            chunks.append({
                "source_id": source_id,
                "chunk_id": chunk_id,
                "title": title,
                "publisher": publisher,
                "url": url,
                "section": current_section,
                "content": content,
                "content_hash": compute_sha256(content.encode("utf-8"))
            })

    chunk_counter = 1
    for line in lines:
        if line.startswith("## "):
            flush_chunk(chunk_counter)
            chunk_counter += 1
            current_section = line.replace("## ", "").strip()
            current_lines = [line]
        elif line.startswith("# "):
            if not current_lines:
                current_lines.append(line)
        else:
            current_lines.append(line)

    flush_chunk(chunk_counter)
    return chunks


def build_index():
    print(f"[{datetime.now(UTC).isoformat()}] Starting RiskWise Offline Knowledge Indexer...")
    INDEX_DIR.mkdir(parents=True, exist_ok=True)

    if not MANIFEST_PATH.exists():
        raise FileNotFoundError(f"Knowledge manifest not found at {MANIFEST_PATH}")

    # Read manifest
    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        manifest_sources = list(reader)

    print(f"Found {len(manifest_sources)} registered sources in manifest.")

    all_chunks = []
    for src in manifest_sources:
        src_id = src["id"]
        filename = src.get("filename")
        if not filename:
            # Fallback by source id or pattern
            matches = list(SOURCES_DIR.glob(f"*{src_id}*.md"))
            if not matches:
                continue
            src_file = matches[0]
        else:
            src_file = SOURCES_DIR / filename

        if not src_file.exists():
            print(f"Warning: source file {src_file} missing on disk.")
            continue

        file_bytes = src_file.read_bytes()
        actual_sha = compute_sha256(file_bytes)
        expected_sha = src.get("sha256_checksum", "")
        if expected_sha and actual_sha != expected_sha:
            print(f"Warning: Checksum mismatch for {src_file.name}. Actual: {actual_sha}, Expected: {expected_sha}")

        chunks = chunk_markdown_file(
            source_id=src_id,
            title=src["title"],
            publisher=src.get("publisher_reference") or src.get("publisher", ""),
            url=src.get("url_reference") or src.get("url", ""),
            filepath=src_file
        )
        all_chunks.extend(chunks)
        print(f"  - Parsed '{src['title']}': {len(chunks)} chunks.")

    if not all_chunks:
        raise ValueError("No text chunks generated from knowledge sources.")

    corpus = [f"{c['title']} | {c['section']} | {c['content']}" for c in all_chunks]

    # Fit deterministic TF-IDF model
    vectorizer = TfidfVectorizer(
        lowercase=True,
        stop_words="english",
        ngram_range=(1, 2),
        sublinear_tf=True,
        max_features=5000
    )
    tfidf_matrix = vectorizer.fit_transform(corpus)

    # Persist artifacts
    vectorizer_path = INDEX_DIR / "vectorizer.joblib"
    matrix_path = INDEX_DIR / "tfidf_matrix.joblib"
    metadata_path = INDEX_DIR / "index_metadata.json"

    joblib.dump(vectorizer, vectorizer_path)
    joblib.dump(tfidf_matrix, matrix_path)

    metadata = {
        "built_at": datetime.now(UTC).isoformat(),
        "total_sources": len(manifest_sources),
        "total_chunks": len(all_chunks),
        "vocab_size": len(vectorizer.vocabulary_),
        "chunks": all_chunks
    }
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    print(f"Successfully built knowledge index with {len(all_chunks)} chunks and {len(vectorizer.vocabulary_)} terms.")
    print(f"Artifacts saved to {INDEX_DIR}")
    return metadata


if __name__ == "__main__":
    build_index()
