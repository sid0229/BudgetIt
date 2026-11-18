"""Tests for backend/ai and the new AI routes. The LLM is always faked; no network."""
import json
from datetime import date, timedelta

import pytest

from ai import chat, insights, llm, memory, prompts, tools


class FakeLLM:
    """Scripted stand-in for ai.llm.generate. Each item is a dict result or an Exception."""

    def __init__(self, script):
        self.script = list(script)
        self.calls = []

    def __call__(self, messages, **kwargs):
        self.calls.append({'messages': [dict(m) for m in messages], **kwargs})
        item = self.script.pop(0) if self.script else {'text': 'ok', 'function_calls': [], 'raw': None}
        if isinstance(item, Exception):
            raise item
        return {'text': item.get('text', ''), 'function_calls': item.get('function_calls', []), 'raw': item.get('raw')}


@pytest.fixture
def fake_llm(monkeypatch):
    def install(script):
        fake = FakeLLM(script)
        monkeypatch.setattr(llm, 'is_configured', lambda: True)
        monkeypatch.setattr(llm, 'generate', fake)
        return fake
    return install


def _user(user_id):
    return {'id': user_id, 'name': 'Asha', 'user_type': 'student'}


# ------------------------------------------------------------------ status / auth

def test_ai_status_no_auth(client):
    data = client.get('/api/ai/status').get_json()
    assert data == {'llm': False, 'dense_retrieval': False, 'model': llm.get_model()}


@pytest.mark.parametrize('method,path', [
    ('post', '/api/chat'), ('get', '/api/chat/history'), ('delete', '/api/chat/history'),
    ('get', '/api/insights'), ('post', '/api/insights/feedback'), ('post', '/api/expenses/categorize'),
])
def test_ai_routes_require_auth(client, method, path):
    assert getattr(client, method)(path, json={}).status_code == 401


def test_existing_routes_still_work(logged_in):
    c = logged_in['client']
    assert len(c.get('/api/expenses').get_json()) == 27
    assert c.get('/api/analytics/weekly').status_code == 200
    assert c.get('/api/goals').get_json()[0]['title'] == 'New Laptop'


# ------------------------------------------------------------------ fallback chat

def _chat(c, message):
    resp = c.post('/api/chat', json={'message': message})
    assert resp.status_code == 200
    data = resp.get_json()
    assert set(data) == {'response', 'sources', 'tools_used', 'generated_by', 'timestamp'}
    return data


def test_fallback_spending_uses_real_numbers(logged_in):
    data = _chat(logged_in['client'], 'How much did I spend on food this week?')
    assert data['generated_by'] == 'fallback'
    assert data['tools_used'] == ['get_spending_summary']
    assert '₹1,600' in data['response']          # 900 + 700 this week
    assert 'offline' in data['response']


def test_fallback_budget_goal_forecast_anomaly(logged_in):
    c = logged_in['client']
    budget = _chat(c, 'Am I over budget?')
    assert budget['tools_used'] == ['get_budget_status']
    assert 'food' in budget['response'] and 'OVER' in budget['response']

    goal = _chat(c, 'How much should I save each week for my laptop?')
    assert goal['tools_used'] == ['plan_goal']
    assert '₹4,200' in goal['response']          # 42,000 over 10 weeks

    forecast = _chat(c, 'Will I stay within my budget by month end?')
    assert forecast['tools_used'] == ['forecast_month_end']
    assert 'month end' in forecast['response']

    anomaly = _chat(c, 'Anything unusual in my spending?')
    assert anomaly['tools_used'] == ['get_spending_anomalies']
    assert 'food' in anomaly['response'].lower()


def test_fallback_general_question_uses_rag_sources(logged_in):
    data = _chat(logged_in['client'], 'How do I build an emergency fund?')
    assert data['generated_by'] == 'fallback'
    assert data['sources'], 'expected knowledge-base sources'
    assert all(set(s) == {'title', 'source'} for s in data['sources'])
    assert '[1]' in data['response']


def test_chat_requires_message(logged_in):
    assert logged_in['client'].post('/api/chat', json={'message': '  '}).status_code == 400


def test_chat_history_roundtrip(logged_in):
    c = logged_in['client']
    _chat(c, 'hi')
    _chat(c, 'How much did I spend this month?')
    msgs = c.get('/api/chat/history').get_json()['messages']
    assert [m['role'] for m in msgs] == ['user', 'bot', 'user', 'bot']
    assert msgs[0]['text'] == 'hi' and msgs[0]['timestamp']
    assert c.delete('/api/chat/history').get_json() == {'message': 'cleared'}
    assert c.get('/api/chat/history').get_json()['messages'] == []


# ------------------------------------------------------------------ LLM chat path

def test_llm_tool_loop_injects_session_user(logged_in, fake_llm, monkeypatch):
    monkeypatch.setattr(chat, '_retrieve', lambda q, k=4: [
        {'id': 'a#0', 'title': 'Food savings', 'source': 'BudgetIt editorial', 'text': 'Cook in batches.', 'score': 1.0},
        {'id': 'b#0', 'title': 'UPI safety', 'source': 'https://www.npci.org.in', 'text': 'Never share PIN.', 'score': 0.5},
    ])
    today = date.today()
    monday = (today - timedelta(days=today.weekday())).isoformat()
    fake = fake_llm([
        {'function_calls': [{'name': 'get_spending_summary', 'id': 'c1',
                             'args': {'start_date': monday, 'end_date': today.isoformat(),
                                      'category': 'food', 'user_id': 999}}]},
        {'text': 'You spent ₹1,600 on food this week. Batch cooking helps [1].'},
    ])
    data = _chat(logged_in['client'], 'How much did I spend on food this week?')
    assert data['generated_by'] == 'llm'
    assert data['tools_used'] == ['get_spending_summary']
    assert data['sources'] == [{'title': 'Food savings', 'source': 'BudgetIt editorial'}]

    # Tool result was computed for the session user, not user 999.
    tool_msg = fake.calls[1]['messages'][-1]
    assert tool_msg['role'] == 'tool'
    assert tool_msg['responses'][0]['response']['result']['total'] == 1600.0
    assert tool_msg['responses'][0]['id'] == 'c1'
    # Prompt contains few-shot, numbered knowledge and the tools.
    system = fake.calls[0]['system_instruction']
    assert 'Example 1' in system and '[1] Food savings' in system and 'USER PROFILE: name=Asha' in system
    assert {t['name'] for t in fake.calls[0]['tools']} == set(tools.TOOL_NAMES)
    # History of the next turn includes the previous exchange.
    fake.script = [{'text': 'Sure!'}]
    _chat(logged_in['client'], 'thanks')
    roles = [m['role'] for m in fake.calls[2]['messages']]
    assert roles == ['user', 'model', 'user']


def test_llm_tool_loop_is_bounded(logged_in, fake_llm):
    call = {'function_calls': [{'name': 'get_goals', 'args': {}, 'id': None}]}
    fake = fake_llm([call] * tools.MAX_TOOL_ROUNDS + [{'text': 'Here is your summary.'}])
    data = _chat(logged_in['client'], 'goals?')
    assert data['generated_by'] == 'llm'
    assert len(fake.calls) == tools.MAX_TOOL_ROUNDS + 1
    assert fake.calls[-1]['tool_mode'] == 'NONE'


def test_llm_failure_falls_back(logged_in, fake_llm):
    fake_llm([RuntimeError('503 overloaded')])
    data = _chat(logged_in['client'], 'How much did I spend on food this week?')
    assert data['generated_by'] == 'fallback'
    assert '₹1,600' in data['response']


def test_llm_empty_text_falls_back(logged_in, fake_llm):
    fake_llm([{'text': ''}])
    assert _chat(logged_in['client'], 'hello')['generated_by'] == 'fallback'


# ------------------------------------------------------------------ tools

def test_execute_tool_ignores_model_user_id_and_unknown(logged_in, db_conn):
    uid = logged_in['user_id']
    res = tools.execute_tool(db_conn, uid, 'get_recent_expenses', {'limit': 3, 'user_id': 12345})
    assert res['count'] == 3
    assert 'error' in tools.execute_tool(db_conn, uid, 'drop_tables', {})
    other = tools.execute_tool(db_conn, uid + 1, 'get_recent_expenses', {})
    assert other['count'] == 0


def test_plan_goal_and_budget_status(logged_in, db_conn):
    uid = logged_in['user_id']
    plan = tools.plan_goal(db_conn, uid, 'laptop')
    assert plan['found'] and plan['weeks_left'] == 10 and plan['weekly_needed'] == 4200.0
    assert tools.plan_goal(db_conn, uid, 'yacht')['found'] is False
    status = {b['category']: b for b in tools.get_budget_status(db_conn, uid)['budgets']}
    assert status['food']['status'] == 'over'
    forecast = tools.execute_tool(db_conn, uid, 'forecast_month_end', {})
    assert 'projected_total' in forecast and 'error' not in forecast
    anomalies = tools.execute_tool(db_conn, uid, 'get_spending_anomalies', {})
    assert anomalies['anomalies'][0]['category'] == 'food'


def test_declarations_are_valid_sdk_objects():
    from google.genai import types
    decls = llm.build_function_declarations(tools.TOOL_DECLARATIONS)
    assert len(decls) == 7
    for d in tools.TOOL_DECLARATIONS:
        assert 'user_id' not in d['parameters'].get('properties', {})
    types.Schema.model_validate(prompts.INSIGHTS_SCHEMA)
    contents = llm._to_contents([
        {'role': 'user', 'text': 'hi'}, {'role': 'model', 'text': 'hello'},
        {'role': 'tool', 'responses': [{'name': 'get_goals', 'response': {'result': {}}, 'id': 'x'}]},
    ])
    assert [c.role for c in contents] == ['user', 'model', 'user']
    assert contents[2].parts[0].function_response.name == 'get_goals'


def test_fmt_inr():
    assert chat.fmt_inr(125000) == '₹1,25,000'
    assert chat.fmt_inr(999) == '₹999'
    assert chat.fmt_inr(12345678.4) == '₹1,23,45,678'


def test_intent_detection():
    assert chat.detect_intent('kitna kharch hua food pe?') == 'spending'
    assert chat.detect_intent('Will I go over my budget this month?') == 'forecast'
    assert chat.detect_intent('Tell me about SIPs') is None


# ------------------------------------------------------------------ insights

def test_insights_rules_shape_and_cache(logged_in):
    c = logged_in['client']
    data = c.get('/api/insights').get_json()
    assert set(data) == {'insights', 'persona', 'forecast', 'anomalies', 'generated_by'}
    assert data['generated_by'] == 'rules'
    assert 3 <= len(data['insights']) <= 5
    for ins in data['insights']:
        assert set(ins) == {'id', 'type', 'title', 'message', 'action', 'tip_id'}
        assert ins['type'] in prompts.INSIGHT_TYPES
    assert any(i['tip_id'] for i in data['insights'])
    assert any(i['id'].startswith('anomaly-food') for i in data['insights'])
    assert {'key', 'label', 'description', 'method'} <= set(data['persona'])
    assert 'projected_total' in data['forecast']

    uid = logged_in['user_id']
    assert insights._cached(uid) is not None
    c.post('/api/expenses', json={'amount': 50, 'category': 'food', 'description': 'chai'})
    assert insights._cached(uid) is None


def test_insights_llm_json(logged_in, db_conn, fake_llm):
    user = _user(logged_in['user_id'])
    facts = insights.compute_facts(db_conn, user)
    tip_id = facts['tips'][0]['id']
    fake = fake_llm([{'text': json.dumps({'insights': [
        {'type': 'warning', 'title': 'Food spike', 'message': 'Food is ₹1,600 this week.', 'action': 'Cook twice', 'tip_id': None},
        {'type': 'info', 'title': 'Tip', 'message': 'Try the mess.', 'action': None, 'tip_id': tip_id},
        {'type': 'bogus', 'title': 'Laptop', 'message': '₹42,000 to go.', 'tip_id': 'made_up_tip'},
    ]})}])
    data = insights.generate_insights(db_conn, user, use_cache=False)
    assert data['generated_by'] == 'llm'
    assert [i['tip_id'] for i in data['insights']] == [None, tip_id, None]
    assert data['insights'][2]['type'] == 'info'
    assert fake.calls[0]['response_schema'] == prompts.INSIGHTS_SCHEMA
    assert 'FACTS' in fake.calls[0]['messages'][0]['text']


def test_insights_llm_bad_output_falls_back(logged_in, db_conn, fake_llm):
    fake_llm([{'text': 'not json'}])
    data = insights.generate_insights(db_conn, _user(logged_in['user_id']), use_cache=False)
    assert data['generated_by'] == 'rules' and len(data['insights']) >= 3


def test_insights_new_user_cold_start(client):
    client.post('/api/auth/signup', json={'name': 'New', 'email': 'n@x.com', 'password': 'p', 'userType': 'professional'})
    data = client.get('/api/insights').get_json()
    assert data['insights'][0]['id'] == 'start-logging'
    assert any(i['tip_id'] for i in data['insights'])


def test_feedback_route(logged_in, db_conn):
    c = logged_in['client']
    tip_id = next(i['tip_id'] for i in c.get('/api/insights').get_json()['insights'] if i['tip_id'])
    assert c.post('/api/insights/feedback', json={'tip_id': tip_id, 'reward': 1}).get_json() == {'message': 'ok'}
    row = db_conn.execute('SELECT tip_id, reward FROM insight_feedback').fetchone()
    assert row['tip_id'] == tip_id and row['reward'] == 1.0
    arm = db_conn.execute('SELECT n FROM bandit_arms WHERE tip_id = ?', (tip_id,)).fetchone()
    assert arm['n'] == 1
    assert c.post('/api/insights/feedback', json={'tip_id': tip_id, 'reward': 5}).status_code == 400
    assert c.post('/api/insights/feedback', json={'tip_id': 'nope', 'reward': 0}).status_code == 400


# ------------------------------------------------------------------ categorize

def test_categorize_keyword(logged_in):
    data = logged_in['client'].post('/api/expenses/categorize', json={'description': 'Swiggy biryani'}).get_json()
    assert data['category'] == 'food' and data['method'] == 'keyword'
    assert set(data) == {'category', 'confidence', 'method'}


def test_categorize_llm_fallback(logged_in, fake_llm):
    fake_llm([{'text': 'Entertainment'}])
    data = logged_in['client'].post('/api/expenses/categorize', json={'description': 'xyzzy plover'}).get_json()
    assert data['category'] == 'entertainment' and data['method'] == 'llm'


def test_categorize_without_llm_defaults(logged_in):
    data = logged_in['client'].post('/api/expenses/categorize', json={'description': 'xyzzy plover'}).get_json()
    assert data['method'] == 'default'


# ------------------------------------------------------------------ memory

def test_memory_summary_every_n_messages(logged_in, db_conn, fake_llm):
    uid = logged_in['user_id']
    assert memory.maybe_update_summary(db_conn, uid) is False  # not configured yet / no messages
    fake = fake_llm([{'text': '- Lives in a hostel in Pune\n- Saving for a laptop'}])
    for i in range(memory.SUMMARY_EVERY):
        memory.save_message(db_conn, uid, 'user', 'msg %d' % i)
        memory.save_message(db_conn, uid, 'bot', 'reply %d' % i)
    assert memory.maybe_update_summary(db_conn, uid) is True
    assert 'hostel' in memory.get_summary(db_conn, uid)
    assert fake.calls[0]['system_instruction'] == prompts.MEMORY_SYSTEM_PROMPT
    # summary is injected into the chat system prompt
    sys_prompt = prompts.build_chat_system_prompt(_user(uid), date.today(), memory_summary=memory.get_summary(db_conn, uid))
    assert 'Lives in a hostel' in sys_prompt


def test_history_window(logged_in, db_conn):
    uid = logged_in['user_id']
    memory.save_message(db_conn, uid, 'bot', 'orphan bot first')
    for i in range(15):
        memory.save_message(db_conn, uid, 'user', 'u%d' % i)
        memory.save_message(db_conn, uid, 'bot', 'b%d' % i)
    hist = memory.get_history_for_model(db_conn, uid)
    assert len(hist) == memory.HISTORY_TURNS * 2
    assert hist[0] == {'role': 'user', 'text': 'u5'}


def test_no_api_key_during_tests():
    import os
    from rag import retriever
    assert not os.environ.get('GEMINI_API_KEY')
    assert retriever.is_dense_enabled() is False
    assert llm.is_configured() is False


def test_citation_parsing_variants():
    chunks = [{'title': 'T%d' % i, 'source': 'S%d' % i} for i in range(1, 5)]
    assert [s['title'] for s in chat._sources_from_citations('a [1, 3] b [2-3] c [9]', chunks)] == ['T1', 'T3', 'T2']
    assert chat._sources_from_citations('no cites', chunks) == []
