"""
Vector store for the RAG knowledge base.

Design reasoning:
- We need "generate embeddings, store them in a vector database" without
  depending on downloading a pretrained embedding model at runtime (many
  sandboxed / air-gapped deployment environments cannot reach model hubs).
  TF-IDF gives us a legitimate, dependency-light embedding: each chunk becomes
  a sparse vector where dimensions are learned vocabulary terms weighted by
  term-frequency/inverse-document-frequency. It is a real, well-understood
  embedding technique (not a mock), and cosine similarity over TF-IDF vectors
  is a standard, competitive baseline for topical retrieval, especially in a
  closed, curated corpus like a per-role knowledge base.
- FAISS is a genuine vector database / ANN library, used here with an
  IndexFlatIP (exact inner-product search over L2-normalized vectors = cosine
  similarity). At this corpus scale the index is small, so exact search is
  cheap; the same interface would scale to IndexIVFFlat/HNSW for a much
  larger corpus without touching calling code.
- The embedding function is isolated behind `VectorStore.embed_query`, so
  swapping in a real dense encoder (OpenAI/Voyage/sentence-transformers) in
  production is a one-function change; nothing else in the RAG pipeline
  needs to know how embeddings are produced.
"""
from __future__ import annotations

import pickle
from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple

import faiss
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer


@dataclass
class Chunk:
    chunk_id: str
    text: str
    source: str       # e.g. filename
    section: str       # e.g. markdown header this chunk came from


class VectorStore:
    """Per-role vector store: TF-IDF vectorizer + FAISS inner-product index."""

    def __init__(self):
        self.vectorizer: TfidfVectorizer | None = None
        self.index: faiss.Index | None = None
        self.chunks: List[Chunk] = []

    # ---- Build ----

    def build(self, chunks: List[Chunk]) -> None:
        if not chunks:
            raise ValueError("Cannot build a vector store with zero chunks")
        self.chunks = chunks
        texts = [c.text for c in chunks]
        self.vectorizer = TfidfVectorizer(
            stop_words="english",
            ngram_range=(1, 2),
            max_features=20000,
            sublinear_tf=True,
        )
        matrix = self.vectorizer.fit_transform(texts).astype("float32").toarray()
        matrix = self._normalize(matrix)
        dim = matrix.shape[1]
        self.index = faiss.IndexFlatIP(dim)
        self.index.add(matrix)

    @staticmethod
    def _normalize(matrix: np.ndarray) -> np.ndarray:
        norms = np.linalg.norm(matrix, axis=1, keepdims=True)
        norms[norms == 0] = 1e-9
        return matrix / norms

    # ---- Query ----

    def embed_query(self, query: str) -> np.ndarray:
        if self.vectorizer is None:
            raise RuntimeError("Vector store not built/loaded yet")
        vec = self.vectorizer.transform([query]).astype("float32").toarray()
        return self._normalize(vec)

    def search(self, query: str, top_k: int = 4) -> List[Tuple[Chunk, float]]:
        if self.index is None:
            raise RuntimeError("Vector store not built/loaded yet")
        q = self.embed_query(query)
        scores, indices = self.index.search(q, min(top_k, len(self.chunks)))
        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx == -1:
                continue
            results.append((self.chunks[idx], float(score)))
        return results

    # ---- Persistence ----

    def save(self, directory: Path) -> None:
        directory.mkdir(parents=True, exist_ok=True)
        faiss.write_index(self.index, str(directory / "index.faiss"))
        with open(directory / "meta.pkl", "wb") as f:
            pickle.dump({"vectorizer": self.vectorizer, "chunks": self.chunks}, f)

    @classmethod
    def load(cls, directory: Path) -> "VectorStore":
        store = cls()
        store.index = faiss.read_index(str(directory / "index.faiss"))
        with open(directory / "meta.pkl", "rb") as f:
            meta = pickle.load(f)
        store.vectorizer = meta["vectorizer"]
        store.chunks = meta["chunks"]
        return store

    def exists_on_disk(self, directory: Path) -> bool:
        return (directory / "index.faiss").exists() and (directory / "meta.pkl").exists()
