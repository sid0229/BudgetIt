import os
import sqlite3
import sys
from datetime import date, timedelta

import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from personalization import CATEGORIES, init_tables  # noqa: E402
from personalization.bandit import (  # noqa: E402
    CONTEXT_DIM, LinUCBTipRecommender, build_context, record_feedback,
)
from personalization.categorize import suggest_category  # noqa: E402
from personalization.personas import (  # noqa: E402
    PERSONAS, assign_persona, category_share_vector, kmeans,
)
from personalization.stats import (  # noqa: E402
    category_baselines, detect_anomalies, forecast_month_end,
)
from personalization.tips import TIPS, get_tip  # noqa: E402

TODAY = date(2026, 11, 18)  # Wednesday


def exp(d, cat, amount, desc=""):
    return {"id": 0, "amount": float(amount), "category": cat, "description": desc, "date": d.isoformat()}


def steady_history(weeks=8, today=TODAY):
    """₹100 food on each of Mon/Thu, ₹300 transport once a week, for `weeks` prior weeks."""
    monday = today - timedelta(days=today.weekday())
    rows = []
    for w in range(1, weeks + 1):
        start = monday - timedelta(weeks=w)
        rows.append(exp(start, "food", 100))
        rows.append(exp(start + timedelta(days=3), "food", 100))
        rows.append(exp(start + timedelta(days=1), "transport", 300))
    return rows


@pytest.fixture
def conn():
    c = sqlite3.connect(":memory:")
    c.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT, email TEXT, password_hash TEXT, user_type TEXT)")
    c.execute("CREATE TABLE expenses (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, amount REAL, "
              "category TEXT, description TEXT, date TEXT)")
    init_tables(c)
    yield c
    c.close()


# ---------- stats ----------

def test_baselines_empty():
    b = category_baselines([], today=TODAY)
    assert set(CATEGORIES) <= set(b)
    assert all(v["ewma_weekly"] == 0 and v["weeks_observed"] == 0 for v in b.values())


def test_baselines_steady_and_excludes_current_week():
    rows = steady_history() + [exp(TODAY, "food", 5000)]
    b = category_baselines(rows, today=TODAY)
    assert b["food"]["ewma_weekly"] == pytest.approx(200)
    assert b["food"]["std_weekly"] == pytest.approx(0)
    assert b["food"]["weeks_observed"] == 8
    assert b["transport"]["ewma_weekly"] == pytest.approx(300)
    assert b["rent"]["ewma_weekly"] == 0


def test_detect_anomaly_spike():
    rows = steady_history() + [exp(TODAY, "food", 900), exp(TODAY, "transport", 280)]
    anomalies = detect_anomalies(rows, today=TODAY)
    assert [a["category"] for a in anomalies] == ["food"]
    a = anomalies[0]
    assert a["this_week"] == 900 and a["baseline"] == 200
    assert a["ratio"] == pytest.approx(4.5) and a["z"] > 2


def test_detect_anomaly_needs_history_and_handles_empty():
    assert detect_anomalies([], today=TODAY) == []
    one_week = steady_history(weeks=1) + [exp(TODAY, "food", 2000)]
    assert detect_anomalies(one_week, today=TODAY) == []


def test_anomalies_sorted_by_severity():
    rows = steady_history() + [exp(TODAY, "food", 600), exp(TODAY, "transport", 3000)]
    cats = [a["category"] for a in detect_anomalies(rows, today=TODAY)]
    assert cats == ["transport", "food"]


def test_forecast_empty():
    f = forecast_month_end([], [], today=TODAY)
    assert f["month"] == "2026-11"
    assert f["spent_so_far"] == 0 and f["projected_total"] == 0
    assert f["monthly_budget"] is None and f["overrun_date"] is None
    assert f["projected_overrun"] == 0


def test_forecast_projection_and_overrun():
    # ₹200/day food for the last 28 days; budget 4000/month food + 700/week transport
    rows = [exp(TODAY - timedelta(days=i), "food", 200) for i in range(28)]
    budgets = [{"category": "food", "amount": 4000, "period": "monthly"},
               {"category": "transport", "amount": 700, "period": "weekly"}]
    f = forecast_month_end(rows, budgets, today=TODAY)
    assert f["spent_so_far"] == pytest.approx(200 * 18)
    assert f["by_category"]["food"]["projected"] == pytest.approx(200 * 30)
    assert f["by_category"]["transport"]["budget"] == pytest.approx(3000)  # 700 * 30/7
    assert f["monthly_budget"] == pytest.approx(7000)
    assert f["projected_total"] == pytest.approx(6000)
    assert f["projected_overrun"] == 0 and f["overrun_date"] is None

    tight = [{"category": "food", "amount": 4000, "period": "monthly"}]
    f2 = forecast_month_end(rows, tight, today=TODAY)
    assert f2["projected_overrun"] == pytest.approx(2000)
    assert f2["overrun_date"] == "2026-11-20"  # 3600 spent, 400 left at ₹200/day


def test_forecast_rent_is_lump_sum():
    rows = [exp(date(2026, 10, 1), "rent", 8000), exp(date(2026, 11, 1), "rent", 8000)]
    f = forecast_month_end(rows, [], today=TODAY)
    assert f["by_category"]["rent"]["projected"] == 8000
    f_unpaid = forecast_month_end(rows[:1], [], today=TODAY)
    assert f_unpaid["by_category"]["rent"]["projected"] == 8000
    assert f_unpaid["by_category"]["rent"]["spent"] == 0


# ---------- personas ----------

def test_share_vector():
    assert category_share_vector([]).tolist() == [0.0] * 6
    v = category_share_vector([exp(TODAY, "food", 300), exp(TODAY, "rent", 100), exp(TODAY, "weird", 100)])
    assert v.sum() == pytest.approx(1)
    assert v[CATEGORIES.index("food")] == pytest.approx(0.6)
    assert v[CATEGORIES.index("other")] == pytest.approx(0.2)


def test_kmeans_separates_clusters():
    rng = np.random.default_rng(1)
    a = rng.normal([0, 0], 0.1, size=(20, 2))
    b = rng.normal([5, 5], 0.1, size=(20, 2))
    X = np.vstack([a, b])
    c1, l1 = kmeans(X, 2, seed=3)
    c2, l2 = kmeans(X, 2, seed=3)
    assert np.array_equal(l1, l2)
    assert len(set(l1[:20])) == 1 and len(set(l1[20:])) == 1 and l1[0] != l1[-1]
    c3, l3 = kmeans(X, 2, init=np.array([[0.0, 0.0], [5.0, 5.0]]))
    assert l3[:20].tolist() == [0] * 20 and l3[20:].tolist() == [1] * 20


def test_personas_shape():
    assert 4 <= len(PERSONAS) <= 5
    for p in PERSONAS.values():
        assert len(p["centroid"]) == 6 and sum(p["centroid"]) == pytest.approx(1)
        assert p["label"] and p["description"]


def _add_user(conn, uid, user_type, cat_amounts):
    conn.execute("INSERT INTO users (id, name, email, password_hash, user_type) VALUES (?, ?, ?, '', ?)",
                 (uid, f"u{uid}", f"u{uid}@x.in", user_type))
    for cat, amt in cat_amounts:
        conn.execute("INSERT INTO expenses (user_id, amount, category, description, date) VALUES (?, ?, ?, '', ?)",
                     (uid, amt, cat, TODAY.isoformat()))
    conn.commit()


def test_persona_cold_start(conn):
    _add_user(conn, 1, "student", [("food", 100)])
    p = assign_persona(conn, 1)
    assert p["method"] == "cold_start" and p["key"] in PERSONAS
    _add_user(conn, 2, "professional", [])
    assert assign_persona(conn, 2)["method"] == "cold_start"
    assert assign_persona(conn, 999)["method"] == "cold_start"  # unknown user doesn't crash


def test_persona_prototype(conn):
    _add_user(conn, 1, "student", [("transport", 500)] * 4 + [("food", 100)])
    p = assign_persona(conn, 1)
    assert p == {**p, "key": "commuter", "method": "prototype"}


def test_persona_kmeans(conn):
    uid = 1
    for _ in range(4):
        _add_user(conn, uid, "student", [("food", 400)] * 4 + [("transport", 50), ("other", 50)])
        uid += 1
    for _ in range(4):
        _add_user(conn, uid, "professional", [("rent", 900)] * 3 + [("food", 100), ("utilities", 100)])
        uid += 1
    assert assign_persona(conn, 1) == {**PERSONAS_VIEW("food_lover"), "method": "kmeans"}
    assert assign_persona(conn, 8)["key"] == "rent_heavy"
    assert assign_persona(conn, 8)["method"] == "kmeans"


def PERSONAS_VIEW(key):
    p = PERSONAS[key]
    return {"key": key, "label": p["label"], "description": p["description"]}


# ---------- tips ----------

def test_tips():
    assert len(TIPS) >= 20
    ids = [t["id"] for t in TIPS]
    assert len(ids) == len(set(ids))
    allowed = set(CATEGORIES) | {"general", "savings"}
    assert all(t["category"] in allowed and t["title"] and t["message"] for t in TIPS)
    assert {t["category"] for t in TIPS} >= set(CATEGORIES)
    assert get_tip(ids[0])["id"] == ids[0] and get_tip("nope") is None


# ---------- bandit ----------

def test_build_context_layout():
    x = build_context([], [], "student", today=TODAY)
    assert x.shape == (CONTEXT_DIM,)
    assert x[0] == 1 and x[1:7].sum() == 0 and x[9] == 1
    rows = steady_history() + [exp(TODAY, "food", 900)]
    budgets = [{"category": "food", "amount": 500, "period": "monthly"}]
    x = build_context(rows, budgets, "professional", today=TODAY)
    assert x[1:7].sum() == pytest.approx(1)
    assert x[8] == 1 and x[9] == 0 and x[10] == 1 and x[11] == 1
    assert 0 <= x[7] <= 1 and x[12] == pytest.approx(18 / 30)


def test_linucb_learns_and_persists(conn):
    x = build_context(steady_history(), [], "student", today=TODAY)
    rec = LinUCBTipRecommender(conn, alpha=0.5)
    first = rec.recommend(x, k=3)
    assert len(first) == 3 and all(set(r) == {"tip_id", "score"} for r in first)
    # deterministic ties: untrained arms come back in TIPS order
    assert [r["tip_id"] for r in first] == [t["id"] for t in TIPS[:3]]

    target = "savings_round_up"
    for _ in range(10):
        rec.update(target, x, 1.0)
    for r in first:
        rec.update(r["tip_id"], x, 0.0)
    rec2 = LinUCBTipRecommender(conn, alpha=0.5)  # reload from SQLite
    assert rec2.recommend(x, k=1)[0]["tip_id"] == target
    assert conn.execute("SELECT n FROM bandit_arms WHERE tip_id = ?", (target,)).fetchone()[0] == 10

    sub = rec2.recommend(x, k=5, candidate_ids=["food_mess_plan", "rent_negotiate"])
    assert [r["tip_id"] for r in sub] and len(sub) == 2


def test_record_feedback(conn):
    x = build_context([], [], "student", today=TODAY)
    record_feedback(conn, 7, "food_mess_plan", 1, x)
    record_feedback(conn, 7, "food_mess_plan", 0, x.tolist())
    rows = conn.execute("SELECT user_id, tip_id, reward, context FROM insight_feedback").fetchall()
    assert len(rows) == 2 and rows[0][:3] == (7, "food_mess_plan", 1.0)
    assert conn.execute("SELECT n FROM bandit_arms WHERE tip_id='food_mess_plan'").fetchone()[0] == 2


def test_init_tables_idempotent(conn):
    init_tables(conn)
    init_tables(conn)


# ---------- categorize ----------

@pytest.mark.parametrize("desc,cat", [
    ("Swiggy order - biryani", "food"),
    ("ZOMATO*1234", "food"),
    ("Uber ride to college", "transport"),
    ("metro card recharge", "transport"),
    ("Rapido bike", "transport"),
    ("PG rent November", "rent"),
    ("hostel fees", "rent"),
    ("Netflix subscription", "entertainment"),
    ("BookMyShow tickets", "entertainment"),
    ("Jio recharge 299", "utilities"),
    ("Airtel postpaid", "utilities"),
    ("electricity bill", "utilities"),
    ("Blinkit groceries", "food"),
    ("Zepto milk", "food"),
])
def test_categorize_keywords(desc, cat):
    r = suggest_category(desc)
    assert r["category"] == cat and r["method"] == "keyword"
    assert 0 < r["confidence"] <= 1


def test_categorize_no_substring_false_positive():
    assert suggest_category("upgrade laptop")["method"] == "default"


def test_categorize_llm_fallback():
    calls = []

    def fake_llm(text):
        calls.append(text)
        return " Entertainment\n"

    r = suggest_category("xyz random thing", llm_fallback=fake_llm)
    assert r == {"category": "entertainment", "confidence": 0.6, "method": "llm"}
    suggest_category("swiggy", llm_fallback=fake_llm)
    assert calls == ["xyz random thing"]  # not called when keyword matched

    assert suggest_category("xyz", llm_fallback=lambda t: "banana")["method"] == "default"

    def boom(t):
        raise RuntimeError("offline")
    assert suggest_category("xyz", llm_fallback=boom) == {"category": "other", "confidence": 0.2, "method": "default"}
    assert suggest_category("")["method"] == "default"
