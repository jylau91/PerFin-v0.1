from __future__ import annotations

import csv
import io
import json
from dataclasses import dataclass
from datetime import date

from app.db.engine import get_conn

REQUIRED_FIELDS = {"symbol", "quantity"}
OPTIONAL_FIELDS = {"avg_cost", "currency", "as_of_date", "account"}


@dataclass
class ImportResult:
    inserted: int
    errors: list[str]


def list_broker_profiles() -> list[dict]:
    rows = get_conn().execute("SELECT * FROM broker_profiles ORDER BY broker_name").fetchall()
    return [dict(r) for r in rows]


def get_profile(broker_name: str) -> dict | None:
    row = get_conn().execute(
        "SELECT * FROM broker_profiles WHERE broker_name = ?", (broker_name,)
    ).fetchone()
    if not row:
        return None
    d = dict(row)
    d["column_map"] = json.loads(d.pop("column_map_json"))
    return d


def save_profile(broker_name: str, column_map: dict[str, str]) -> None:
    get_conn().execute(
        """
        INSERT INTO broker_profiles (broker_name, column_map_json)
        VALUES (?, ?)
        ON CONFLICT(broker_name) DO UPDATE SET column_map_json=excluded.column_map_json
        """,
        (broker_name, json.dumps(column_map)),
    )


def sniff_columns(csv_bytes: bytes) -> list[str]:
    text = csv_bytes.decode("utf-8-sig", errors="replace")
    reader = csv.reader(io.StringIO(text))
    header = next(reader, [])
    return [h.strip() for h in header]


def import_csv(csv_bytes: bytes, column_map: dict[str, str], account_name: str) -> ImportResult:
    """column_map maps our field name -> CSV column name."""
    missing = REQUIRED_FIELDS - set(column_map)
    if missing:
        return ImportResult(0, [f"missing required field(s): {sorted(missing)}"])

    from app.db.repo import ensure_account

    account_id = ensure_account(account_name, "investment", None, "SGD")
    text = csv_bytes.decode("utf-8-sig", errors="replace")
    reader = csv.DictReader(io.StringIO(text))
    conn = get_conn()
    inserted = 0
    errors: list[str] = []
    for row in reader:
        try:
            symbol = row[column_map["symbol"]].strip().upper()
            qty = float(row[column_map["quantity"]].replace(",", ""))
            avg_cost = None
            if "avg_cost" in column_map and row.get(column_map["avg_cost"]):
                avg_cost = int(round(float(row[column_map["avg_cost"]].replace(",", "")) * 100))
            currency = (row.get(column_map.get("currency", ""), "") or "SGD").strip() or "SGD"
            as_of = (row.get(column_map.get("as_of_date", ""), "") or date.today().isoformat()).strip()
            conn.execute(
                """
                INSERT INTO holdings (account_id, symbol, quantity, avg_cost_cents, currency, as_of_date)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (account_id, symbol, qty, avg_cost, currency, as_of),
            )
            inserted += 1
        except Exception as exc:
            errors.append(f"row {reader.line_num}: {exc}")
    return ImportResult(inserted, errors)
