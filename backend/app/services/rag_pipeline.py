"""
RAG pipeline orchestration: load role-specific knowledge base documents,
chunk them, build/load a per-role vector store, and expose retrieval.

Chunking strategy:
  We split each markdown knowledge-base file by its `##` section headers
  first (these documents are hand-curated so headers already delimit
  coherent topics -- "API Design", "Caching", "Transformers and LLMs", etc).
  Within a section, if the text still exceeds `chunk_max_words`, we further
  split on sentence boundaries into overlapping windows (chunk_overlap_words)
  so that a fact near a chunk boundary is not lost from context in either
  neighboring chunk. This two-level strategy (semantic section boundary,
  then bounded sliding window) keeps chunks topically coherent (good for
  precision) while bounding their size (good for keeping retrieved context
  focused rather than noisy) -- more effective for downstream question
  generation than naive fixed-size chunking of the raw file.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List, Tuple

from app.config import get_settings
from app.services.vector_store import Chunk, VectorStore

settings = get_settings()

_HEADER_RE = re.compile(r"^##\s+(.*)$", re.MULTILINE)

# in-memory cache so we only build/load each role's index once per process
_STORE_CACHE: Dict[str, VectorStore] = {}


def _split_into_sections(markdown_text: str) -> List[Tuple[str, str]]:
    """Return list of (section_title, section_body) from a '## '-delimited doc."""
    matches = list(_HEADER_RE.finditer(markdown_text))
    sections = []
    for i, match in enumerate(matches):
        title = match.group(1).strip()
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(markdown_text)
        body = markdown_text[start:end].strip()
        if body:
            sections.append((title, body))
    return sections


def _sliding_window_split(text: str, max_words: int, overlap_words: int) -> List[str]:
    sentences = re.split(r"(?<=[.!?])\s+", text)
    windows: List[str] = []
    current: List[str] = []
    current_len = 0

    def flush():
        if current:
            windows.append(" ".join(current).strip())

    for sentence in sentences:
        words = sentence.split()
        if current_len + len(words) > max_words and current:
            flush()
            # start next window with overlap from the tail of the previous one
            tail_words = " ".join(current).split()[-overlap_words:]
            current = [" ".join(tail_words)] if tail_words else []
            current_len = len(tail_words)
        current.append(sentence)
        current_len += len(words)
    flush()
    return [w for w in windows if w]


def load_and_chunk_document(path: Path) -> List[Chunk]:
    text = path.read_text(encoding="utf-8")
    sections = _split_into_sections(text)
    chunks: List[Chunk] = []
    for sec_idx, (title, body) in enumerate(sections):
        word_count = len(body.split())
        if word_count <= settings.chunk_max_words:
            pieces = [body]
        else:
            pieces = _sliding_window_split(body, settings.chunk_max_words, settings.chunk_overlap_words)
        for piece_idx, piece in enumerate(pieces):
            chunk_id = f"{path.stem}::{sec_idx}::{piece_idx}"
            chunks.append(Chunk(chunk_id=chunk_id, text=piece, source=path.name, section=title))
    return chunks


def _kb_path_for_role(role: str) -> Path:
    path = settings.knowledge_base_dir / f"{role}.md"
    if not path.exists():
        raise FileNotFoundError(
            f"No knowledge base document found for role '{role}' at {path}"
        )
    return path


def get_store_for_role(role: str, force_rebuild: bool = False) -> VectorStore:
    if not force_rebuild and role in _STORE_CACHE:
        return _STORE_CACHE[role]

    role_dir = settings.vector_index_dir / role
    store = VectorStore()

    if not force_rebuild and store.exists_on_disk(role_dir):
        store = VectorStore.load(role_dir)
    else:
        doc_path = _kb_path_for_role(role)
        chunks = load_and_chunk_document(doc_path)
        store.build(chunks)
        store.save(role_dir)

    _STORE_CACHE[role] = store
    return store


def retrieve(role: str, query: str, top_k: int | None = None) -> List[Tuple[Chunk, float]]:
    store = get_store_for_role(role)
    k = top_k or settings.retrieval_top_k
    results = store.search(query, top_k=k)
    # Filter out near-zero-similarity noise -- better to retrieve fewer, more
    # relevant chunks than pad context with irrelevant material.
    return [(c, s) for c, s in results if s > 0.02]


def build_all_indexes(force_rebuild: bool = True) -> None:
    """Utility to (re)build every role's index, e.g. at deploy time."""
    for role in settings.role_list:
        get_store_for_role(role, force_rebuild=force_rebuild)
