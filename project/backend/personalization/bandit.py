"""Disjoint LinUCB contextual bandit for choosing which tips to show.

Context vector layout (CONTEXT_DIM = 14), all values roughly in [0, 1]:
  0      bias (always 1.0)
  1-6    category shares of spend in the last 30 days, in CATEGORIES order
         (food, transport, rent, entertainment, utilities, other)
  7      budget utilisation this month = spent / monthly budget, clipped to [0, 2] then / 2
  8      has_budget (1 if any budget set)
  9      is_student (1 if user_type == "student")
  10     anomaly flag (1 if any category is unusually high this week)
  11     projected overrun flag (1 if month-end forecast exceeds budget)
  12     month progress = day of month / days in month
  13     activity = min(1, number of expenses in last 30 days / 30)
"""
import calendar
import json
from datetime import date, datetime, timedelta

import numpy as np

from . import CATEGORIES
from .personas import category_share_vector
from .stats import _to_date, detect_anomalies, forecast_month_end
from .tips import TIPS

CONTEXT_DIM = 14


def init_bandit_tables(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS bandit_arms (
            tip_id TEXT PRIMARY KEY,
            A TEXT NOT NULL,
            b TEXT NOT NULL,
            n INTEGER NOT NULL DEFAULT 0
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS insight_feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            tip_id TEXT NOT NULL,
            reward REAL NOT NULL,
            context TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()


def build_context(expenses, budgets, user_type, today=None):
    """Feature vector describing the user's current situation (see module docstring)."""
    today = _to_date(today or date.today())
    expenses = expenses or []
    cutoff = today - timedelta(days=29)
    recent = []
    for e in expenses:
        try:
            d = _to_date(e["date"])
        except (KeyError, ValueError, TypeError):
            continue
        if cutoff <= d <= today:
            recent.append(e)

    x = np.zeros(CONTEXT_DIM)
    x[0] = 1.0
    x[1:7] = category_share_vector(recent)

    forecast = forecast_month_end(expenses, budgets, today=today)
    budget = forecast["monthly_budget"]
    if budget:
        x[7] = min(max(forecast["spent_so_far"] / budget, 0.0), 2.0) / 2.0
        x[8] = 1.0
        x[11] = 1.0 if forecast["projected_overrun"] > 0 else 0.0
    x[9] = 1.0 if user_type == "student" else 0.0
    x[10] = 1.0 if detect_anomalies(expenses, today=today) else 0.0
    x[12] = today.day / calendar.monthrange(today.year, today.month)[1]
    x[13] = min(1.0, len(recent) / 30.0)
    return x


class LinUCBTipRecommender:
    """One ridge-regression arm per tip; score = theta.x + alpha * sqrt(x' A^-1 x)."""

    def __init__(self, conn, alpha=1.0):
        self.conn = conn
        self.alpha = alpha
        init_bandit_tables(conn)

    def _load(self, tip_id, d):
        row = self.conn.execute("SELECT A, b, n FROM bandit_arms WHERE tip_id = ?", (tip_id,)).fetchone()
        if row:
            A = np.array(json.loads(row[0]), dtype=float)
            b = np.array(json.loads(row[1]), dtype=float)
            if A.shape == (d, d) and b.shape == (d,):
                return A, b, int(row[2])
        return np.eye(d), np.zeros(d), 0

    def _save(self, tip_id, A, b, n):
        self.conn.execute(
            "INSERT OR REPLACE INTO bandit_arms (tip_id, A, b, n) VALUES (?, ?, ?, ?)",
            (tip_id, json.dumps(A.tolist()), json.dumps(b.tolist()), n),
        )
        self.conn.commit()

    def recommend(self, context, k=3, candidate_ids=None):
        x = np.asarray(context, dtype=float)
        d = len(x)
        ids = candidate_ids if candidate_ids is not None else [t["id"] for t in TIPS]
        scored = []
        for order, tip_id in enumerate(ids):
            A, b, _ = self._load(tip_id, d)
            A_inv = np.linalg.inv(A)
            theta = A_inv @ b
            score = float(theta @ x + self.alpha * np.sqrt(max(x @ A_inv @ x, 0.0)))
            scored.append((-score, order, tip_id, score))
        scored.sort()
        return [{"tip_id": t, "score": round(s, 6)} for _, _, t, s in scored[:k]]

    def update(self, tip_id, context, reward):
        x = np.asarray(context, dtype=float)
        A, b, n = self._load(tip_id, len(x))
        A += np.outer(x, x)
        b += float(reward) * x
        self._save(tip_id, A, b, n + 1)


def record_feedback(conn, user_id, tip_id, reward, context):
    """Store a feedback row and update the tip's bandit arm."""
    init_bandit_tables(conn)
    x = np.asarray(context, dtype=float)
    conn.execute(
        "INSERT INTO insight_feedback (user_id, tip_id, reward, context, created_at) VALUES (?, ?, ?, ?, ?)",
        (user_id, tip_id, float(reward), json.dumps(x.tolist()), datetime.now().isoformat(timespec="seconds")),
    )
    conn.commit()
    LinUCBTipRecommender(conn).update(tip_id, x, reward)
