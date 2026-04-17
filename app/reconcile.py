from __future__ import annotations

from app.db.engine import get_conn
from app.db.repo import update_reconcile

TOLERANCE_CENTS = 1


def reconcile_statement(statement_id: int) -> tuple[str, int | None]:
    conn = get_conn()
    stmt = conn.execute(
        "SELECT opening_balance_cents, closing_balance_cents FROM statements WHERE id=?",
        (statement_id,),
    ).fetchone()
    if not stmt:
        return "unknown", None
    opening = stmt["opening_balance_cents"]
    closing = stmt["closing_balance_cents"]
    if opening is None or closing is None:
        update_reconcile(statement_id, "unknown", None)
        return "unknown", None
    total_row = conn.execute(
        "SELECT COALESCE(SUM(amount_cents), 0) AS s FROM transactions WHERE statement_id=?",
        (statement_id,),
    ).fetchone()
    txn_sum = int(total_row["s"])
    # For bank accounts: closing = opening + sum(signed_txns).
    # For credit cards: closing = opening + sum(charges) - sum(payments).
    # Our signed amounts handle both if parsers emit charges positive, payments negative.
    expected_closing = opening + txn_sum
    delta = closing - expected_closing
    status = "ok" if abs(delta) <= TOLERANCE_CENTS else "mismatch"
    update_reconcile(statement_id, status, delta)
    return status, delta
