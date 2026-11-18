"""Spending statistics: EWMA weekly baselines, anomaly detection, month-end forecast."""
import calendar
import math
from datetime import date, datetime, timedelta

import numpy as np

from . import CATEGORIES


def _to_date(value):
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return datetime.strptime(str(value)[:10], "%Y-%m-%d").date()


def _parse(expenses):
    """Return [(date, category, amount)] skipping malformed rows."""
    rows = []
    for e in expenses or []:
        try:
            rows.append((_to_date(e["date"]), str(e.get("category") or "other"), float(e["amount"])))
        except (KeyError, ValueError, TypeError):
            continue
    return rows


def _week_start(d):
    return d - timedelta(days=d.weekday())  # Monday


def _ewma(values, alpha):
    if len(values) == 0:
        return 0.0
    s = float(values[0])
    for x in values[1:]:
        s = alpha * float(x) + (1 - alpha) * s
    return s


def _all_categories(rows):
    cats = list(CATEGORIES)
    for _, c, _ in rows:
        if c not in cats:
            cats.append(c)
    return cats


def category_baselines(expenses, today=None, alpha=0.3, weeks=8):
    """EWMA of weekly totals per category over prior full weeks (current week excluded).

    Weeks start on Monday. The window starts at the later of `weeks` weeks ago and
    the week of the user's first expense, so new users are not diluted by zero weeks.
    """
    today = _to_date(today or date.today())
    rows = _parse(expenses)
    cats = _all_categories(rows)
    result = {c: {"ewma_weekly": 0.0, "std_weekly": 0.0, "weeks_observed": 0} for c in cats}

    current = _week_start(today)
    past = [r for r in rows if r[0] < current]
    if not past:
        return result

    first_week = _week_start(min(r[0] for r in past))
    start = max(current - timedelta(weeks=weeks), first_week)
    n_weeks = (current - start).days // 7
    if n_weeks <= 0:
        return result

    totals = {c: np.zeros(n_weeks) for c in cats}
    for d, c, amt in past:
        if d < start:
            continue
        totals[c][(d - start).days // 7] += amt

    for c in cats:
        series = totals[c]
        result[c] = {
            "ewma_weekly": round(_ewma(series, alpha), 2),
            "std_weekly": round(float(np.std(series)), 2),
            "weeks_observed": int(n_weeks),
        }
    return result


def detect_anomalies(expenses, today=None, z_threshold=2.0, min_ratio=1.5):
    """Categories whose spend this week is unusually high vs their EWMA baseline."""
    today = _to_date(today or date.today())
    rows = _parse(expenses)
    baselines = category_baselines(rows_to_dicts(rows), today=today)

    week_start = _week_start(today)
    this_week = {}
    for d, c, amt in rows:
        if week_start <= d <= today:
            this_week[c] = this_week.get(c, 0.0) + amt

    anomalies = []
    for c, spent in this_week.items():
        base = baselines.get(c)
        if not base or base["weeks_observed"] < 2 or spent <= 0:
            continue
        baseline = base["ewma_weekly"]
        # Floor the spread so a perfectly flat history doesn't make every rupee an anomaly.
        spread = max(base["std_weekly"], 0.25 * baseline, 50.0)
        z = (spent - baseline) / spread
        ratio = spent / baseline if baseline > 0 else float("inf")
        if z >= z_threshold and ratio >= min_ratio:
            anomalies.append({
                "category": c,
                "this_week": round(spent, 2),
                "baseline": round(baseline, 2),
                "ratio": round(ratio, 2) if math.isfinite(ratio) else 99.0,
                "z": round(z, 2),
            })
    anomalies.sort(key=lambda a: (-a["z"], -a["ratio"], a["category"]))
    return anomalies


def rows_to_dicts(rows):
    return [{"date": d.isoformat(), "category": c, "amount": a} for d, c, a in rows]


def monthly_budget_amount(budget, days_in_month):
    """Convert a budget row to a monthly amount (weekly x days_in_month/7)."""
    amount = float(budget.get("amount") or 0)
    if budget.get("period") == "weekly":
        return amount * days_in_month / 7.0
    return amount


def forecast_month_end(expenses, budgets, today=None, alpha=0.1, lookback_days=28):
    """Project month-end spend: spent so far + EWMA daily rate x remaining days.

    Rent is treated as a lump sum: if paid this month it is not projected further,
    otherwise last month's rent (if any) is assumed to still be due.
    """
    today = _to_date(today or date.today())
    rows = _parse(expenses)
    cats = _all_categories(rows)
    dim = calendar.monthrange(today.year, today.month)[1]
    month_start = today.replace(day=1)
    remaining = dim - today.day
    prev_month_end = month_start - timedelta(days=1)
    prev_month_start = prev_month_end.replace(day=1)

    budget_by_cat = {}
    for b in budgets or []:
        cat = str(b.get("category") or "other")
        budget_by_cat[cat] = budget_by_cat.get(cat, 0.0) + monthly_budget_amount(b, dim)
    for cat in budget_by_cat:
        if cat not in cats:
            cats.append(cat)

    upto_today = [r for r in rows if r[0] <= today]
    first_day = min((r[0] for r in upto_today), default=None)
    window_start = today - timedelta(days=lookback_days - 1)
    if first_day and first_day > window_start:
        window_start = first_day
    n_days = (today - window_start).days + 1 if first_day else 0

    by_category = {}
    spent_total = 0.0
    projected_total = 0.0
    daily_rate_total = 0.0
    for c in cats:
        spent = sum(a for d, cc, a in upto_today if cc == c and d >= month_start)
        if c == "rent":
            if spent > 0:
                projected = spent
            else:
                projected = sum(a for d, cc, a in rows if cc == c and prev_month_start <= d <= prev_month_end)
        else:
            rate = 0.0
            if n_days > 0:
                daily = np.zeros(n_days)
                for d, cc, a in upto_today:
                    if cc == c and d >= window_start:
                        daily[(d - window_start).days] += a
                rate = _ewma(daily, alpha) if n_days > 1 else float(daily[0])
                # Blend with the plain mean so one quiet day doesn't zero the rate.
                rate = 0.5 * rate + 0.5 * float(daily.mean())
            daily_rate_total += rate
            projected = spent + rate * remaining
        budget = budget_by_cat.get(c)
        by_category[c] = {
            "spent": round(spent, 2),
            "projected": round(projected, 2),
            "budget": round(budget, 2) if budget is not None else None,
        }
        spent_total += spent
        projected_total += projected

    monthly_budget = round(sum(budget_by_cat.values()), 2) if budget_by_cat else None
    overrun = max(0.0, projected_total - monthly_budget) if monthly_budget is not None else 0.0

    overrun_date = None
    if monthly_budget is not None and projected_total > monthly_budget:
        if spent_total >= monthly_budget:
            # Day the actual cumulative spend crossed the budget.
            cum = 0.0
            for d in sorted({r[0] for r in upto_today if r[0] >= month_start}):
                cum += sum(a for dd, _, a in upto_today if dd == d)
                if cum >= monthly_budget:
                    overrun_date = d.isoformat()
                    break
        else:
            pending_rent = by_category.get("rent", {}).get("projected", 0) - by_category.get("rent", {}).get("spent", 0)
            gap = monthly_budget - spent_total - pending_rent
            if gap <= 0:
                days = 1
            elif daily_rate_total > 0:
                days = math.ceil(gap / daily_rate_total)
            else:
                days = remaining
            days = max(1, min(days, remaining)) if remaining > 0 else 0
            overrun_date = (today + timedelta(days=days)).isoformat()

    return {
        "month": today.strftime("%Y-%m"),
        "spent_so_far": round(spent_total, 2),
        "projected_total": round(projected_total, 2),
        "monthly_budget": monthly_budget,
        "projected_overrun": round(overrun, 2),
        "overrun_date": overrun_date,
        "by_category": by_category,
    }
