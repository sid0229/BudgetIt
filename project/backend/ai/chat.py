"""Chat orchestrator: context assembly (profile + memory + persona + RAG + history),
Gemini manual tool loop, and a genuinely useful rule-based fallback.
"""
import re
from datetime import date, timedelta

from ai import llm, memory, prompts, tools

OFFLINE_NOTE = "(The full AI assistant is offline right now, so this is a quick answer straight from your data.)"
OFFLINE_NOTE_KB = "(The full AI assistant is offline right now, so this is a quick answer from the BudgetIt knowledge base.)"


# ---------------------------------------------------------------- helpers

def fmt_inr(amount):
    """₹ with Indian digit grouping, whole rupees: 125000 -> ₹1,25,000."""
    try:
        value = float(amount)
    except (TypeError, ValueError):
        return '₹0'
    neg = value < 0
    s = str(int(round(abs(value))))
    if len(s) > 3:
        head, tail = s[:-3], s[-3:]
        groups = []
        while len(head) > 2:
            groups.insert(0, head[-2:])
            head = head[:-2]
        if head:
            groups.insert(0, head)
        s = ','.join(groups) + ',' + tail
    return ('-₹' if neg else '₹') + s


def _retrieve(message, k=4):
    try:
        from rag.retriever import retrieve
        return list(retrieve(message, k=k) or [])
    except Exception:
        return []


def _persona(conn, user_id):
    try:
        from personalization.personas import assign_persona
        return assign_persona(conn, user_id)
    except Exception:
        return None


def _sources_from_citations(text, chunks):
    """Map [n] citations in the answer to their chunks (deduped, in citation order)."""
    seen, sources = set(), []
    numbers = []
    for match in re.finditer(r'\[(\d+(?:\s*[,\-\u2013]\s*\d+)*)\]', text or ''):  # [1], [1, 2], [1-3]
        for a, b in re.findall(r'(\d+)(?:\s*[\-\u2013]\s*(\d+))?', match.group(1)):
            lo, hi = int(a), int(b or a)
            numbers.extend(range(lo, min(hi, lo + 10) + 1))
    for n in numbers:
        idx = n - 1
        if 0 <= idx < len(chunks):
            c = chunks[idx]
            key = (c.get('title'), c.get('source'))
            if key not in seen:
                seen.add(key)
                sources.append({'title': c.get('title', ''), 'source': c.get('source', '')})
    return sources


# ---------------------------------------------------------------- LLM path

def _llm_answer(conn, user, message, history, chunks, today):
    system = prompts.build_chat_system_prompt(
        user, today,
        persona=_persona(conn, user['id']),
        memory_summary=memory.get_summary(conn, user['id']),
        knowledge=chunks,
    )
    messages = list(history) + [{'role': 'user', 'text': message}]
    tools_used = []
    text = ''

    for _ in range(tools.MAX_TOOL_ROUNDS):
        result = llm.generate(messages, system_instruction=system, tools=tools.TOOL_DECLARATIONS)
        calls = result.get('function_calls') or []
        if not calls:
            text = result.get('text') or ''
            break
        messages.append({'role': 'model', 'raw': result.get('raw'), 'function_calls': calls})
        responses = []
        for call in calls:
            name = call.get('name')
            # user_id always comes from the session, never from the model.
            output = tools.execute_tool(conn, user['id'], name, call.get('args') or {})
            if name not in tools_used:
                tools_used.append(name)
            responses.append({'name': name, 'response': {'result': output}, 'id': call.get('id')})
        messages.append({'role': 'tool', 'responses': responses})
    else:
        # Tool budget exhausted: force a text answer from what we have.
        result = llm.generate(messages, system_instruction=system, tools=tools.TOOL_DECLARATIONS, tool_mode='NONE')
        text = result.get('text') or ''

    text = text.strip()
    if not text:
        raise RuntimeError('empty LLM response')
    return {
        'response': text,
        'sources': _sources_from_citations(text, chunks),
        'tools_used': tools_used,
        'generated_by': 'llm',
    }


# ---------------------------------------------------------------- fallback path

CATEGORY_KEYWORDS = {
    'food': ['food', 'eat', 'eating', 'meal', 'swiggy', 'zomato', 'grocer', 'restaurant', 'canteen', 'mess', 'snack', 'coffee', 'khana'],
    'transport': ['transport', 'travel', 'uber', 'ola', 'rapido', 'metro', 'cab', 'auto', 'bus', 'fuel', 'petrol', 'commute'],
    'rent': ['rent', ' pg', 'hostel', 'flat', 'room'],
    'entertainment': ['entertainment', 'movie', 'netflix', 'spotify', 'fun', 'party', 'game', 'outing', 'ott'],
    'utilities': ['utilit', 'bill', 'electric', 'recharge', 'wifi', 'internet', 'phone', 'mobile', 'gas', 'water'],
}

INTENT_KEYWORDS = [
    ('anomaly', ['unusual', 'anomal', 'spike', 'weird', 'strange', 'more than usual', 'overspend', 'over spend', 'suspicious']),
    ('forecast', ['forecast', 'month end', 'month-end', 'end of the month', 'end of month', 'predict', 'project', 'on track', 'will i', 'stay within']),
    ('budget', ['budget', 'limit', 'over budget', 'left to spend', 'remaining']),
    ('goal', ['goal', 'save for', 'saving for', 'savings plan', 'how much should i save', 'how much to save', 'laptop', 'trip', 'target']),
    ('recent', ['recent', 'latest', 'last few expenses', 'last expenses', 'transactions']),
    ('spending', ['spend', 'spent', 'spending', 'expense', 'kharch', 'how much did', 'total', 'paid']),
]

GREETINGS = {'hi', 'hello', 'hey', 'hii', 'namaste', 'hola', 'yo', 'good morning', 'good evening'}


def detect_category(text):
    t = ' ' + text.lower()
    for cat, words in CATEGORY_KEYWORDS.items():
        if any(w in t for w in words):
            return cat
    return None


def detect_intent(text):
    t = text.lower()
    for intent, words in INTENT_KEYWORDS:
        if any(w in t for w in words):
            return intent
    if detect_category(t) and any(w in t for w in ('how much', 'kitna', 'kitne')):
        return 'spending'
    return None


def resolve_period(text, today):
    t = text.lower()
    if 'yesterday' in t:
        d = today - timedelta(days=1)
        return d, d, 'yesterday'
    if 'today' in t:
        return today, today, 'today'
    if 'last week' in t or 'previous week' in t:
        start = today - timedelta(days=today.weekday() + 7)
        return start, start + timedelta(days=6), 'last week'
    if 'this week' in t or 'week' in t:
        return today - timedelta(days=today.weekday()), today, 'this week'
    if 'last month' in t or 'previous month' in t:
        end = today.replace(day=1) - timedelta(days=1)
        return end.replace(day=1), end, 'last month'
    m = re.search(r'last (\d{1,3}) days', t)
    if m:
        n = max(1, int(m.group(1)))
        return today - timedelta(days=n - 1), today, 'in the last %d days' % n
    return today.replace(day=1), today, 'this month'


def _summarise_chunk(chunk, max_chars=420):
    pieces = []
    for ln in str(chunk.get('text', '')).splitlines():
        ln = ln.strip()
        if not ln or ln.startswith('#') or ln.startswith('---'):
            continue  # skip headings / rules
        ln = re.sub(r'[*_`]{1,3}', '', ln.lstrip('-*>0123456789. ')).strip()
        if ln and ln[-1] not in '.!?:;':
            ln += '.'
        pieces.append(ln)
    text = re.sub(r'\s+', ' ', ' '.join(pieces)).strip()
    sentences = re.split(r'(?<=[.!?])\s+', text)
    out = ''
    for s in sentences:
        if len(out) + len(s) > max_chars and out:
            break
        out = (out + ' ' + s).strip()
    return out or text[:max_chars]


def _fallback_spending(conn, uid, message, today):
    start, end, label = resolve_period(message, today)
    category = detect_category(message)
    s = tools.get_spending_summary(conn, uid, start.isoformat(), end.isoformat(), category, today=today)
    what = ('on %s ' % category) if category else ''
    if s['count'] == 0:
        return "I don't see any expenses %s%s (%s to %s). Log a few and I can break them down for you." % (
            what, label, s['start_date'], s['end_date'])
    lines = ['You spent %s %s%s across %d expense%s (about %s a day).' % (
        fmt_inr(s['total']), what, label, s['count'], '' if s['count'] == 1 else 's', fmt_inr(s['daily_average']))]
    if not category and s['by_category']:
        top = list(s['by_category'].items())[:3]
        lines.append('Top categories: ' + ', '.join('%s %s' % (c, fmt_inr(v)) for c, v in top) + '.')
    if s['largest_expenses']:
        big = s['largest_expenses'][0]
        desc = (' (%s)' % big['description']) if big.get('description') else ''
        lines.append('Biggest single expense: %s on %s%s, %s.' % (fmt_inr(big['amount']), big['category'], desc, big['date']))
    return ' '.join(lines)


def _fallback_budget(conn, uid, today):
    st = tools.get_budget_status(conn, uid, today=today)
    if not st['budgets']:
        return "You haven't set any budgets yet. Set a weekly or monthly budget per category on the Budget page and I'll track it for you."
    parts = []
    for b in st['budgets']:
        status = {'over': 'OVER budget', 'near_limit': 'close to the limit', 'ok': 'on track'}[b['status']]
        parts.append('%s (%s): %s of %s used (%.0f%%), %s' % (
            b['category'], b['period'], fmt_inr(b['spent']), fmt_inr(b['budget']), b['percent_used'], status))
    over = [b['category'] for b in st['budgets'] if b['status'] == 'over']
    tail = (' Ease off on %s for the rest of the period.' % ', '.join(over)) if over else ' Nice work staying in control.'
    return 'Budget status: ' + '; '.join(parts) + '.' + tail


def _fallback_goal(conn, uid, message, today):
    goals = tools.get_goals(conn, uid, today=today)['goals']
    if not goals:
        return "You don't have any savings goals yet. Add one on the Goals page (e.g. a laptop or trip) and I'll work out how much to save each week."
    plan = tools.plan_goal(conn, uid, message, today=today)
    if not plan.get('found'):
        plan = tools.plan_goal(conn, uid, str(goals[0]['id']), today=today)
    if plan['status'] == 'completed':
        text = 'Your goal "%s" is fully funded (%s). Time to celebrate or set the next one!' % (plan['goal'], fmt_inr(plan['target_amount']))
    elif plan['status'] == 'overdue':
        text = 'Your goal "%s" passed its target date with %s still to go. Consider setting a new date; even %s a week adds up.' % (
            plan['goal'], fmt_inr(plan['remaining']), fmt_inr(plan['remaining'] / 8))
    else:
        text = 'For "%s" you still need %s by %s, so save about %s a week (%s a month) for the next %d week%s.' % (
            plan['goal'], fmt_inr(plan['remaining']), plan['target_date'], fmt_inr(plan['weekly_needed']),
            fmt_inr(plan['monthly_needed']), plan['weeks_left'], '' if plan['weeks_left'] == 1 else 's')
        share = plan.get('weekly_needed_as_percent_of_spend')
        if share is not None:
            text += ' That is about %.0f%% of your average weekly spending (%s).' % (share, fmt_inr(plan['average_weekly_spend_last_4_weeks']))
    others = [g['title'] for g in goals if g['title'] != plan['goal']]
    if others:
        text += ' Other goals: ' + ', '.join(others[:3]) + '.'
    return text


def _fallback_forecast(conn, uid, today):
    f = tools.forecast_month_end(conn, uid, today=today)
    text = 'So far this month (%s) you have spent %s; at your current pace you will reach about %s by month end.' % (
        f.get('month', ''), fmt_inr(f.get('spent_so_far', 0)), fmt_inr(f.get('projected_total', 0)))
    budget = f.get('monthly_budget')
    if budget:
        if (f.get('projected_overrun') or 0) > 0:
            text += ' That is %s over your %s budget' % (fmt_inr(f['projected_overrun']), fmt_inr(budget))
            text += (', crossing it around %s.' % f['overrun_date']) if f.get('overrun_date') else '.'
            days_left = max(1, (date(today.year + (today.month // 12), today.month % 12 + 1, 1) - today).days)
            text += ' Cutting about %s a day keeps you on track.' % fmt_inr(f['projected_overrun'] / days_left)
        else:
            text += ' That is within your %s monthly budget. Keep it up!' % fmt_inr(budget)
    else:
        text += ' Set budgets to see whether that keeps you on track.'
    return text


def _fallback_anomaly(conn, uid, today):
    res = tools.get_spending_anomalies(conn, uid, today=today)
    if not res['anomalies']:
        return "Nothing unusual this week: every category is within its normal range compared with your recent weeks."
    parts = ['%s at %s vs your usual %s (%.1fx)' % (a['category'], fmt_inr(a['this_week']), fmt_inr(a['baseline']), a['ratio'])
             for a in res['anomalies'][:3]]
    return 'Unusual spending this week: ' + '; '.join(parts) + '. If it was a one-off, no worries; otherwise set a cap for the rest of the week.'


def _fallback_recent(conn, uid, message):
    res = tools.get_recent_expenses(conn, uid, limit=5, category=detect_category(message))
    if not res['expenses']:
        return "You haven't logged any expenses yet."
    items = ['%s %s on %s%s' % (e['date'], fmt_inr(e['amount']), e['category'],
                                (' (%s)' % e['description']) if e['description'] else '') for e in res['expenses']]
    return 'Your latest expenses: ' + '; '.join(items) + '.'


def fallback_answer(conn, user, message, chunks, today=None):
    today = today or date.today()
    uid = user['id']
    intent = detect_intent(message)
    tools_used, sources = [], []
    handlers = {
        'spending': ('get_spending_summary', lambda: _fallback_spending(conn, uid, message, today)),
        'budget': ('get_budget_status', lambda: _fallback_budget(conn, uid, today)),
        'goal': ('plan_goal', lambda: _fallback_goal(conn, uid, message, today)),
        'forecast': ('forecast_month_end', lambda: _fallback_forecast(conn, uid, today)),
        'anomaly': ('get_spending_anomalies', lambda: _fallback_anomaly(conn, uid, today)),
        'recent': ('get_recent_expenses', lambda: _fallback_recent(conn, uid, message)),
    }
    text = None
    note = OFFLINE_NOTE
    if intent in handlers:
        tool_name, fn = handlers[intent]
        try:
            text = fn()
            tools_used.append(tool_name)
        except Exception:
            text = None

    if text is None:
        cleaned = re.sub(r'[^a-z ]', '', message.lower()).strip()
        if cleaned in GREETINGS or not cleaned:
            s = tools.get_spending_summary(conn, uid, today.replace(day=1).isoformat(), today.isoformat(), today=today)
            tools_used.append('get_spending_summary')
            text = ('Hi %s! You have spent %s so far this month. Ask me things like "How much did I spend on food this week?", '
                    '"Am I within budget?", "Will I overshoot this month?" or "How much should I save for my goal?"'
                    % (user.get('name') or 'there', fmt_inr(s['total'])))
        elif chunks:
            top = chunks[0]
            text = 'From our guide "%s" [1]: %s' % (top.get('title', ''), _summarise_chunk(top))
            note = OFFLINE_NOTE_KB
            sources.append({'title': top.get('title', ''), 'source': top.get('source', '')})
            if len(chunks) > 1 and chunks[1].get('title') != top.get('title'):
                text += ' See also "%s" [2].' % chunks[1].get('title', '')
                sources.append({'title': chunks[1].get('title', ''), 'source': chunks[1].get('source', '')})
        else:
            text = ('I can answer questions about your spending, budgets, goals, month-end forecast and unusual '
                    'spending, plus general money tips for students. Try "How much did I spend on food this month?"')

    return {
        'response': text + ' ' + note,
        'sources': sources,
        'tools_used': tools_used,
        'generated_by': 'fallback',
    }


# ---------------------------------------------------------------- entry point

def answer(conn, user, message, today=None):
    """user: {"id","name","user_type"} from the session.

    Returns {"response", "sources": [{"title","source"}], "tools_used": [str], "generated_by": "llm"|"fallback"}.
    """
    today = today or date.today()
    message = (message or '').strip()[:2000]
    history = memory.get_history_for_model(conn, user['id'])
    chunks = _retrieve(message, k=4) if message else []

    result = None
    if llm.is_configured() and message:
        try:
            result = _llm_answer(conn, user, message, history, chunks, today)
        except Exception:
            result = None
    if result is None:
        result = fallback_answer(conn, user, message, chunks, today=today)

    try:
        memory.save_message(conn, user['id'], 'user', message)
        memory.save_message(conn, user['id'], 'bot', result['response'])
        memory.maybe_update_summary(conn, user['id'])
    except Exception:
        pass
    return result
