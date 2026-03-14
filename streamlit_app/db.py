"""
SQLite database layer for local Streamlit app.
Uses sync SQLAlchemy — no asyncpg needed.
"""

import sqlite3
from datetime import date
from pathlib import Path

DB_PATH = Path(__file__).parent / "perfin.db"


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_conn() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS statements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                bank TEXT NOT NULL,
                account_type TEXT NOT NULL,
                period_start TEXT,
                period_end TEXT,
                filename TEXT NOT NULL,
                uploaded_at TEXT NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                statement_id INTEGER NOT NULL REFERENCES statements(id) ON DELETE CASCADE,
                date TEXT NOT NULL,
                description TEXT NOT NULL,
                amount REAL NOT NULL,
                balance REAL,
                polarity TEXT,
                category TEXT NOT NULL DEFAULT 'Other',
                reviewed INTEGER NOT NULL DEFAULT 0
            );
        """)


# --- Statements ---

def insert_statement(bank, account_type, period_start, period_end, filename) -> int:
    with get_conn() as conn:
        cur = conn.execute(
            """INSERT INTO statements (bank, account_type, period_start, period_end, filename)
               VALUES (?, ?, ?, ?, ?)""",
            (bank, account_type,
             period_start.isoformat() if period_start else None,
             period_end.isoformat() if period_end else None,
             filename),
        )
        return cur.lastrowid


def list_statements() -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT s.*, COUNT(t.id) as txn_count
            FROM statements s
            LEFT JOIN transactions t ON t.statement_id = s.id
            GROUP BY s.id
            ORDER BY s.uploaded_at DESC
        """).fetchall()
        return [dict(r) for r in rows]


def delete_statement(statement_id: int):
    with get_conn() as conn:
        conn.execute("DELETE FROM statements WHERE id = ?", (statement_id,))


# --- Transactions ---

def insert_transactions(statement_id: int, txns: list[dict]):
    with get_conn() as conn:
        conn.executemany(
            """INSERT INTO transactions (statement_id, date, description, amount, balance, polarity, category)
               VALUES (:statement_id, :date, :description, :amount, :balance, :polarity, :category)""",
            [{"statement_id": statement_id, **t} for t in txns],
        )


def list_transactions(
    statement_id: int | None = None,
    category: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
) -> list[dict]:
    query = "SELECT * FROM transactions WHERE 1=1"
    params: list = []
    if statement_id:
        query += " AND statement_id = ?"
        params.append(statement_id)
    if category:
        query += " AND category = ?"
        params.append(category)
    if date_from:
        query += " AND date >= ?"
        params.append(date_from)
    if date_to:
        query += " AND date <= ?"
        params.append(date_to)
    query += " ORDER BY date DESC"
    with get_conn() as conn:
        return [dict(r) for r in conn.execute(query, params).fetchall()]


def update_category(txn_id: int, category: str):
    with get_conn() as conn:
        conn.execute(
            "UPDATE transactions SET category = ?, reviewed = 1 WHERE id = ?",
            (category, txn_id),
        )


# --- Analysis ---

def get_category_summary() -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT category,
                   SUM(CASE WHEN amount < 0 THEN ABS(amount) ELSE 0 END) as spend,
                   SUM(CASE WHEN amount > 0 THEN amount ELSE 0 END) as income
            FROM transactions
            GROUP BY category
            ORDER BY spend DESC
        """).fetchall()
        return [dict(r) for r in rows]


def get_monthly_summary(months: int = 6) -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT strftime('%Y-%m', date) as month,
                   SUM(CASE WHEN amount < 0 THEN ABS(amount) ELSE 0 END) as spend,
                   SUM(CASE WHEN amount > 0 THEN amount ELSE 0 END) as income
            FROM transactions
            GROUP BY month
            ORDER BY month DESC
            LIMIT ?
        """, (months,)).fetchall()
        return [dict(r) for r in reversed(rows)]


def get_top_merchants(limit: int = 5) -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT description as merchant,
                   SUM(ABS(amount)) as total,
                   COUNT(*) as count
            FROM transactions
            WHERE amount < 0
            GROUP BY description
            ORDER BY total DESC
            LIMIT ?
        """, (limit,)).fetchall()
        return [dict(r) for r in rows]
