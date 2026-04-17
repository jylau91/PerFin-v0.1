from __future__ import annotations

from datetime import date, timedelta

from app.ai.client import run_feature
from app.db.engine import get_conn

SYSTEM = (
    "You are a Singapore-based personal finance coach. Given 3-month income/expense trend, "
    "return strict JSON: "
    '{"target_monthly_save_sgd":number,"plan_markdown":str,"weekly_actions":[str,str,str,str]}. '
    "Keep the plan concrete, specific, and compatible with Singapore (CPF, SRS hints only where obvious)."
)


def _trend() -> dict:
    conn = get_conn()
    since = (date.today().replace(day=1) - timedelta(days=95)).isoformat()
    rows = conn.execute(
        """
        SELECT strftime('%Y-%m', txn_date) AS m,
               SUM(CASE WHEN amount_cents > 0 THEN amount_cents ELSE 0 END) AS out_cents,
               SUM(CASE WHEN amount_cents < 0 THEN -amount_cents ELSE 0 END) AS in_cents
        FROM transactions
        WHERE txn_date >= ?
        GROUP BY m
        ORDER BY m
        """,
        (since,),
    ).fetchall()
    return {
        "months": [
            {"month": r["m"], "income_sgd": r["in_cents"] / 100, "expense_sgd": r["out_cents"] / 100}
            for r in rows
        ]
    }


def generate() -> dict:
    payload = _trend()
    return run_feature("save_plan", payload, SYSTEM, heavy=True)
