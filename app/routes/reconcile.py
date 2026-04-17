from __future__ import annotations

from fastapi import APIRouter, Request

from app.db.engine import get_conn
from app.deps import render
from app.reconcile import reconcile_statement

router = APIRouter(prefix="/reconcile", tags=["reconcile"])


@router.get("")
def reconcile_list(request: Request):
    conn = get_conn()
    rows = conn.execute(
        """
        SELECT s.*, a.name AS account_name
        FROM statements s JOIN accounts a ON a.id = s.account_id
        ORDER BY s.period_end DESC LIMIT 50
        """
    ).fetchall()
    return render(request, "reconcile.html", statements=rows)


@router.post("/{statement_id}/run")
def run_one(statement_id: int):
    status, delta = reconcile_statement(statement_id)
    return {"status": status, "delta_cents": delta}
