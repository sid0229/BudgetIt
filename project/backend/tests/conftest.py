"""Shared fixtures: temp SQLite DB, Flask test client, logged-in user with seeded data.

No test may touch the network: GEMINI_API_KEY is removed for every test (after
app.py has loaded backend/.env) and the RAG index is reset so it stays BM25-only.
"""
import os
import sys
from datetime import date, timedelta

import pytest

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

# Import everything that calls load_dotenv() up front, so the key from
# backend/.env is loaded once here and then removed per test below.
import app as _app_module  # noqa: E402,F401
try:
    from rag import retriever as _retriever  # noqa: E402,F401
except Exception:  # pragma: no cover
    _retriever = None


@pytest.fixture(autouse=True)
def _no_network(monkeypatch):
    monkeypatch.delenv('GEMINI_API_KEY', raising=False)
    try:
        from rag import retriever
        retriever.reset_index()
    except Exception:
        pass
    try:
        from ai import insights
        insights.clear_cache()
    except Exception:
        pass
    yield
    try:
        from rag import retriever
        retriever.reset_index()
    except Exception:
        pass


@pytest.fixture
def app(tmp_path, monkeypatch):
    import app as app_module  # loads .env; the autouse fixture already removed the key

    monkeypatch.delenv('GEMINI_API_KEY', raising=False)
    flask_app = app_module.app
    monkeypatch.setitem(flask_app.config, 'DATABASE', str(tmp_path / 'test.db'))
    flask_app.config['TESTING'] = True
    app_module.init_db()
    return flask_app


@pytest.fixture
def client(app):
    return app.test_client()


def seed_expenses(client, today=None):
    """~6 weeks of steady student spending plus a food spike this week."""
    today = today or date.today()
    monday = today - timedelta(days=today.weekday())
    rows = []
    for w in range(1, 7):
        start = monday - timedelta(weeks=w)
        rows += [
            (start, 'food', 150, 'Mess dinner'),
            (start + timedelta(days=2), 'food', 200, 'Swiggy'),
            (start + timedelta(days=1), 'transport', 120, 'Metro card'),
            (start + timedelta(days=4), 'entertainment', 250, 'Movie'),
        ]
    # spike this week (always on/before today)
    rows += [
        (monday, 'food', 900, 'Zomato party order'),
        (today, 'food', 700, 'Restaurant'),
        (today, 'transport', 80, 'Auto'),
    ]
    for d, cat, amount, desc in rows:
        resp = client.post('/api/expenses', json={'amount': amount, 'category': cat,
                                                  'description': desc, 'date': d.isoformat()})
        assert resp.status_code == 201
    return rows


@pytest.fixture
def logged_in(client):
    resp = client.post('/api/auth/signup', json={'name': 'Asha', 'email': 'asha@example.com',
                                                 'password': 'pw12345', 'userType': 'student'})
    assert resp.status_code == 201
    user_id = resp.get_json()['user']['id']
    seed_expenses(client)
    client.post('/api/budgets', json={'category': 'food', 'amount': 1000, 'period': 'weekly'})
    client.post('/api/budgets', json={'category': 'transport', 'amount': 2000, 'period': 'monthly'})
    target = (date.today() + timedelta(days=70)).isoformat()
    client.post('/api/goals', json={'title': 'New Laptop', 'targetAmount': 42000, 'targetDate': target})
    return {'client': client, 'user_id': user_id}


@pytest.fixture
def db_conn(app):
    import app as app_module
    conn = app_module.get_db_connection()
    yield conn
    conn.close()
