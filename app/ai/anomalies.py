from __future__ import annotations

from datetime import date, timedelta
from statistics import mean, pstdev

from app.ai.anonymise import anonymise_merchant
from app.ai.client import run_feature
from app.db.engine import get_conn

SYSTEM = (
    "You are a fraud-detection assistant. Given anonymised transactions with precomputed "
    "category z-scores, return strict JSON: "
    '{"flagged":[{"hash":str,"reason":str,"confidence":number}]}. '
    "Confidence is 0..1. Only flag rows that look genuinely suspicious."
)


def _features() -> dict:
    conn = get_conn()
    since = (date.today() - timedelta(days=90)).isoformat()
    rows = conn.execute(
        """
        SELECT t.hash, t.txn_date, t.description, t.amount_cents,
               COALESCE(c.name, 'Uncategorised') AS category
        FROM transactions t LEFT JOIN categories c ON c.id = t.category_id
        WHERE t.txn_date >= ? AND t.amount_cents > 0
        """,
        (since,),
    ).fetchall()
    by_cat: dict[str, list[int]] = {}
    for r in rows:
        by_cat.setdefault(r["category"], []).append(int(r["amount_cents"]))
    stats = {c: (mean(v), pstdev(v) or 1) for c, v in by_cat.items()}
    out = []
    for r in rows:
        mu, sd = stats[r["category"]]
        z = (int(r["amount_cents"]) - mu) / sd if sd else 0.0
        out.append(
            {
                "hash": r["hash"],
                "date": r["txn_date"],
                "merchant": anonymise_merchant(r["description"]),
                "amount_sgd": int(r["amount_cents"]) / 100,
                "category": r["category"],
                "z_score": round(z, 2),
            }
        )
    out.sort(key=lambda x: x["z_score"], reverse=True)
    return {"transactions": out[:80]}


def flag() -> dict:
    payload = _features()
    return run_feature("anomalies", payload, SYSTEM)
