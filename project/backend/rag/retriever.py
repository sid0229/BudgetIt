"""Hybrid retrieval over the curated knowledge base.

Public API (shared contract)::

    retrieve(query: str, k: int = 4) -> list[{"id", "title", "source", "text", "score"}]
    is_dense_enabled() -> bool

Design
------
* Sparse: BM25 (``rank_bm25.BM25Okapi``) over lowercase word tokens with light
  stopword removal and naive plural stripping.
* Dense: Gemini embeddings (``GEMINI_EMBED_MODEL``, default
  ``gemini-embedding-001``) with task types RETRIEVAL_DOCUMENT / RETRIEVAL_QUERY.
  Document embeddings are cached on disk in ``rag/index/`` as
  ``emb_<hash>.npy`` + ``emb_<hash>.json`` where the hash covers the embed model
  and every chunk's id + text, so editing the knowledge base invalidates it.
* Fusion: Reciprocal Rank Fusion, ``score = sum(1 / (60 + rank))``.
* No ``GEMINI_API_KEY`` or any embedding error -> BM25 only. Never raises.
* The index is a lazily-built module-level singleton guarded by a lock.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import threading
import time
from pathlib import Path

import numpy as np
from rank_bm25 import BM25Okapi

from .chunker import KNOWLEDGE_DIR, load_chunks

logger = logging.getLogger(__name__)

BACKEND_DIR = Path(__file__).resolve().parent.parent
INDEX_DIR = Path(__file__).resolve().parent / "index"

try:  # Load backend/.env if present; never fatal.
    from dotenv import load_dotenv

    _env_path = BACKEND_DIR / ".env"
    if _env_path.exists():
        load_dotenv(_env_path, override=False)
except Exception:  # pragma: no cover
    pass

RRF_K = 60
DENSE_CANDIDATES = 20  # how many dense hits take part in fusion
EMBED_BATCH = 100
DENSE_RETRY_SECONDS = 300  # back-off after an embedding failure

STOPWORDS = frozenset(
    """
    a an the and or but if then else of to in on at by for with from into onto
    about as is are was were be been being am do does did doing have has had
    having i me my mine we our ours you your yours he him his she her hers it
    its they them their theirs this that these those there here what which who
    whom whose when where why how can could should would will shall may might
    must not no nor so too very just than also any all some such own same each
    few more most other only up down out over under again further once s t
    don doesn didn isn aren wasn weren won wouldn shouldn couldn get got please
    tell know want need like much many way ways give
    """.split()
)

_TOKEN_RE = re.compile(r"[a-z0-9]+")


def tokenize(text: str) -> list[str]:
    """Lowercase word tokens, stopwords removed, simple plural stripping."""
    out = []
    for tok in _TOKEN_RE.findall((text or "").lower()):
        if tok in STOPWORDS:
            continue
        if len(tok) > 3 and tok.endswith("s") and not tok.endswith("ss"):
            tok = tok[:-1]
        out.append(tok)
    return out


# --------------------------------------------------------------------------
# Embeddings (Gemini). Tests monkeypatch ``_embed_texts``.
# --------------------------------------------------------------------------

def _api_key() -> str | None:
    key = os.environ.get("GEMINI_API_KEY", "").strip()
    return key or None


def _embed_model() -> str:
    return os.environ.get("GEMINI_EMBED_MODEL", "").strip() or "gemini-embedding-001"


_client = None
_client_key = None


def _get_client():
    global _client, _client_key
    key = _api_key()
    if not key:
        raise RuntimeError("GEMINI_API_KEY not set")
    if _client is None or _client_key != key:
        from google import genai

        _client = genai.Client(api_key=key)
        _client_key = key
    return _client


def _embed_texts(texts: list[str], task_type: str) -> np.ndarray:
    """Embed texts with Gemini; returns float32 array (n, dim). May raise."""
    client = _get_client()
    try:
        from google.genai import types

        config = types.EmbedContentConfig(task_type=task_type)
    except Exception:  # older SDK without task types
        config = None
    vectors: list[list[float]] = []
    for start in range(0, len(texts), EMBED_BATCH):
        batch = texts[start : start + EMBED_BATCH]
        kwargs = {"model": _embed_model(), "contents": batch}
        if config is not None:
            kwargs["config"] = config
        resp = client.models.embed_content(**kwargs)
        embs = resp.embeddings or []
        if len(embs) != len(batch):
            raise RuntimeError("embedding count mismatch")
        vectors.extend(list(e.values) for e in embs)
    return np.asarray(vectors, dtype=np.float32)


def _normalize(mat: np.ndarray) -> np.ndarray:
    mat = np.asarray(mat, dtype=np.float32)
    if mat.ndim == 1:
        mat = mat[None, :]
    norms = np.linalg.norm(mat, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return mat / norms


# --------------------------------------------------------------------------
# Index
# --------------------------------------------------------------------------

def _doc_text(chunk: dict) -> str:
    return f"{chunk['title']}\n{chunk['text']}"


def content_hash(chunks: list[dict], model: str) -> str:
    h = hashlib.sha256(model.encode("utf-8"))
    for ch in chunks:
        h.update(b"\x00" + ch["id"].encode("utf-8") + b"\x01" + _doc_text(ch).encode("utf-8"))
    return h.hexdigest()[:16]


class _Index:
    def __init__(self, chunks: list[dict]):
        self.chunks = chunks
        self.bm25 = BM25Okapi([tokenize(_doc_text(c)) for c in chunks]) if chunks else None
        self.embeddings: np.ndarray | None = None  # normalised (n, dim)
        self.model: str | None = None
        self.dense_failed_at: float | None = None
        self._query_cache: dict[str, np.ndarray] = {}

    # -- dense -----------------------------------------------------------
    def ensure_dense(self) -> bool:
        """Load or compute document embeddings. Returns True if available."""
        if not _api_key() or not self.chunks:
            return False
        model = _embed_model()
        if self.embeddings is not None and self.model == model:
            return True
        if self.dense_failed_at and time.time() - self.dense_failed_at < DENSE_RETRY_SECONDS:
            return False
        digest = content_hash(self.chunks, model)
        npy = INDEX_DIR / f"emb_{digest}.npy"
        meta = INDEX_DIR / f"emb_{digest}.json"
        try:
            if npy.exists() and meta.exists():
                info = json.loads(meta.read_text(encoding="utf-8"))
                emb = np.load(npy)
                if info.get("ids") == [c["id"] for c in self.chunks] and emb.shape[0] == len(self.chunks):
                    self.embeddings, self.model = _normalize(emb), model
                    return True
            emb = _embed_texts([_doc_text(c) for c in self.chunks], "RETRIEVAL_DOCUMENT")
            if emb.shape[0] != len(self.chunks):
                raise RuntimeError("embedding count mismatch")
            emb = _normalize(emb)
            try:
                INDEX_DIR.mkdir(parents=True, exist_ok=True)
                np.save(npy, emb)
                meta.write_text(
                    json.dumps({"model": model, "hash": digest, "ids": [c["id"] for c in self.chunks]}),
                    encoding="utf-8",
                )
            except Exception as exc:  # cache write failure is not fatal
                logger.warning("RAG: could not write embedding cache: %s", exc)
            self.embeddings, self.model = emb, model
            self._query_cache.clear()
            return True
        except Exception as exc:
            logger.warning("RAG: dense embeddings unavailable, using BM25 only (%s)", exc)
            self.dense_failed_at = time.time()
            self.embeddings = None
            return False

    def embed_query(self, query: str) -> np.ndarray | None:
        cached = self._query_cache.get(query)
        if cached is not None:
            return cached
        try:
            vec = _normalize(_embed_texts([query], "RETRIEVAL_QUERY"))[0]
        except Exception as exc:
            logger.warning("RAG: query embedding failed, using BM25 only (%s)", exc)
            return None
        if self.embeddings is not None and vec.shape[0] != self.embeddings.shape[1]:
            return None
        if len(self._query_cache) > 256:
            self._query_cache.clear()
        self._query_cache[query] = vec
        return vec

    # -- rankings ----------------------------------------------------------
    def bm25_ranking(self, query: str) -> list[int]:
        tokens = tokenize(query)
        if not tokens or self.bm25 is None:
            return []
        scores = self.bm25.get_scores(tokens)
        order = np.argsort(-scores, kind="stable")
        return [int(i) for i in order if scores[i] > 0]

    def dense_ranking(self, query: str) -> list[int]:
        if not self.ensure_dense():
            return []
        qvec = self.embed_query(query)
        if qvec is None:
            return []
        sims = self.embeddings @ qvec
        order = np.argsort(-sims, kind="stable")
        return [int(i) for i in order[:DENSE_CANDIDATES]]


def rrf_fuse(rankings: list[list[int]], k: int = RRF_K) -> list[tuple[int, float]]:
    """Reciprocal Rank Fusion. Returns [(item, score)] sorted by score desc."""
    scores: dict[int, float] = {}
    first_seen: dict[int, int] = {}
    for ranking in rankings:
        for rank, item in enumerate(ranking, start=1):
            scores[item] = scores.get(item, 0.0) + 1.0 / (k + rank)
            first_seen.setdefault(item, len(first_seen))
    return sorted(scores.items(), key=lambda kv: (-kv[1], first_seen[kv[0]]))


_INDEX: _Index | None = None
_LOCK = threading.Lock()


def get_index() -> _Index:
    """Lazily build the BM25 index (thread-safe singleton)."""
    global _INDEX
    if _INDEX is None:
        with _LOCK:
            if _INDEX is None:
                try:
                    chunks = load_chunks(KNOWLEDGE_DIR)
                except Exception as exc:
                    logger.error("RAG: failed to load knowledge base: %s", exc)
                    chunks = []
                _INDEX = _Index(chunks)
    return _INDEX


def reset_index() -> None:
    """Drop the cached index (used by tests and after editing knowledge files)."""
    global _INDEX
    with _LOCK:
        _INDEX = None


def is_dense_enabled() -> bool:
    """True when Gemini embeddings are configured and the dense index is usable."""
    try:
        if not _api_key():
            return False
        idx = get_index()
        with _LOCK:
            return idx.ensure_dense()
    except Exception:
        return False


def retrieve(query: str, k: int = 4) -> list[dict]:
    """Hybrid BM25 + dense retrieval fused with RRF. Never raises."""
    try:
        if not query or not query.strip() or k <= 0:
            return []
        idx = get_index()
        if not idx.chunks:
            return []
        rankings = [idx.bm25_ranking(query)]
        if _api_key():
            with _LOCK:  # only the (one-off) document embedding step is serialised
                dense_ok = idx.ensure_dense()
            dense = idx.dense_ranking(query) if dense_ok else []
            if dense:
                rankings.append(dense)
        fused = rrf_fuse([r for r in rankings if r])
        results = []
        for i, score in fused[:k]:
            ch = idx.chunks[i]
            results.append(
                {
                    "id": ch["id"],
                    "title": ch["title"],
                    "source": ch["source"],
                    "text": ch["text"],
                    "score": float(score),
                }
            )
        return results
    except Exception as exc:  # pragma: no cover - defensive
        logger.error("RAG: retrieve failed: %s", exc)
        return []
