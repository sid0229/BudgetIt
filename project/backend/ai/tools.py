"""Function-calling tools executed against SQLite for the session user.

The model only ever sees the declarations below; none of them has a user_id
parameter. execute_tool() receives the user_id from the Flask session and drops
any user_id the model might try to pass.
"""
import json
import math
from datetime import date, datetime, timedelta

CATEGORIES = ['food', 'transport', 'rent', 'entertainment', 'utilities', 'other']

MAX_TOOL_ROUNDS = 4

TOOL_DECLARATIONS = [
    {
        'name': 'get_spending_summary',
        'description': ("Total spending for the user between two dates (inclusive), with a per-category "
                        "breakdown, number of expenses, daily average and the largest expenses. Use this "
                        "for any question about how much the user spent."),
        'parameters': {
            'type': 'OBJECT',
            'properties': {
                'start_date': {'type': 'STRING', 'description': 'Start date YYYY-MM-DD (inclusive).'},
                'end_date': {'type': 'STRING', 'description': 'End date YYYY-MM-DD (inclusive).'},
                'category': {'type': 'STRING', 'enum': CATEGORIES,
                             'description': 'Optional single category filter.'},
            },
            'required': ['start_date', 'end_date'],
        },
    },
    {
        'name': 'get_budget_status',
        'description': ("Every budget the user has set with amount spent in the current period "
                        "(weekly = last 7 days, monthly = month to date), remaining amount and percent used."),
        'parameters': {'type': 'OBJECT', 'properties': {}},
    },
    {
        'name': 'get_goals',
        'description': 'The user\'s savings goals with target, saved amount, progress percent and days left.',
        'parameters': {'type': 'OBJECT', 'properties': {}},
    },
    {
        'name': 'get_recent_expenses',
        'description': 'Most recent expenses (newest first), optionally filtered by category.',
        'parameters': {
            'type': 'OBJECT',
            'properties': {
                'limit': {'type': 'INTEGER', 'description': 'How many expenses to return (1-50, default 10).'},
                'category': {'type': 'STRING', 'enum': CATEGORIES, 'description': 'Optional category filter.'},
            },
        },
    },
    {
        'name': 'forecast_month_end',
        'description': ("Projects this month's total spending at month end from the recent daily spending "
                        "rate, compares it with the monthly budget and returns the projected overrun and "
                        "the date the budget would be exceeded."),
        'parameters': {'type': 'OBJECT', 'properties': {}},
    },
    {
        'name': 'get_spending_anomalies',
        'description': ("Categories where this week's spending is unusually high compared with the user's "
                        "own recent weekly baseline (EWMA). Use for 'am I overspending?' / 'anything unusual?'."),
        'parameters': {'type': 'OBJECT', 'properties': {}},
    },
    {
        'name': 'plan_goal',
        'description': ("Deterministic savings plan for one goal: remaining amount, weeks left and the "
                        "weekly/monthly amount needed to hit it on time, compared with current spending."),
        'parameters': {
            'type': 'OBJECT',
            'properties': {
                'goal_title_or_id': {'type': 'STRING',
                                     'description': 'Goal id or (part of) the goal title, e.g. "laptop".'},
            },
            'required': ['goal_title_or_id'],
        },
    },
]

TOOL_NAMES = [d['name'] for d in TOOL_DECLARATIONS]


# ---------------------------------------------------------------- data access

def load_expenses(conn, user_id):
    rows = conn.execute(
        'SELECT id, amount, category, description, date FROM expenses WHERE user_id = ? ORDER BY date DESC, id DESC',
        (user_id,)
    ).fetchall()
    return [{
        'id': row['id'],
        'amount': float(row['amount'] or 0),
        'category': row['category'],
        'description': row['description'] or '',
        'date': str(row['date'])[:10],
    } for row in rows]


def load_budgets(conn, user_id):
    """One budget per category (latest row wins; the budgets table has no unique key)."""
    rows = conn.execute(
        'SELECT category, amount, period FROM budgets WHERE user_id = ? ORDER BY id',
        (user_id,)
    ).fetchall()
    latest = {}
    for row in rows:
        latest[row['category']] = {
            'category': row['category'],
            'amount': float(row['amount'] or 0),
            'period': row['period'],
        }
    return list(latest.values())


def load_goals(conn, user_id):
    rows = conn.execute(
        'SELECT id, title, target_amount, saved_amount, target_date FROM goals WHERE user_id = ? ORDER BY id',
        (user_id,)
    ).fetchall()
    return [{
        'id': row['id'],
        'title': row['title'],
        'target_amount': float(row['target_amount'] or 0),
        'saved_amount': float(row['saved_amount'] or 0),
        'target_date': str(row['target_date'])[:10],
    } for row in rows]


def _parse_date(value, default):
    if not value:
        return default
    try:
        return datetime.strptime(str(value)[:10], '%Y-%m-%d').date()
    except ValueError:
        return default


def _r(x):
    return round(float(x), 2)


# ---------------------------------------------------------------- tools

def get_spending_summary(conn, user_id, start_date=None, end_date=None, category=None, today=None):
    today = today or date.today()
    start = _parse_date(start_date, today.replace(day=1))
    end = _parse_date(end_date, today)
    if end < start:
        start, end = end, start
    if category not in CATEGORIES:
        category = None

    rows = [e for e in load_expenses(conn, user_id)
            if start.isoformat() <= e['date'] <= end.isoformat()
            and (category is None or e['category'] == category)]
    by_category = {}
    for e in rows:
        by_category[e['category']] = by_category.get(e['category'], 0.0) + e['amount']
    total = sum(e['amount'] for e in rows)
    days = (end - start).days + 1
    largest = sorted(rows, key=lambda e: e['amount'], reverse=True)[:3]
    return {
        'start_date': start.isoformat(),
        'end_date': end.isoformat(),
        'category': category,
        'total': _r(total),
        'count': len(rows),
        'daily_average': _r(total / days) if days > 0 else 0.0,
        'by_category': {k: _r(v) for k, v in sorted(by_category.items(), key=lambda kv: -kv[1])},
        'largest_expenses': [{'amount': _r(e['amount']), 'category': e['category'],
                              'description': e['description'], 'date': e['date']} for e in largest],
        'currency': 'INR',
    }


def get_budget_status(conn, user_id, today=None):
    today = today or date.today()
    expenses = load_expenses(conn, user_id)
    week_start = (today - timedelta(days=6)).isoformat()
    month_start = today.replace(day=1).isoformat()
    result = []
    for b in load_budgets(conn, user_id):
        since = week_start if b['period'] == 'weekly' else month_start
        spent = sum(e['amount'] for e in expenses
                    if e['category'] == b['category'] and since <= e['date'] <= today.isoformat())
        pct = (spent / b['amount'] * 100) if b['amount'] > 0 else 0.0
        status = 'over' if pct > 100 else ('near_limit' if pct >= 80 else 'ok')
        result.append({
            'category': b['category'],
            'period': b['period'],
            'window': 'last 7 days' if b['period'] == 'weekly' else 'this month so far',
            'budget': _r(b['amount']),
            'spent': _r(spent),
            'remaining': _r(b['amount'] - spent),
            'percent_used': round(pct, 1),
            'status': status,
        })
    return {'budgets': result, 'has_budgets': bool(result), 'currency': 'INR'}


def get_goals(conn, user_id, today=None):
    today = today or date.today()
    goals = []
    for g in load_goals(conn, user_id):
        target = _parse_date(g['target_date'], today)
        progress = (g['saved_amount'] / g['target_amount'] * 100) if g['target_amount'] > 0 else 0.0
        goals.append({
            'id': g['id'],
            'title': g['title'],
            'target_amount': _r(g['target_amount']),
            'saved_amount': _r(g['saved_amount']),
            'remaining': _r(max(0.0, g['target_amount'] - g['saved_amount'])),
            'progress_percent': round(progress, 1),
            'target_date': g['target_date'],
            'days_left': (target - today).days,
        })
    return {'goals': goals, 'count': len(goals), 'currency': 'INR'}


def get_recent_expenses(conn, user_id, limit=10, category=None):
    try:
        limit = int(limit or 10)
    except (TypeError, ValueError):
        limit = 10
    limit = max(1, min(50, limit))
    if category not in CATEGORIES:
        category = None
    rows = [e for e in load_expenses(conn, user_id) if category is None or e['category'] == category]
    return {'expenses': [{k: e[k] for k in ('amount', 'category', 'description', 'date')}
                         for e in rows[:limit]],
            'count': min(limit, len(rows)), 'currency': 'INR'}


def forecast_month_end(conn, user_id, today=None):
    from personalization import stats
    return stats.forecast_month_end(load_expenses(conn, user_id), load_budgets(conn, user_id), today=today)


def get_spending_anomalies(conn, user_id, today=None):
    from personalization import stats
    anomalies = stats.detect_anomalies(load_expenses(conn, user_id), today=today)
    return {'anomalies': anomalies, 'count': len(anomalies)}


def _find_goal(goals, key):
    key = str(key or '').strip().lower()
    if not goals:
        return None
    if key.isdigit():
        for g in goals:
            if g['id'] == int(key):
                return g
    if key:
        for g in goals:
            if key == g['title'].lower():
                return g
        for g in goals:
            if key in g['title'].lower() or g['title'].lower() in key:
                return g
        words = [w for w in key.split() if len(w) > 2]
        for g in goals:
            if any(w in g['title'].lower() for w in words):
                return g
    return None


def plan_goal(conn, user_id, goal_title_or_id=None, today=None):
    today = today or date.today()
    goals = load_goals(conn, user_id)
    goal = _find_goal(goals, goal_title_or_id)
    if goal is None:
        return {'found': False, 'available_goals': [g['title'] for g in goals],
                'message': 'No matching goal found.'}

    remaining = max(0.0, goal['target_amount'] - goal['saved_amount'])
    target = _parse_date(goal['target_date'], today)
    days_left = (target - today).days
    weeks_left = max(1, math.ceil(days_left / 7)) if days_left > 0 else 0
    weekly_needed = remaining / weeks_left if weeks_left else remaining
    months_left = max(1, math.ceil(days_left / 30.44)) if days_left > 0 else 0
    monthly_needed = remaining / months_left if months_left else remaining

    # Compare with the user's average weekly spending over the last 28 days.
    since = (today - timedelta(days=27)).isoformat()
    recent = [e for e in load_expenses(conn, user_id) if since <= e['date'] <= today.isoformat()]
    avg_weekly_spend = sum(e['amount'] for e in recent) / 4.0
    share = (weekly_needed / avg_weekly_spend * 100) if avg_weekly_spend > 0 else None

    return {
        'found': True,
        'goal': goal['title'],
        'goal_id': goal['id'],
        'target_amount': _r(goal['target_amount']),
        'saved_amount': _r(goal['saved_amount']),
        'remaining': _r(remaining),
        'target_date': goal['target_date'],
        'days_left': days_left,
        'weeks_left': weeks_left,
        'weekly_needed': _r(weekly_needed),
        'monthly_needed': _r(monthly_needed),
        'average_weekly_spend_last_4_weeks': _r(avg_weekly_spend),
        'weekly_needed_as_percent_of_spend': round(share, 1) if share is not None else None,
        'status': 'completed' if remaining <= 0 else ('overdue' if days_left <= 0 else 'in_progress'),
        'currency': 'INR',
    }


_IMPLEMENTATIONS = {
    'get_spending_summary': get_spending_summary,
    'get_budget_status': get_budget_status,
    'get_goals': get_goals,
    'get_recent_expenses': get_recent_expenses,
    'forecast_month_end': forecast_month_end,
    'get_spending_anomalies': get_spending_anomalies,
    'plan_goal': plan_goal,
}

_ALLOWED_ARGS = {
    d['name']: set(d['parameters'].get('properties', {}).keys()) for d in TOOL_DECLARATIONS
}


def execute_tool(conn, user_id, name, args=None):
    """Run a tool for user_id (from the session). Never raises; errors go back to the model."""
    fn = _IMPLEMENTATIONS.get(name)
    if fn is None:
        return {'error': 'Unknown tool: %s' % name}
    allowed = _ALLOWED_ARGS.get(name, set())
    clean = {k: v for k, v in (args or {}).items() if k in allowed}  # drops user_id & friends
    try:
        result = fn(conn, user_id, **clean)
        # Make sure everything is JSON-serialisable for the function response.
        return json.loads(json.dumps(result, default=str))
    except Exception as exc:  # pragma: no cover - defensive
        return {'error': '%s failed: %s' % (name, exc)}
