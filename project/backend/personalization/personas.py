"""Spending personas: prototype centroids + pure-numpy k-means over category shares."""
import numpy as np

from . import CATEGORIES

# Centroids are category shares in CATEGORIES order:
# food, transport, rent, entertainment, utilities, other
PERSONAS = {
    "food_lover": {
        "label": "Foodie",
        "description": "Food and eating out take the biggest slice of your spending.",
        "centroid": [0.50, 0.10, 0.15, 0.10, 0.05, 0.10],
    },
    "commuter": {
        "label": "Daily Commuter",
        "description": "Travel (cabs, autos, metro) is a large share of your spending.",
        "centroid": [0.20, 0.40, 0.15, 0.08, 0.07, 0.10],
    },
    "rent_heavy": {
        "label": "Rent-Focused",
        "description": "Rent or PG/hostel fees dominate your budget; small daily savings add up.",
        "centroid": [0.15, 0.08, 0.55, 0.07, 0.10, 0.05],
    },
    "entertainment_seeker": {
        "label": "Fun Seeker",
        "description": "Movies, subscriptions and outings are a big part of your spending.",
        "centroid": [0.20, 0.10, 0.15, 0.40, 0.05, 0.10],
    },
    "balanced_saver": {
        "label": "Balanced Spender",
        "description": "Your spending is spread evenly across categories.",
        "centroid": [0.25, 0.15, 0.25, 0.10, 0.12, 0.13],
    },
}

PERSONA_KEYS = list(PERSONAS.keys())
PROTOTYPES = np.array([PERSONAS[k]["centroid"] for k in PERSONA_KEYS], dtype=float)

COLD_START = {"student": "food_lover", "professional": "balanced_saver"}

MIN_USERS_FOR_KMEANS = 8
MIN_EXPENSES_PER_USER = 5
MIN_EXPENSES_FOR_PERSONA = 3


def category_share_vector(expenses):
    """Share of total spend per category (len 6, sums to 1; zeros if no spend)."""
    v = np.zeros(len(CATEGORIES))
    for e in expenses or []:
        try:
            amt = float(e["amount"])
        except (KeyError, ValueError, TypeError):
            continue
        cat = e.get("category")
        idx = CATEGORIES.index(cat) if cat in CATEGORIES else CATEGORIES.index("other")
        v[idx] += max(amt, 0.0)
    total = v.sum()
    return v / total if total > 0 else v


def kmeans(X, k, init=None, iters=50, seed=0):
    """Lloyd's k-means. Returns (centroids [k,d], labels [n]). Empty clusters keep their centroid."""
    X = np.asarray(X, dtype=float)
    if init is not None:
        centroids = np.asarray(init, dtype=float).copy()
        k = centroids.shape[0]
    else:
        rng = np.random.default_rng(seed)
        idx = rng.choice(len(X), size=min(k, len(X)), replace=False)
        centroids = X[idx].copy()
    labels = np.zeros(len(X), dtype=int)
    if len(X) == 0:
        return centroids, labels
    for i in range(iters):
        dists = ((X[:, None, :] - centroids[None, :, :]) ** 2).sum(axis=2)
        new_labels = dists.argmin(axis=1)
        new_centroids = centroids.copy()
        for j in range(len(centroids)):
            members = X[new_labels == j]
            if len(members):
                new_centroids[j] = members.mean(axis=0)
        converged = i > 0 and np.array_equal(new_labels, labels) and np.allclose(new_centroids, centroids)
        labels, centroids = new_labels, new_centroids
        if converged:
            break
    return centroids, labels


def nearest_prototype(vec):
    d = ((PROTOTYPES - np.asarray(vec, dtype=float)) ** 2).sum(axis=1)
    return PERSONA_KEYS[int(d.argmin())]


def _persona(key, method):
    p = PERSONAS[key]
    return {"key": key, "label": p["label"], "description": p["description"], "method": method}


def _user_expenses(conn, user_id):
    rows = conn.execute(
        "SELECT amount, category FROM expenses WHERE user_id = ?", (user_id,)
    ).fetchall()
    return [{"amount": r[0], "category": r[1]} for r in rows]


def _user_type(conn, user_id):
    try:
        row = conn.execute("SELECT user_type FROM users WHERE id = ?", (user_id,)).fetchone()
        return row[0] if row else "student"
    except Exception:
        return "student"


def assign_persona(conn, user_id):
    """Persona for a user: k-means across users when enough data, else nearest prototype."""
    expenses = _user_expenses(conn, user_id)
    vec = category_share_vector(expenses)
    if len(expenses) < MIN_EXPENSES_FOR_PERSONA or vec.sum() == 0:
        key = COLD_START.get(_user_type(conn, user_id), "balanced_saver")
        return _persona(key, "cold_start")

    eligible = conn.execute(
        "SELECT user_id FROM expenses GROUP BY user_id HAVING COUNT(*) >= ? ORDER BY user_id",
        (MIN_EXPENSES_PER_USER,),
    ).fetchall()
    user_ids = [r[0] for r in eligible]
    if len(user_ids) >= MIN_USERS_FOR_KMEANS and user_id in user_ids:
        X = np.array([category_share_vector(_user_expenses(conn, uid)) for uid in user_ids])
        centroids, labels = kmeans(X, len(PROTOTYPES), init=PROTOTYPES)
        cluster = labels[user_ids.index(user_id)]
        return _persona(nearest_prototype(centroids[cluster]), "kmeans")

    return _persona(nearest_prototype(vec), "prototype")
