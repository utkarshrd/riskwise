import json
import math
import re
from collections import Counter
from pathlib import Path

import joblib
from backend.app.core.config import settings
from pydantic import BaseModel
from sklearn.metrics.pairwise import cosine_similarity


class Citation(BaseModel):
    source_id: str
    chunk_id: str
    title: str
    publisher: str
    url: str
    relevance_score: float
    snippet: str


class RAGRetriever:
    def __init__(self, index_dir: Path | None = None):
        self.index_dir = index_dir or (settings.ARTIFACTS_DIR / "vector_index")
        self.metadata_file = self.index_dir / "index_metadata.json"
        self.vectorizer_file = self.index_dir / "vectorizer.joblib"
        self.matrix_file = self.index_dir / "tfidf_matrix.joblib"

        self.chunks: list[dict] = []
        self.vectorizer = None
        self.tfidf_matrix = None

        # BM25 index components
        self.corpus_size = 0
        self.tokenized_corpus: list[list[str]] = []
        self.doc_lens: list[int] = []
        self.avgdl: float = 0.0
        self.df: Counter = Counter()

        self._load_index()

    def _load_index(self):
        if self.metadata_file.exists() and self.vectorizer_file.exists() and self.matrix_file.exists():
            try:
                with open(self.metadata_file, "r", encoding="utf-8") as f:
                    meta = json.load(f)
                    self.chunks = meta.get("chunks", [])
                self.vectorizer = joblib.load(self.vectorizer_file)
                self.tfidf_matrix = joblib.load(self.matrix_file)

                # Build BM25 index over chunk contents
                self.corpus_size = len(self.chunks)
                if self.corpus_size > 0:
                    self.tokenized_corpus = [
                        re.findall(r"\b\w+\b", c.get("content", "").lower())
                        for c in self.chunks
                    ]
                    self.doc_lens = [len(d) for d in self.tokenized_corpus]
                    self.avgdl = sum(self.doc_lens) / max(1, self.corpus_size)

                    self.df = Counter()
                    for doc in self.tokenized_corpus:
                        for term in set(doc):
                            self.df[term] += 1
            except (OSError, ValueError, KeyError):
                self.chunks = []
                self.vectorizer = None
                self.tfidf_matrix = None

    @property
    def is_available(self) -> bool:
        return bool(self.chunks and self.vectorizer is not None and self.tfidf_matrix is not None)

    def _compute_bm25(self, query_terms: list[str], k1: float = 1.5, b: float = 0.75) -> list[float]:
        scores = []
        n = self.corpus_size
        for i, doc in enumerate(self.tokenized_corpus):
            dl = self.doc_lens[i]
            tf = Counter(doc)
            score = 0.0
            for q in query_terms:
                if q in tf:
                    doc_freq = self.df.get(q, 0)
                    idf = math.log(1.0 + (n - doc_freq + 0.5) / (doc_freq + 0.5))
                    denom = tf[q] + k1 * (1 - b + b * (dl / self.avgdl))
                    score += idf * (tf[q] * (k1 + 1)) / denom
            scores.append(score)
        return scores

    def retrieve(self, query: str, top_k: int = 3, min_score: float = 0.12) -> list[Citation]:
        if not self.is_available:
            return []

        clean_query = query.strip()
        if not clean_query:
            return []

        # 1. Dense TF-IDF Cosine Similarity
        q_vec = self.vectorizer.transform([clean_query])
        tfidf_scores = cosine_similarity(q_vec, self.tfidf_matrix)[0]

        # 2. Sparse Lexical BM25 Scoring
        q_terms = re.findall(r"\b\w+\b", clean_query.lower())
        bm25_raw = self._compute_bm25(q_terms)
        max_bm25 = max(bm25_raw) if bm25_raw and max(bm25_raw) > 0 else 1.0
        bm25_norm = [s / max_bm25 for s in bm25_raw]

        # 3. Hybrid Reciprocal / Weighted Fusion (0.4 TF-IDF + 0.6 BM25)
        hybrid_scores = [
            0.4 * float(tfidf_scores[i]) + 0.6 * float(bm25_norm[i])
            for i in range(len(self.chunks))
        ]

        # Sort by hybrid score
        top_indices = sorted(range(len(hybrid_scores)), key=lambda i: hybrid_scores[i], reverse=True)
        citations = []
        for idx in top_indices[:top_k]:
            score = hybrid_scores[idx]
            # Minimum similarity threshold: out-of-domain queries rejected
            if score >= min_score and tfidf_scores[idx] > 0.04:
                chunk = self.chunks[idx]
                content = chunk.get("content", "")
                snippet = content[:380] + "..." if len(content) > 380 else content
                citations.append(Citation(
                    source_id=chunk.get("source_id", ""),
                    chunk_id=chunk.get("chunk_id", ""),
                    title=chunk.get("title", ""),
                    publisher=chunk.get("publisher", ""),
                    url=chunk.get("url", ""),
                    relevance_score=round(score, 4),
                    snippet=snippet
                ))

        return citations
