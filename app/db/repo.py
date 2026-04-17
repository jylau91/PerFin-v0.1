from __future__ import annotations

import hashlib
import sqlite3
from collections.abc import Iterable
from dataclasses import dataclass

from app.db.engine import get_conn, tx


@dataclass
class Account:
    id: int
    name: str
    type: str
    bank_id: str | None
    currency: str


def ensure_account(name: str, type_: str, bank_id: str | None, currency: str = "SGD") -> int:
    conn = get_conn()
    row = conn.execute(
        "SELECT id FROM accounts WHERE name = ? AND type = ? AND bank_id IS ?",
        (name, type_, bank_id),
    ).fetchone()
    if row:
        return int(row["id"])
    cur = conn.execute(
        "INSERT INTO accounts (name, type, bank_id, currency) VALUES (?, ?, ?, ?)",
        (name, type_, bank_id, currency),
    )
    return int(cur.lastrowid)


def list_accounts() -> list[sqlite3.Row]:
    return list(get_conn().execute("SELECT * FROM accounts ORDER BY type, name").fetchall())


def txn_hash(account_id: int, txn_date: str, amount_cents: int, raw_desc: str) -> str:
    h = hashlib.sha256(f"{account_id}|{txn_date}|{amount_cents}|{raw_desc}".encode()).hexdigest()
    return h


def insert_statement(
    account_id: int,
    period_start: str,
    period_end: str,
    opening_cents: int | None,
    closing_cents: int | None,
    source_pdf_path: str | None,
    parser_id: str,
) -> int | None:
    conn = get_conn()
    try:
        cur = conn.execute(
            """
            INSERT INTO statements
              (account_id, period_start, period_end, opening_balance_cents,
               closing_balance_cents, source_pdf_path, parser_id)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (account_id, period_start, period_end, opening_cents, closing_cents,
             source_pdf_path, parser_id),
        )
        return int(cur.lastrowid)
    except sqlite3.IntegrityError:
        row = conn.execute(
            "SELECT id FROM statements WHERE account_id=? AND period_start=? AND period_end=?",
            (account_id, period_start, period_end),
        ).fetchone()
        return int(row["id"]) if row else None


def insert_transactions(rows: Iterable[dict]) -> tuple[int, int]:
    inserted = 0
    skipped = 0
    with tx() as conn:
        for r in rows:
            try:
                conn.execute(
                    """
                    INSERT INTO transactions
                      (statement_id, account_id, txn_date, post_date, description,
                       raw_description, amount_cents, currency, hash)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        r.get("statement_id"),
                        r["account_id"],
                        r["txn_date"],
                        r.get("post_date"),
                        r["description"],
                        r["raw_description"],
                        r["amount_cents"],
                        r.get("currency", "SGD"),
                        r["hash"],
                    ),
                )
                inserted += 1
            except sqlite3.IntegrityError:
                skipped += 1
    return inserted, skipped


def update_reconcile(statement_id: int, status: str, delta_cents: int | None) -> None:
    get_conn().execute(
        "UPDATE statements SET reconcile_status=?, reconcile_delta_cents=? WHERE id=?",
        (status, delta_cents, statement_id),
    )


def already_ingested(source: str, external_id: str, filename: str) -> bool:
    row = get_conn().execute(
        "SELECT 1 FROM ingest_sources WHERE source=? AND external_id=? AND attachment_filename=?",
        (source, external_id, filename),
    ).fetchone()
    return row is not None


def record_ingest(
    source: str,
    external_id: str | None,
    raw_subject: str | None,
    raw_sender: str | None,
    attachment_filename: str | None,
    statement_id: int | None,
    error: str | None,
) -> None:
    try:
        get_conn().execute(
            """
            INSERT INTO ingest_sources
              (source, external_id, raw_subject, raw_sender, attachment_filename, statement_id, error)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (source, external_id, raw_subject, raw_sender, attachment_filename, statement_id, error),
        )
    except sqlite3.IntegrityError:
        pass


def record_poll(source: str, matched: int, ingested: int, skipped: int, errored: int, note: str = "") -> None:
    get_conn().execute(
        "INSERT INTO poll_log (source, matched, ingested, skipped, errored, note) VALUES (?,?,?,?,?,?)",
        (source, matched, ingested, skipped, errored, note),
    )


def last_poll(source: str) -> sqlite3.Row | None:
    return get_conn().execute(
        "SELECT * FROM poll_log WHERE source=? ORDER BY ran_at DESC LIMIT 1",
        (source,),
    ).fetchone()


def ai_cache_get(key: str) -> sqlite3.Row | None:
    return get_conn().execute("SELECT * FROM ai_cache WHERE key=?", (key,)).fetchone()


def ai_cache_put(key: str, model: str, feature: str, request_json: str, response_json: str,
                 tokens_in: int, tokens_out: int) -> None:
    get_conn().execute(
        """
        INSERT OR REPLACE INTO ai_cache
          (key, model, feature, request_json, response_json, tokens_in, tokens_out)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (key, model, feature, request_json, response_json, tokens_in, tokens_out),
    )


def ai_usage_add(month: str, tokens_in: int, tokens_out: int) -> None:
    get_conn().execute(
        """
        INSERT INTO ai_usage (month, tokens_in, tokens_out)
        VALUES (?, ?, ?)
        ON CONFLICT(month) DO UPDATE SET
          tokens_in = ai_usage.tokens_in + excluded.tokens_in,
          tokens_out = ai_usage.tokens_out + excluded.tokens_out
        """,
        (month, tokens_in, tokens_out),
    )


def ai_usage_for(month: str) -> tuple[int, int]:
    row = get_conn().execute("SELECT tokens_in, tokens_out FROM ai_usage WHERE month=?", (month,)).fetchone()
    if not row:
        return 0, 0
    return int(row["tokens_in"]), int(row["tokens_out"])
