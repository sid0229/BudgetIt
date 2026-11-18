from flask import Flask, request, jsonify, session
from flask_cors import CORS
import sqlite3
import hashlib
import secrets
from datetime import datetime, timedelta
import json
import os

from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, '.env'))

from ai import chat as ai_chat
from ai import insights as ai_insights
from ai import memory as ai_memory
from ai import llm as ai_llm
from ai import categorize as ai_categorize

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY') or secrets.token_hex(16)
app.config['DATABASE'] = os.environ.get('BUDGETIT_DB', 'budgetit.db')
CORS(app, supports_credentials=True)

# Database initialization
def init_db():
    conn = sqlite3.connect(app.config['DATABASE'])
    cursor = conn.cursor()
    
    # Users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            user_type TEXT NOT NULL CHECK (user_type IN ('student', 'professional')),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Expenses table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            category TEXT NOT NULL,
            description TEXT,
            date TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    # Budgets table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS budgets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            category TEXT NOT NULL,
            amount REAL NOT NULL,
            period TEXT NOT NULL CHECK (period IN ('weekly', 'monthly')),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    # Goals table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS goals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            target_amount REAL NOT NULL,
            saved_amount REAL DEFAULT 0,
            target_date TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    conn.commit()

    # GenAI tables (personalization: bandit/feedback; ai: chat history + memory)
    import personalization
    personalization.init_tables(conn)
    ai_memory.init_tables(conn)

    conn.commit()
    conn.close()

# Helper functions
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def get_db_connection():
    conn = sqlite3.connect(app.config['DATABASE'])
    conn.row_factory = sqlite3.Row
    return conn

def current_user():
    return {
        'id': session['user_id'],
        'name': session.get('user_name'),
        'email': session.get('user_email'),
        'user_type': session.get('user_type', 'student'),
    }

# Authentication routes
@app.route('/api/auth/signup', methods=['POST'])
def signup():
    data = request.json
    name = data.get('name')
    email = data.get('email')
    password = data.get('password')
    user_type = data.get('userType', 'student')
    
    if not all([name, email, password]):
        return jsonify({'error': 'Missing required fields'}), 400
    
    conn = get_db_connection()
    
    # Check if user already exists
    existing_user = conn.execute('SELECT id FROM users WHERE email = ?', (email,)).fetchone()
    if existing_user:
        conn.close()
        return jsonify({'error': 'User already exists'}), 409
    
    # Create new user
    password_hash = hash_password(password)
    cursor = conn.cursor()
    cursor.execute(
        'INSERT INTO users (name, email, password_hash, user_type) VALUES (?, ?, ?, ?)',
        (name, email, password_hash, user_type)
    )
    user_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    session['user_id'] = user_id
    session['user_email'] = email
    session['user_name'] = name
    session['user_type'] = user_type
    
    return jsonify({
        'message': 'User created successfully',
        'user': {
            'id': user_id,
            'name': name,
            'email': email,
            'userType': user_type
        }
    }), 201

@app.route('/api/auth/signin', methods=['POST'])
def signin():
    data = request.json
    email = data.get('email')
    password = data.get('password')
    
    if not all([email, password]):
        return jsonify({'error': 'Missing credentials'}), 400
    
    conn = get_db_connection()
    user = conn.execute(
        'SELECT id, name, email, password_hash, user_type FROM users WHERE email = ?',
        (email,)
    ).fetchone()
    conn.close()
    
    if not user or user['password_hash'] != hash_password(password):
        return jsonify({'error': 'Invalid credentials'}), 401
    
    session['user_id'] = user['id']
    session['user_email'] = user['email']
    session['user_name'] = user['name']
    session['user_type'] = user['user_type']
    
    return jsonify({
        'message': 'Login successful',
        'user': {
            'id': user['id'],
            'name': user['name'],
            'email': user['email'],
            'userType': user['user_type']
        }
    }), 200

@app.route('/api/auth/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'message': 'Logged out successfully'}), 200

@app.route('/api/auth/me', methods=['GET'])
def get_current_user():
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    return jsonify({
        'user': {
            'id': session['user_id'],
            'name': session['user_name'],
            'email': session['user_email'],
            'userType': session['user_type']
        }
    }), 200

# Expense routes
@app.route('/api/expenses', methods=['GET'])
def get_expenses():
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    conn = get_db_connection()
    expenses = conn.execute(
        'SELECT id, amount, category, description, date FROM expenses WHERE user_id = ? ORDER BY date DESC',
        (session['user_id'],)
    ).fetchall()
    conn.close()
    
    return jsonify([dict(expense) for expense in expenses]), 200

@app.route('/api/expenses', methods=['POST'])
def add_expense():
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    data = request.json
    amount = data.get('amount')
    category = data.get('category')
    description = data.get('description', '')
    date = data.get('date', datetime.now().strftime('%Y-%m-%d'))
    
    if not all([amount, category]):
        return jsonify({'error': 'Missing required fields'}), 400
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        'INSERT INTO expenses (user_id, amount, category, description, date) VALUES (?, ?, ?, ?, ?)',
        (session['user_id'], amount, category, description, date)
    )
    expense_id = cursor.lastrowid
    conn.commit()
    conn.close()
    ai_insights.invalidate(session['user_id'])
    
    return jsonify({
        'id': expense_id,
        'message': 'Expense added successfully'
    }), 201

# Budget routes
@app.route('/api/budgets', methods=['GET'])
def get_budgets():
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    conn = get_db_connection()
    budgets = conn.execute(
        'SELECT id, category, amount, period FROM budgets WHERE user_id = ?',
        (session['user_id'],)
    ).fetchall()
    conn.close()
    
    return jsonify([dict(budget) for budget in budgets]), 200

@app.route('/api/budgets', methods=['POST'])
def set_budget():
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    data = request.json
    category = data.get('category')
    amount = data.get('amount')
    period = data.get('period', 'weekly')
    
    if not all([category, amount]):
        return jsonify({'error': 'Missing required fields'}), 400
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Update existing budget or create new one
    cursor.execute(
        'INSERT OR REPLACE INTO budgets (user_id, category, amount, period) VALUES (?, ?, ?, ?)',
        (session['user_id'], category, amount, period)
    )
    conn.commit()
    conn.close()
    ai_insights.invalidate(session['user_id'])
    
    return jsonify({'message': 'Budget set successfully'}), 200

# Goals routes
@app.route('/api/goals', methods=['GET'])
def get_goals():
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    conn = get_db_connection()
    goals = conn.execute(
        'SELECT id, title, target_amount, saved_amount, target_date FROM goals WHERE user_id = ?',
        (session['user_id'],)
    ).fetchall()
    conn.close()
    
    return jsonify([dict(goal) for goal in goals]), 200

@app.route('/api/goals', methods=['POST'])
def add_goal():
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    data = request.json
    title = data.get('title')
    target_amount = data.get('targetAmount')
    target_date = data.get('targetDate')
    
    if not all([title, target_amount, target_date]):
        return jsonify({'error': 'Missing required fields'}), 400
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        'INSERT INTO goals (user_id, title, target_amount, target_date) VALUES (?, ?, ?, ?)',
        (session['user_id'], title, target_amount, target_date)
    )
    goal_id = cursor.lastrowid
    conn.commit()
    conn.close()
    ai_insights.invalidate(session['user_id'])
    
    return jsonify({
        'id': goal_id,
        'message': 'Goal added successfully'
    }), 201

# AI routes (logic lives in backend/ai/)
@app.route('/api/chat', methods=['POST'])
def chat_with_ai():
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401

    data = request.get_json(silent=True) or {}
    message = str(data.get('message', '') or '').strip()
    if not message:
        return jsonify({'error': 'Message is required'}), 400

    conn = get_db_connection()
    try:
        result = ai_chat.answer(conn, current_user(), message)
    finally:
        conn.close()

    return jsonify({
        'response': result['response'],
        'sources': result.get('sources', []),
        'tools_used': result.get('tools_used', []),
        'generated_by': result.get('generated_by', 'fallback'),
        'timestamp': datetime.now().isoformat()
    }), 200

@app.route('/api/chat/history', methods=['GET'])
def get_chat_history():
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401

    conn = get_db_connection()
    messages = ai_memory.get_messages(conn, session['user_id'], limit=100)
    conn.close()

    return jsonify({'messages': messages}), 200

@app.route('/api/chat/history', methods=['DELETE'])
def clear_chat_history():
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401

    conn = get_db_connection()
    ai_memory.clear_history(conn, session['user_id'])
    conn.close()

    return jsonify({'message': 'cleared'}), 200

@app.route('/api/insights', methods=['GET'])
def get_insights():
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401

    conn = get_db_connection()
    try:
        payload = ai_insights.generate_insights(conn, current_user())
    finally:
        conn.close()

    return jsonify(payload), 200

@app.route('/api/insights/feedback', methods=['POST'])
def insights_feedback():
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401

    data = request.get_json(silent=True) or {}
    tip_id = data.get('tip_id')
    reward = data.get('reward')
    if not tip_id or reward not in (0, 1, True, False):
        return jsonify({'error': 'tip_id and reward (1 or 0) are required'}), 400

    conn = get_db_connection()
    try:
        ai_insights.record_feedback(conn, current_user(), str(tip_id), 1.0 if reward else 0.0)
    except Exception as exc:
        return jsonify({'error': 'Could not record feedback: %s' % exc}), 400
    finally:
        conn.close()

    return jsonify({'message': 'ok'}), 200

@app.route('/api/expenses/categorize', methods=['POST'])
def categorize_expense():
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401

    data = request.get_json(silent=True) or {}
    description = str(data.get('description', '') or '')
    result = ai_categorize.categorize(description)

    return jsonify({
        'category': result['category'],
        'confidence': result['confidence'],
        'method': result['method']
    }), 200

@app.route('/api/ai/status', methods=['GET'])
def ai_status():
    try:
        from rag.retriever import is_dense_enabled
        dense = bool(is_dense_enabled())
    except Exception:
        dense = False

    return jsonify({
        'llm': ai_llm.is_configured(),
        'dense_retrieval': dense,
        'model': ai_llm.get_model()
    }), 200

# Analytics routes
@app.route('/api/analytics/weekly', methods=['GET'])
def get_weekly_analytics():
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    conn = get_db_connection()
    
    # Get expenses from last 7 days
    week_ago = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
    expenses = conn.execute(
        'SELECT category, SUM(amount) as total FROM expenses WHERE user_id = ? AND date >= ? GROUP BY category',
        (session['user_id'], week_ago)
    ).fetchall()
    
    # Get budgets
    budgets = conn.execute(
        'SELECT category, amount FROM budgets WHERE user_id = ? AND period = "weekly"',
        (session['user_id'],)
    ).fetchall()
    
    conn.close()
    
    expense_data = {expense['category']: expense['total'] for expense in expenses}
    budget_data = {budget['category']: budget['amount'] for budget in budgets}
    
    return jsonify({
        'expenses': expense_data,
        'budgets': budget_data,
        'period': 'weekly'
    }), 200

if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=int(os.environ.get('PORT', 5001)))