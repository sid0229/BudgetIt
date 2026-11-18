"""Tests for the RAG package (no network: embeddings are always faked)."""

import os
import sys

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

import numpy as np
import pytest

from rag import chunker, retriever


@pytest.fixture(autouse=True)
def clean_index(monkeypatch, tmp_path):
    """Fresh singleton per test, cache in tmp dir, no key unless a test sets one."""
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setattr(retriever, "INDEX_DIR", tmp_path / "index")

    def no_network(texts, task_type):  # pragma: no cover - should never run
        raise AssertionError("network embedding call attempted in tests")

    monkeypatch.setattr(retriever, "_embed_texts", no_network)
    retriever.reset_index()
    yield
    retriever.reset_index()


# ---------------------------------------------------------------- chunking

def test_knowledge_base_size_and_front_matter():
    files = sorted(chunker.KNOWLEDGE_DIR.glob("*.md"))
    assert 15 <= len(files) <= 20
    for path in files:
        meta, body = chunker.parse_front_matter(path.read_text(encoding="utf-8"))
        assert meta.get("title"), path.name
        assert meta.get("source"), path.name
        assert "not financial advice" in body.lower(), path.name


def test_chunk_ids_metadata_and_sizes():
    chunks = chunker.load_chunks()
    ids = [c["id"] for c in chunks]
    assert len(ids) == len(set(ids))
    for c in chunks:
        stem, _, n = c["id"].partition("#")
        assert stem and n.isdigit()
        assert c["title"] and c["source"] and c["text"]
        assert len(c["text"]) <= 1000
    lengths = [len(c["text"]) for c in chunks]
    assert 400 <= sum(lengths) / len(lengths) <= 800


def test_chunk_text_splits_on_headings_and_carries_metadata():
    para = "Saving money is a habit that compounds over time. " * 6  # ~300 chars
    raw = (
        "---\ntitle: Test Doc\nsource: https://example.gov.in\n---\n\n# Test Doc\n\n"
        f"## Alpha\n\n{para}\n\n{para}\n\n## Beta\n\n{para}\n\n{para}\n\n{para}\n"
    )
    chunks = chunker.chunk_text(raw, "test_doc")
    assert [c["id"] for c in chunks] == [f"test_doc#{i}" for i in range(len(chunks))]
    assert len(chunks) >= 2
    assert all(c["title"] == "Test Doc" and c["source"] == "https://example.gov.in" for c in chunks)
    assert all(len(c["text"]) <= 800 for c in chunks)
    assert chunks[0]["text"].startswith("Alpha")
    assert any(c["text"].startswith("Beta") for c in chunks)


def test_tokenize_removes_stopwords_and_plurals():
    assert retriever.tokenize("What are the UPI scams?") == ["upi", "scam"]


# ---------------------------------------------------------------- BM25

def _top_stems(query, k=3):
    return [r["id"].split("#")[0] for r in retriever.retrieve(query, k=k)]


def test_bm25_food_query():
    assert "food_savings" in _top_stems("zomato swiggy food spending")


def test_bm25_upi_pin_query():
    assert "upi_safety_scams" in _top_stems("someone asked for my UPI PIN")


@pytest.mark.parametrize(
    "query,stem",
    [
        ("how do I improve my CIBIL credit score", "credit_cards_cibil"),
        ("netflix spotify subscription autopay", "subscriptions_audit"),
        ("how much emergency fund should I keep", "emergency_fund"),
        ("buy now pay later late fee", "bnpl_debt_avoidance"),
        ("form 16 ITR filing first salary", "first_job_tax"),
    ],
)
def test_bm25_topic_queries(query, stem):
    assert stem in _top_stems(query)


def test_retrieve_result_shape():
    results = retriever.retrieve("index fund SIP", k=4)
    assert 1 <= len(results) <= 4
    for r in results:
        assert set(r) == {"id", "title", "source", "text", "score"}
        assert isinstance(r["score"], float)
    scores = [r["score"] for r in results]
    assert scores == sorted(scores, reverse=True)


def test_retrieve_edge_cases():
    assert retriever.retrieve("", k=4) == []
    assert retriever.retrieve("   ", k=4) == []
    assert retriever.retrieve("the and of", k=4) == []  # only stopwords
    assert retriever.retrieve("upi", k=0) == []
    assert len(retriever.retrieve("upi", k=2)) <= 2


# ---------------------------------------------------------------- RRF / dense

def test_rrf_fuse_math():
    fused = retriever.rrf_fuse([[0, 1, 2], [2, 0, 3]], k=60)
    scores = dict(fused)
    assert scores[0] == pytest.approx(1 / 61 + 1 / 62)
    assert scores[2] == pytest.approx(1 / 63 + 1 / 61)
    assert scores[3] == pytest.approx(1 / 63)
    assert [i for i, _ in fused][:2] == [0, 2]


def _fake_embedder(target_stem, chunks, calls):
    """Documents of `target_stem` point along e0; queries point along e0 too."""
    target_texts = {retriever._doc_text(c) for c in chunks if c["id"].startswith(target_stem + "#")}

    def fake(texts, task_type):
        calls.append(task_type)
        out = np.zeros((len(texts), 8), dtype=np.float32)
        for i, t in enumerate(texts):
            if task_type == "RETRIEVAL_QUERY" or t in target_texts:
                out[i, 0] = 1.0
            else:
                out[i, 1 + (hash(t) % 7)] = 1.0
        return out

    return fake


def test_hybrid_rrf_with_fake_embeddings(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "fake-key")
    chunks = chunker.load_chunks()
    calls = []
    monkeypatch.setattr(retriever, "_embed_texts", _fake_embedder("student_discounts", chunks, calls))
    # Fake vectors tie for all non-target docs; only let the genuine dense hits fuse.
    n_target = sum(c["id"].startswith("student_discounts#") for c in chunks)
    monkeypatch.setattr(retriever, "DENSE_CANDIDATES", n_target)

    # Query has no lexical overlap with student_discounts; dense must pull it in.
    results = retriever.retrieve("zomato swiggy food spending", k=6)
    stems = [r["id"].split("#")[0] for r in results]
    assert "food_savings" in stems  # from BM25
    assert "student_discounts" in stems  # from dense
    assert retriever.is_dense_enabled() is True
    assert "RETRIEVAL_DOCUMENT" in calls and "RETRIEVAL_QUERY" in calls

    # Embeddings cached on disk keyed by content hash.
    assert list(retriever.INDEX_DIR.glob("emb_*.npy"))
    assert list(retriever.INDEX_DIR.glob("emb_*.json"))

    # A fresh index re-uses the disk cache instead of re-embedding documents.
    retriever.reset_index()
    calls.clear()
    retriever.retrieve("food", k=3)
    assert "RETRIEVAL_DOCUMENT" not in calls


def test_fused_score_beats_single_list(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "fake-key")
    chunks = chunker.load_chunks()
    monkeypatch.setattr(retriever, "_embed_texts", _fake_embedder("upi_safety_scams", chunks, []))
    results = retriever.retrieve("someone asked for my UPI PIN", k=4)
    assert results[0]["id"].startswith("upi_safety_scams#")
    # Appearing in both rankings gives more than any single-list max (1/61).
    assert results[0]["score"] > 1 / 61


# ---------------------------------------------------------------- fallback

def test_no_key_means_bm25_only():
    assert retriever.is_dense_enabled() is False
    assert retriever.retrieve("upi pin", k=3)


def test_embedding_error_falls_back_to_bm25(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "fake-key")

    def boom(texts, task_type):
        raise RuntimeError("quota exceeded")

    monkeypatch.setattr(retriever, "_embed_texts", boom)
    results = retriever.retrieve("someone asked for my UPI PIN", k=3)
    assert results and results[0]["id"].startswith("upi_safety_scams#")
    assert retriever.is_dense_enabled() is False


def test_query_embedding_error_falls_back(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "fake-key")

    def docs_only(texts, task_type):
        if task_type == "RETRIEVAL_QUERY":
            raise RuntimeError("timeout")
        return np.ones((len(texts), 4), dtype=np.float32)

    monkeypatch.setattr(retriever, "_embed_texts", docs_only)
    results = retriever.retrieve("zomato swiggy food spending", k=3)
    assert "food_savings" in [r["id"].split("#")[0] for r in results]


def test_real_embed_without_key_raises_but_retrieve_does_not(monkeypatch):
    # The real embedder must refuse (not hit the network) without a key.
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    with pytest.raises(RuntimeError):
        retriever._get_client()
    assert retriever.retrieve("food", k=2)
