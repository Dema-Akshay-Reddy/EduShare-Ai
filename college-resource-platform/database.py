"""
database.py
Handles all SQLite database operations for the AI-Powered College Resource
Sharing Platform: schema creation, seeding, and CRUD helpers for resources,
students, transactions, search history, demand history, and user accounts.

Every function uses the `db_session()` context manager below, which
guarantees the connection is closed in a `finally` block even if a query
raises (e.g. a UNIQUE constraint violation on signup). Without this, an
exception mid-function would leave an uncommitted connection open and
silently lock the database file for every subsequent write.
"""

import sqlite3
import os
from contextlib import contextmanager
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "resource_platform.db")


def get_connection():
    conn = sqlite3.connect(DB_PATH, timeout=15)
    conn.row_factory = sqlite3.Row
    return conn


@contextmanager
def db_session():
    """Yields a connection and guarantees it is closed afterwards, even if
    the caller's code raises an exception."""
    conn = get_connection()
    try:
        yield conn
    finally:
        conn.close()


def init_db():
    """Create all tables if they do not already exist."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    with db_session() as conn:
        cur = conn.cursor()

        cur.execute("""
            CREATE TABLE IF NOT EXISTS resources (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                item_name TEXT NOT NULL,
                category TEXT NOT NULL,
                department TEXT NOT NULL,
                semester INTEGER NOT NULL,
                condition TEXT NOT NULL,
                description TEXT,
                availability_status TEXT NOT NULL DEFAULT 'Available',
                uploader_name TEXT,
                estimated_value REAL DEFAULT 0,
                upload_date TEXT NOT NULL
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS students (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                department TEXT NOT NULL,
                semester INTEGER NOT NULL,
                interests TEXT
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                resource_id INTEGER NOT NULL,
                recipient_name TEXT NOT NULL,
                exchange_date TEXT NOT NULL,
                money_saved REAL DEFAULT 0,
                FOREIGN KEY (resource_id) REFERENCES resources (id)
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS search_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_name TEXT,
                query TEXT,
                timestamp TEXT NOT NULL
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS demand_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT NOT NULL,
                department TEXT NOT NULL,
                month INTEGER NOT NULL,
                year INTEGER NOT NULL,
                requests_count INTEGER NOT NULL
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                salt TEXT NOT NULL,
                full_name TEXT NOT NULL,
                department TEXT NOT NULL,
                semester INTEGER NOT NULL,
                interests TEXT,
                student_id INTEGER,
                failed_attempts INTEGER NOT NULL DEFAULT 0,
                locked_until TEXT,
                created_at TEXT NOT NULL,
                last_login TEXT,
                FOREIGN KEY (student_id) REFERENCES students (id)
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                token TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                token TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        """)

        conn.commit()


# ---------------------------------------------------------------------------
# Resources
# ---------------------------------------------------------------------------
def add_resource(item_name, category, department, semester, condition,
                  description, availability_status, uploader_name, estimated_value):
    with db_session() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO resources
            (item_name, category, department, semester, condition, description,
             availability_status, uploader_name, estimated_value, upload_date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (item_name, category, department, semester, condition, description,
              availability_status, uploader_name, estimated_value,
              datetime.now().strftime("%Y-%m-%d")))
        conn.commit()
        return cur.lastrowid


def get_all_resources(only_available=False):
    with db_session() as conn:
        cur = conn.cursor()
        if only_available:
            cur.execute("SELECT * FROM resources WHERE availability_status = 'Available' ORDER BY id DESC")
        else:
            cur.execute("SELECT * FROM resources ORDER BY id DESC")
        rows = cur.fetchall()
        return [dict(r) for r in rows]


def get_resource_by_id(resource_id):
    with db_session() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM resources WHERE id = ?", (resource_id,))
        row = cur.fetchone()
        return dict(row) if row else None


def update_resource_status(resource_id, status):
    with db_session() as conn:
        cur = conn.cursor()
        cur.execute("UPDATE resources SET availability_status = ? WHERE id = ?", (status, resource_id))
        conn.commit()


# ---------------------------------------------------------------------------
# Students
# ---------------------------------------------------------------------------
def add_student(name, department, semester, interests=""):
    with db_session() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO students (name, department, semester, interests)
            VALUES (?, ?, ?, ?)
        """, (name, department, semester, interests))
        conn.commit()
        return cur.lastrowid


def get_all_students():
    with db_session() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM students ORDER BY id")
        rows = cur.fetchall()
        return [dict(r) for r in rows]


def get_student_by_name(name):
    with db_session() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM students WHERE name = ?", (name,))
        row = cur.fetchone()
        return dict(row) if row else None


def get_student_by_id(student_id):
    with db_session() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM students WHERE id = ?", (student_id,))
        row = cur.fetchone()
        return dict(row) if row else None


# ---------------------------------------------------------------------------
# Transactions (resource exchanges)
# ---------------------------------------------------------------------------
def record_transaction(resource_id, recipient_name, money_saved):
    with db_session() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO transactions (resource_id, recipient_name, exchange_date, money_saved)
            VALUES (?, ?, ?, ?)
        """, (resource_id, recipient_name, datetime.now().strftime("%Y-%m-%d"), money_saved))
        conn.commit()
    update_resource_status(resource_id, "Exchanged")


def get_all_transactions():
    with db_session() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT t.id, t.resource_id, r.item_name, r.category, r.department,
                   t.recipient_name, t.exchange_date, t.money_saved
            FROM transactions t
            JOIN resources r ON t.resource_id = r.id
            ORDER BY t.exchange_date DESC
        """)
        rows = cur.fetchall()
        return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Search history (used to refine recommendations)
# ---------------------------------------------------------------------------
def log_search(student_name, query):
    with db_session() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO search_history (student_name, query, timestamp)
            VALUES (?, ?, ?)
        """, (student_name, query, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()


def get_search_history(student_name=None):
    with db_session() as conn:
        cur = conn.cursor()
        if student_name:
            cur.execute("SELECT * FROM search_history WHERE student_name = ? ORDER BY id DESC", (student_name,))
        else:
            cur.execute("SELECT * FROM search_history ORDER BY id DESC")
        rows = cur.fetchall()
        return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Demand history (used to train the demand-prediction model)
# ---------------------------------------------------------------------------
def add_demand_record(category, department, month, year, requests_count):
    with db_session() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO demand_history (category, department, month, year, requests_count)
            VALUES (?, ?, ?, ?, ?)
        """, (category, department, month, year, requests_count))
        conn.commit()


def get_demand_history():
    with db_session() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM demand_history")
        rows = cur.fetchall()
        return [dict(r) for r in rows]


def is_db_seeded():
    with db_session() as conn:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) as c FROM resources")
        count = cur.fetchone()["c"]
        return count > 0


# ---------------------------------------------------------------------------
# Users (authentication accounts)
# ---------------------------------------------------------------------------
def create_user(username, email, password_hash, salt, full_name, department,
                 semester, interests, student_id):
    """Raises sqlite3.IntegrityError if the username or email is already
    taken (UNIQUE constraints) — the caller should catch this and show a
    friendly error. The connection is always closed via db_session(), even
    when this exception is raised, so a failed signup attempt can never
    leave the database locked for other users."""
    with db_session() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO users (username, email, password_hash, salt, full_name,
                                department, semester, interests, student_id, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (username, email, password_hash, salt, full_name, department, semester,
              interests, student_id, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()
        return cur.lastrowid


def get_user_by_username(username):
    with db_session() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE username = ?", (username,))
        row = cur.fetchone()
        return dict(row) if row else None


def get_user_by_email(email):
    with db_session() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE email = ?", (email,))
        row = cur.fetchone()
        return dict(row) if row else None


def get_user_by_full_name(full_name: str):
    """Look up a registered user by their display name.
    Used to find an uploader's email address when sending exchange notifications.
    Returns None if the uploader was a seeded/synthetic user with no account."""
    with db_session() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE full_name = ?", (full_name,))
        row = cur.fetchone()
        return dict(row) if row else None


def record_login_success(user_id):
    with db_session() as conn:
        cur = conn.cursor()
        cur.execute("""
            UPDATE users SET failed_attempts = 0, locked_until = NULL, last_login = ?
            WHERE id = ?
        """, (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), user_id))
        conn.commit()


def record_login_failure(user_id, lock_until=None):
    with db_session() as conn:
        cur = conn.cursor()
        cur.execute("SELECT failed_attempts FROM users WHERE id = ?", (user_id,))
        current = cur.fetchone()["failed_attempts"] or 0
        cur.execute("""
            UPDATE users SET failed_attempts = ?, locked_until = ?
            WHERE id = ?
        """, (current + 1, lock_until, user_id))
        conn.commit()


# ---------------------------------------------------------------------------
# Sessions (persistent login across browser refreshes)
# ---------------------------------------------------------------------------
def create_session(token: str, user_id: int, expires_at: str):
    """Store a new session token tied to a user. Cleans up any expired tokens
    for the same user at the same time to keep the table lean."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with db_session() as conn:
        cur = conn.cursor()
        # Remove stale sessions for this user
        cur.execute("DELETE FROM sessions WHERE user_id = ? AND expires_at < ?", (user_id, now))
        cur.execute("""
            INSERT OR REPLACE INTO sessions (token, user_id, created_at, expires_at)
            VALUES (?, ?, ?, ?)
        """, (token, user_id, now, expires_at))
        conn.commit()


def get_session(token: str):
    """Return the session row if the token exists and has not expired, else None."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with db_session() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT s.*, u.id as uid FROM sessions s
            JOIN users u ON s.user_id = u.id
            WHERE s.token = ? AND s.expires_at > ?
        """, (token, now))
        row = cur.fetchone()
        return dict(row) if row else None


def delete_session(token: str):
    """Invalidate a session token on logout."""
    with db_session() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM sessions WHERE token = ?", (token,))
        conn.commit()


def purge_expired_sessions():
    """Housekeeping — delete all rows whose expiry has passed."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with db_session() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM sessions WHERE expires_at < ?", (now,))
        conn.commit()


def get_user_by_id(user_id: int):
    with db_session() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        row = cur.fetchone()
        return dict(row) if row else None
