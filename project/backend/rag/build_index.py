"""Precompute dense embeddings for the knowledge base.

Usage (from project/backend):  python -m rag.build_index
"""

from __future__ import annotations

import sys

from . import retriever


def main() -> int:
    idx = retriever.get_index()
    print(f"Loaded {len(idx.chunks)} chunks from {retriever.KNOWLEDGE_DIR}")
    if not retriever._api_key():
        print("GEMINI_API_KEY is not set: skipping dense embeddings. Retrieval will use BM25 only.")
        return 0
    if idx.ensure_dense():
        model = retriever._embed_model()
        digest = retriever.content_hash(idx.chunks, model)
        print(f"Dense index ready: {idx.embeddings.shape[0]} x {idx.embeddings.shape[1]} "
              f"(model {model}) cached at {retriever.INDEX_DIR / ('emb_' + digest + '.npy')}")
    else:
        print("Embedding failed (see warning above). Retrieval will fall back to BM25 only.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
