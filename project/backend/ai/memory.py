"""Chat history + LLM-maintained user profile summary (long-term memory)."""
from datetime import datetime

from ai import llm, prompts

HISTORY_TURNS = 10          # last 10 user/bot exchanges are sent to the model
SUMMARY_EVERY = 6           # refresh the profile summary every 6 user messages


def init_tables(conn):
    conn.execute('''
        CREATE TABLE IF NOT EXISTS chat_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            role TEXT NOT NULL CHECK (role IN ('user', 'bot')),
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_chat_messages_user ON chat_messages (user_id, id)')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS user_memory (
            user_id INTEGER PRIMARY KEY,
            summary TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    conn.commit()


def save_message(conn, user_id, role, content):
    conn.execute(
        'INSERT INTO chat_messages (user_id, role, content, created_at) VALUES (?, ?, ?, ?)',
        (user_id, role, content, datetime.now().isoformat())
    )
    conn.commit()


def get_messages(conn, user_id, limit=None):
    """Messages oldest-first as [{"role": "user"|"bot", "text", "timestamp"}]."""
    if limit:
        rows = conn.execute(
            'SELECT role, content, created_at FROM chat_messages WHERE user_id = ? ORDER BY id DESC LIMIT ?',
            (user_id, limit)
        ).fetchall()
        rows = list(reversed(rows))
    else:
        rows = conn.execute(
            'SELECT role, content, created_at FROM chat_messages WHERE user_id = ? ORDER BY id',
            (user_id,)
        ).fetchall()
    return [{'role': r['role'], 'text': r['content'], 'timestamp': r['created_at']} for r in rows]


def get_history_for_model(conn, user_id):
    """Last HISTORY_TURNS exchanges in llm.generate() message format."""
    msgs = get_messages(conn, user_id, limit=HISTORY_TURNS * 2)
    # Gemini expects the conversation to start with a user turn.
    while msgs and msgs[0]['role'] != 'user':
        msgs.pop(0)
    return [{'role': 'user' if m['role'] == 'user' else 'model', 'text': m['text']} for m in msgs]


def clear_history(conn, user_id):
    conn.execute('DELETE FROM chat_messages WHERE user_id = ?', (user_id,))
    conn.commit()


def get_summary(conn, user_id):
    row = conn.execute('SELECT summary FROM user_memory WHERE user_id = ?', (user_id,)).fetchone()
    return row['summary'] if row and row['summary'] else ''


def set_summary(conn, user_id, summary):
    conn.execute(
        'INSERT INTO user_memory (user_id, summary, updated_at) VALUES (?, ?, ?) '
        'ON CONFLICT(user_id) DO UPDATE SET summary = excluded.summary, updated_at = excluded.updated_at',
        (user_id, summary, datetime.now().isoformat())
    )
    conn.commit()


def user_message_count(conn, user_id):
    row = conn.execute(
        "SELECT COUNT(*) AS n FROM chat_messages WHERE user_id = ? AND role = 'user'", (user_id,)
    ).fetchone()
    return row['n'] if row else 0


def maybe_update_summary(conn, user_id, force=False):
    """Every SUMMARY_EVERY user messages, ask the LLM to merge new facts into the profile.

    Returns True if the summary was updated. Skipped when the LLM is not configured;
    any failure is swallowed (memory is a nice-to-have).
    """
    if not llm.is_configured():
        return False
    count = user_message_count(conn, user_id)
    if not force and (count == 0 or count % SUMMARY_EVERY != 0):
        return False
    try:
        recent = get_messages(conn, user_id, limit=SUMMARY_EVERY * 2)
        result = llm.generate(
            [{'role': 'user', 'text': prompts.build_memory_prompt(get_summary(conn, user_id), recent)}],
            system_instruction=prompts.MEMORY_SYSTEM_PROMPT,
            temperature=0.2,
        )
        summary = (result.get('text') or '').strip()
        if summary:
            set_summary(conn, user_id, summary[:1500])
            return True
    except Exception:
        pass
    return False
