"""Dashboard insights pipeline.

1. Compute facts from the user's data: month-end forecast, anomalies, persona,
   budget status, goals (personalization.stats / personas + ai.tools).
2. LinUCB contextual bandit picks the top 3 tips for this user's context.
3. Gemini (JSON schema output) writes 3-5 insights grounded ONLY on those facts
   and tips; on any problem we fall back to deterministic rule insights built
   from the same facts.
4. Result cached per user for 10 minutes; invalidated on expense/budget/goal writes.
"""
import json
import threading
import time
from datetime import date

from ai import llm, prompts, tools
from ai.chat import fmt_inr

CACHE_TTL_SECONDS = 600
_cache = {}            # user_id -> {"at": float, "payload": dict, "context": list|None}
_cache_lock = threading.Lock()

DEFAULT_PERSONA = {
    'key': 'getting_started',
    'label': 'Getting Started',
    'description': 'Log a few expenses so BudgetIt can learn your spending style.',
    'method': 'cold_start',
}


# ---------------------------------------------------------------- cache

def invalidate(user_id):
    with _cache_lock:
        _cache.pop(user_id, None)


def clear_cache():
    with _cache_lock:
        _cache.clear()


def _cached(user_id):
    with _cache_lock:
        entry = _cache.get(user_id)
        if entry and time.time() - entry['at'] < CACHE_TTL_SECONDS:
            return entry
    return None


# ---------------------------------------------------------------- facts

def _context(expenses, budgets, user_type, today):
    try:
        from personalization.bandit import build_context
        return build_context(expenses, budgets, user_type, today=today)
    except Exception:
        return None


def _pick_tips(conn, context, expenses, k=3):
    """LinUCB top-k tips -> list of {"id","category","title","message"}."""
    try:
        from personalization.bandit import LinUCBTipRecommender
        from personalization.tips import get_tip
        if context is not None:
            recs = LinUCBTipRecommender(conn).recommend(context, k=k)
            picked = [get_tip(r['tip_id']) for r in recs]
            picked = [t for t in picked if t]
            if picked:
                return picked
    except Exception:
        pass
    # Fallback: tips for the user's top spending categories.
    try:
        from personalization.tips import TIPS
    except Exception:
        return []
    totals = {}
    for e in expenses:
        totals[e['category']] = totals.get(e['category'], 0.0) + e['amount']
    order = sorted(totals, key=lambda c: -totals[c]) + ['general', 'savings']
    picked = []
    for cat in order:
        for tip in TIPS:
            if tip['category'] == cat and tip not in picked:
                picked.append(tip)
                break
        if len(picked) >= k:
            break
    return picked


def compute_facts(conn, user, today=None):
    today = today or date.today()
    uid = user['id']
    expenses = tools.load_expenses(conn, uid)
    budgets = tools.load_budgets(conn, uid)

    forecast, anomalies, persona = None, [], None
    try:
        from personalization import stats
        forecast = stats.forecast_month_end(expenses, budgets, today=today)
        anomalies = stats.detect_anomalies(expenses, today=today)
    except Exception:
        pass
    try:
        from personalization.personas import assign_persona
        persona = assign_persona(conn, uid)
    except Exception:
        persona = None

    context = _context(expenses, budgets, user.get('user_type') or 'student', today)
    tips = _pick_tips(conn, context, expenses, k=3)
    month_start = today.replace(day=1).isoformat()

    return {
        'expenses': expenses,
        'context': context,
        'forecast': json.loads(json.dumps(forecast, default=float)) if forecast else None,
        'anomalies': json.loads(json.dumps(anomalies, default=float)) if anomalies else [],
        'persona': persona or dict(DEFAULT_PERSONA),
        'budgets': tools.get_budget_status(conn, uid, today=today)['budgets'],
        'goals': tools.get_goals(conn, uid, today=today)['goals'],
        'month_summary': tools.get_spending_summary(conn, uid, month_start, today.isoformat(), today=today),
        'tips': tips,
        'today': today,
    }


def _round_facts(value):
    """Whole rupees for amounts, 1 decimal for small ratios, so the LLM doesn't echo paise."""
    if isinstance(value, dict):
        return {k: _round_facts(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_round_facts(v) for v in value]
    if isinstance(value, float):
        return int(round(value)) if abs(value) >= 10 else round(value, 1)
    return value


def _facts_for_prompt(user, f):
    return _round_facts(_raw_facts_for_prompt(user, f))


def _raw_facts_for_prompt(user, f):
    ms = f['month_summary']
    return {
        'today': f['today'].isoformat(),
        'user_type': user.get('user_type') or 'student',
        'name': user.get('name') or '',
        'persona': f['persona'].get('label'),
        'expense_count_total': len(f['expenses']),
        'this_month': {'total': ms['total'], 'count': ms['count'], 'by_category': ms['by_category']},
        'forecast': f['forecast'],
        'anomalies': f['anomalies'][:3],
        'budgets': f['budgets'],
        'goals': [{k: g[k] for k in ('title', 'target_amount', 'saved_amount', 'remaining', 'progress_percent', 'days_left')}
                  for g in f['goals']],
        'tips': [{'id': t['id'], 'category': t.get('category'), 'title': t['title'], 'message': t['message']}
                 for t in f['tips']],
    }


# ---------------------------------------------------------------- LLM writer

def _validate_llm_insights(raw_items, tips):
    tip_ids = {t['id'] for t in tips}
    out = []
    for item in raw_items or []:
        if not isinstance(item, dict):
            continue
        title = str(item.get('title') or '').strip()
        message = str(item.get('message') or '').strip()
        if not title or not message:
            continue
        itype = item.get('type') if item.get('type') in prompts.INSIGHT_TYPES else 'info'
        tip_id = item.get('tip_id') if item.get('tip_id') in tip_ids else None
        action = item.get('action')
        action = str(action).strip() if action else None
        out.append({
            'id': ('tip-%s' % tip_id) if tip_id else 'llm-%d' % (len(out) + 1),
            'type': itype,
            'title': title[:80],
            'message': message[:400],
            'action': (action or None) and action[:160],
            'tip_id': tip_id,
        })
    # De-duplicate ids (same tip used twice)
    seen = set()
    for i, ins in enumerate(out):
        if ins['id'] in seen:
            ins['id'] = '%s-%d' % (ins['id'], i)
        seen.add(ins['id'])
    return out[:5]


def _llm_insights(user, f):
    result = llm.generate(
        [{'role': 'user', 'text': prompts.build_insights_prompt(_facts_for_prompt(user, f))}],
        system_instruction=prompts.INSIGHTS_SYSTEM_PROMPT,
        response_schema=prompts.INSIGHTS_SCHEMA,
        temperature=0.5,
    )
    data = json.loads(result.get('text') or '{}')
    items = _validate_llm_insights(data.get('insights'), f['tips'])
    if len(items) < 3:
        raise ValueError('LLM returned %d valid insights' % len(items))
    return items


# ---------------------------------------------------------------- rule writer

def rule_insights(user, f):
    out = []
    forecast = f['forecast'] or {}
    ms = f['month_summary']

    if not f['expenses']:
        out.append({'id': 'start-logging', 'type': 'info', 'title': 'Start logging expenses',
                    'message': 'Add your daily expenses (even small chai and auto rides) so BudgetIt can spot patterns and forecast your month.',
                    'action': 'Log today\'s expenses', 'tip_id': None})
    elif forecast.get('monthly_budget'):
        if (forecast.get('projected_overrun') or 0) > 0:
            when = (' around %s' % forecast['overrun_date']) if forecast.get('overrun_date') else ''
            out.append({'id': 'forecast', 'type': 'warning', 'title': 'Month-end budget at risk',
                        'message': 'At your current pace you will spend about %s this month, %s over your %s budget%s.' % (
                            fmt_inr(forecast['projected_total']), fmt_inr(forecast['projected_overrun']),
                            fmt_inr(forecast['monthly_budget']), when),
                        'action': 'Review your biggest category this week', 'tip_id': None})
        else:
            out.append({'id': 'forecast', 'type': 'success', 'title': 'On track this month',
                        'message': 'Projected month-end spend is %s, within your %s budget. Keep it up!' % (
                            fmt_inr(forecast.get('projected_total', 0)), fmt_inr(forecast['monthly_budget'])),
                        'action': None, 'tip_id': None})
    elif ms['count']:
        top = next(iter(ms['by_category'].items()), None)
        msg = 'You have spent %s so far this month' % fmt_inr(ms['total'])
        if top:
            msg += ', most of it on %s (%s)' % (top[0], fmt_inr(top[1]))
        if forecast.get('projected_total'):
            msg += ', heading for about %s by month end' % fmt_inr(forecast['projected_total'])
        out.append({'id': 'month-summary', 'type': 'info', 'title': 'This month so far', 'message': msg + '.',
                    'action': 'Set a monthly budget to track it', 'tip_id': None})

    if f['anomalies']:
        a = f['anomalies'][0]
        out.append({'id': 'anomaly-%s' % a['category'], 'type': 'warning',
                    'title': '%s spending spike' % a['category'].capitalize(),
                    'message': 'You spent %s on %s this week, %.1fx your usual %s.' % (
                        fmt_inr(a['this_week']), a['category'], a['ratio'], fmt_inr(a['baseline'])),
                    'action': 'Set a cap on %s for the rest of the week' % a['category'], 'tip_id': None})
    else:
        over = [b for b in f['budgets'] if b['status'] == 'over']
        if over:
            b = max(over, key=lambda x: x['percent_used'])
            out.append({'id': 'budget-%s' % b['category'], 'type': 'warning',
                        'title': '%s budget exceeded' % b['category'].capitalize(),
                        'message': 'You have used %s of your %s %s budget (%.0f%%).' % (
                            fmt_inr(b['spent']), fmt_inr(b['budget']), b['period'], b['percent_used']),
                        'action': None, 'tip_id': None})

    goals = sorted(f['goals'], key=lambda g: -g['progress_percent'])
    if goals:
        g = goals[0]
        if g['progress_percent'] >= 100:
            out.append({'id': 'goal-%s' % g['id'], 'type': 'celebration', 'title': '%s goal reached!' % g['title'][:40],
                        'message': 'You saved %s for "%s". Brilliant discipline!' % (fmt_inr(g['target_amount']), g['title']),
                        'action': 'Set your next goal', 'tip_id': None})
        elif g['progress_percent'] >= 50:
            out.append({'id': 'goal-%s' % g['id'], 'type': 'celebration', 'title': '%s is %.0f%% funded' % (g['title'][:40], g['progress_percent']),
                        'message': 'Only %s to go on "%s". Keep going!' % (fmt_inr(g['remaining']), g['title']),
                        'action': None, 'tip_id': None})

    tips = f['tips'][:2] if len(out) < 3 else f['tips'][:1]
    for t in tips:
        out.append({'id': 'tip-%s' % t['id'], 'type': 'info', 'title': t['title'], 'message': t['message'],
                    'action': None, 'tip_id': t['id']})

    # Pad up to 3 with remaining tips if needed.
    for t in f['tips']:
        if len(out) >= 3:
            break
        if not any(i.get('tip_id') == t['id'] for i in out):
            out.append({'id': 'tip-%s' % t['id'], 'type': 'info', 'title': t['title'], 'message': t['message'],
                        'action': None, 'tip_id': t['id']})
    return out[:5]


# ---------------------------------------------------------------- entry points

def generate_insights(conn, user, today=None, use_cache=True):
    uid = user['id']
    if use_cache:
        entry = _cached(uid)
        if entry:
            return entry['payload']

    f = compute_facts(conn, user, today=today)
    insights, generated_by = None, 'rules'
    if llm.is_configured():
        try:
            insights = _llm_insights(user, f)
            generated_by = 'llm'
        except Exception:
            insights = None
    if insights is None:
        insights = rule_insights(user, f)

    payload = {
        'insights': insights,
        'persona': f['persona'],
        'forecast': f['forecast'],
        'anomalies': f['anomalies'],
        'generated_by': generated_by,
    }
    context = f['context']
    with _cache_lock:
        _cache[uid] = {
            'at': time.time(),
            'payload': payload,
            'context': context.tolist() if hasattr(context, 'tolist') else context,
        }
    return payload


def record_feedback(conn, user, tip_id, reward):
    """Reward the bandit arm using the context the tip was shown in (cached), else the current one."""
    from personalization.bandit import record_feedback as bandit_record
    from personalization.tips import get_tip
    import numpy as np

    if not get_tip(tip_id):
        raise ValueError('unknown tip_id %s' % tip_id)

    entry = _cached(user['id'])
    context = entry['context'] if entry and entry.get('context') is not None else None
    if context is None:
        expenses = tools.load_expenses(conn, user['id'])
        budgets = tools.load_budgets(conn, user['id'])
        context = _context(expenses, budgets, user.get('user_type') or 'student', date.today())
    if context is None:
        raise RuntimeError('could not build bandit context')
    bandit_record(conn, user['id'], tip_id, float(reward), np.asarray(context, dtype=float))
