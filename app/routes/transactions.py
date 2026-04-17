from __future__ import annotations

from fastapi import APIRouter, Form, Request

from app.db.engine import get_conn
from app.deps import render

router = APIRouter(prefix="/transactions", tags=["transactions"])


@router.get("")
def list_txns(request: Request, account_id: int | None = None, statement_id: int | None = None):
    conn = get_conn()
    q = """
      SELECT t.*, a.name AS account_name, c.name AS category_name
      FROM transactions t
      JOIN accounts a ON a.id = t.account_id
      LEFT JOIN categories c ON c.id = t.category_id
      WHERE 1=1
    """
    args: list = []
    if account_id:
        q += " AND t.account_id = ?"
        args.append(account_id)
    if statement_id:
        q += " AND t.statement_id = ?"
        args.append(statement_id)
    q += " ORDER BY t.txn_date DESC LIMIT 500"
    rows = conn.execute(q, args).fetchall()
    categories = conn.execute("SELECT * FROM categories ORDER BY name").fetchall()
    return render(
        request,
        "transactions/list.html",
        txns=rows,
        categories=categories,
        account_id=account_id,
        statement_id=statement_id,
    )


@router.post("/{txn_id}/category")
def set_category(request: Request, txn_id: int, category_id: int = Form(...)):
    get_conn().execute("UPDATE transactions SET category_id=? WHERE id=?", (category_id, txn_id))
    return {"ok": True}
