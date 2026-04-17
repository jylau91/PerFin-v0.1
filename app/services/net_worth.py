from __future__ import annotations

from datetime import date

from app.db.engine import get_conn


def cash_total_cents() -> int:
    conn = get_conn()
    row = conn.execute(
        """
        SELECT COALESCE(SUM(s.closing_balance_cents), 0) AS total FROM (
          SELECT account_id, MAX(period_end) AS last_end FROM statements GROUP BY account_id
        ) t
        JOIN statements s ON s.account_id = t.account_id AND s.period_end = t.last_end
        JOIN accounts a ON a.id = s.account_id
        WHERE a.type = 'bank'
        """
    ).fetchone()
    return int(row["total"] or 0)


def credit_card_owed_cents() -> int:
    conn = get_conn()
    row = conn.execute(
        """
        SELECT COALESCE(SUM(s.closing_balance_cents), 0) AS total FROM (
          SELECT account_id, MAX(period_end) AS last_end FROM statements GROUP BY account_id
        ) t
        JOIN statements s ON s.account_id = t.account_id AND s.period_end = t.last_end
        JOIN accounts a ON a.id = s.account_id
        WHERE a.type = 'credit_card'
        """
    ).fetchone()
    return int(row["total"] or 0)


def investments_total_cents() -> int:
    conn = get_conn()
    rows = conn.execute(
        """
        SELECT h.symbol, SUM(h.quantity) AS qty,
               (SELECT close_cents FROM prices p WHERE p.symbol = h.symbol
                 ORDER BY p.as_of_date DESC LIMIT 1) AS close_cents
        FROM holdings h
        GROUP BY h.symbol
        """
    ).fetchall()
    total = 0
    for r in rows:
        qty = float(r["qty"] or 0)
        close = int(r["close_cents"] or 0)
        total += int(round(qty * close))
    return total


def snapshot_today() -> tuple[int, int, int]:
    cash = cash_total_cents() - credit_card_owed_cents()
    inv = investments_total_cents()
    total = cash + inv
    get_conn().execute(
        """
        INSERT INTO net_worth_snapshots (as_of_date, cash_cents, investments_cents, total_cents)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(as_of_date) DO UPDATE SET
          cash_cents=excluded.cash_cents,
          investments_cents=excluded.investments_cents,
          total_cents=excluded.total_cents
        """,
        (date.today().isoformat(), cash, inv, total),
    )
    return cash, inv, total
