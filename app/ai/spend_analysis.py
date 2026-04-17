from __future__ import annotations

from datetime import date, timedelta

from app.ai.anonymise import anonymise_merchant
from app.ai.client import run_feature
from app.db.engine import get_conn

SYSTEM = (
    "You are a personal finance analyst for a Singapore-based user. "
    "Given anonymised monthly spending aggregates, return strict JSON: "
    '{"insights":[{"title":str,"detail":str}],"recommendations":[{"area":str,"action":str,"estimated_monthly_saving_sgd":number}]}. '
    "Be concrete. Use SGD. Do not invent numbers beyond what's provided."
)


def _month_buckets(months: int = 3) -> dict:
    conn = get_conn()
    since = (date.today().replace(day=1) - timedelta(days=31 * months)).isoformat()
    by_cat = conn.execute(
        """
        SELECT strftime('%Y-%m', txn_date) AS m,
               COALESCE(c.name, 'Uncategorised') AS category,
               SUM(CASE WHEN t.amount_cents > 0 THEN t.amount_cents ELSE 0 END) AS spend_cents
        FROM transactions t LEFT JOIN categories c ON c.id = t.category_id
        WHERE txn_date >= ?
        GROUP BY m, category
        ORDER BY m, category
        """,
        (since,),
    ).fetchall()
    top_merchants = conn.execute(
        """
        SELECT description, SUM(amount_cents) AS spend_cents, COUNT(*) AS n
        FROM transactions
        WHERE txn_date >= ? AND amount_cents > 0
        GROUP BY description
        ORDER BY spend_cents DESC
        LIMIT 30
        """,
        (since,),
    ).fetchall()
    return {
        "months": [
            {"month": r["m"], "category": r["category"], "spend_sgd": r["spend_cents"] / 100}
            for r in by_cat
        ],
        "top_merchants": [
            {"merchant": anonymise_merchant(r["description"]),
             "spend_sgd": r["spend_cents"] / 100, "count": r["n"]}
            for r in top_merchants
        ],
    }


def analyse() -> dict:
    payload = _month_buckets()
    return run_feature("spend_analysis", payload, SYSTEM)
