"""
database.py
Handles all SQLite database operations for the AI-Powered College Resource
Sharing Platform: schema creation, seeding, and CRUD helpers for resources,
students, transactions, and search history.
"""

import sqlite3
import os
from datetime import datetime, date

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "resource_platform.db")


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create all tables if they do not already exist."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = get_connection()
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

    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# Resources
# ---------------------------------------------------------------------------
def add_resource(item_name, category, department, semester, condition,
                  description, availability_status, uploader_name, estimated_value):
    conn = get_connection()
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
    new_id = cur.lastrowid
    conn.close()
    return new_id


def get_all_resources(only_available=False):
    conn = get_connection()
    cur = conn.cursor()
    if only_available:
        cur.execute("SELECT * FROM resources WHERE availability_status = 'Available' ORDER BY id DESC")
    else:
        cur.execute("SELECT * FROM resources ORDER BY id DESC")
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_resource_by_id(resource_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM resources WHERE id = ?", (resource_id,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def update_resource_status(resource_id, status):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE resources SET availability_status = ? WHERE id = ?", (status, resource_id))
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# Students
# ---------------------------------------------------------------------------
def add_student(name, department, semester, interests=""):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO students (name, department, semester, interests)
        VALUES (?, ?, ?, ?)
    """, (name, department, semester, interests))
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    return new_id


def get_all_students():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM students ORDER BY id")
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_student_by_name(name):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM students WHERE name = ?", (name,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


# ---------------------------------------------------------------------------
# Transactions (resource exchanges)
# ---------------------------------------------------------------------------
def record_transaction(resource_id, recipient_name, money_saved):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO transactions (resource_id, recipient_name, exchange_date, money_saved)
        VALUES (?, ?, ?, ?)
    """, (resource_id, recipient_name, datetime.now().strftime("%Y-%m-%d"), money_saved))
    conn.commit()
    conn.close()
    update_resource_status(resource_id, "Exchanged")


def get_all_transactions():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT t.id, t.resource_id, r.item_name, r.category, r.department,
               t.recipient_name, t.exchange_date, t.money_saved
        FROM transactions t
        JOIN resources r ON t.resource_id = r.id
        ORDER BY t.exchange_date DESC
    """)
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Search history (used to refine recommendations)
# ---------------------------------------------------------------------------
def log_search(student_name, query):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO search_history (student_name, query, timestamp)
        VALUES (?, ?, ?)
    """, (student_name, query, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    conn.close()


def get_search_history(student_name=None):
    conn = get_connection()
    cur = conn.cursor()
    if student_name:
        cur.execute("SELECT * FROM search_history WHERE student_name = ? ORDER BY id DESC", (student_name,))
    else:
        cur.execute("SELECT * FROM search_history ORDER BY id DESC")
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Demand history (used to train the demand-prediction model)
# ---------------------------------------------------------------------------
def add_demand_record(category, department, month, year, requests_count):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO demand_history (category, department, month, year, requests_count)
        VALUES (?, ?, ?, ?, ?)
    """, (category, department, month, year, requests_count))
    conn.commit()
    conn.close()


def get_demand_history():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM demand_history")
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def is_db_seeded():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) as c FROM resources")
    count = cur.fetchone()["c"]
    conn.close()
    return count > 0
