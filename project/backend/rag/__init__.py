"""Retrieval-augmented knowledge base for BudgetIt (curated Indian personal-finance docs)."""

from .retriever import is_dense_enabled, retrieve

__all__ = ["retrieve", "is_dense_enabled"]
