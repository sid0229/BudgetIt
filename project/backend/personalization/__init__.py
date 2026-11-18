"""Personalization: spending stats, personas, tips and a LinUCB tip recommender."""

CATEGORIES = ["food", "transport", "rent", "entertainment", "utilities", "other"]


def init_tables(conn):
    """Create personalization tables (safe to call repeatedly)."""
    from .bandit import init_bandit_tables
    init_bandit_tables(conn)
