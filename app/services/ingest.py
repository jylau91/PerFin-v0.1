from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from app.config import get_settings
from app.db.repo import (
    ensure_account,
    insert_statement,
    insert_transactions,
    record_ingest,
    txn_hash,
)
from app.parsers.base import ParseError
from app.parsers.registry import detect_bank
from app.reconcile import reconcile_statement

log = logging.getLogger("perfin.ingest")


@dataclass
class IngestOutcome:
    ok: bool
    statement_id: int | None
    parser_id: str | None
    inserted: int
    skipped: int
    reconcile_status: str | None
    error: str | None = None


def _store_pdf(pdf_bytes: bytes, filename: str) -> Path:
    settings = get_settings()
    dest = settings.PERFIN_DB_PATH.parent / "statements" / filename
    dest.parent.mkdir(parents=True, exist_ok=True)
    # Avoid overwrite: suffix with count if needed.
    if dest.exists():
        stem, suffix = dest.stem, dest.suffix
        n = 1
        while dest.exists():
            dest = dest.with_name(f"{stem}_{n}{suffix}")
            n += 1
    dest.write_bytes(pdf_bytes)
    return dest


def ingest_pdf(
    *,
    pdf_bytes: bytes,
    filename: str,
    password: str | None,
    source: str,
    external_id: str | None,
    raw_subject: str | None,
    raw_sender: str | None,
) -> IngestOutcome:
    try:
        parser = detect_bank(pdf_bytes, password)
    except ParseError as exc:
        record_ingest(source, external_id, raw_subject, raw_sender, filename, None, str(exc))
        return IngestOutcome(False, None, None, 0, 0, None, str(exc))

    try:
        parsed = parser.parse(pdf_bytes, password)
    except ParseError as exc:
        record_ingest(source, external_id, raw_subject, raw_sender, filename, None, str(exc))
        return IngestOutcome(False, None, parser.parser_id, 0, 0, None, str(exc))

    pdf_path = _store_pdf(pdf_bytes, filename)
    account_name = f"{parsed.bank_id.upper()} {parsed.account_number or 'default'}"
    account_id = ensure_account(
        name=account_name,
        type_=parsed.account_type,
        bank_id=parsed.bank_id,
        currency=parsed.currency,
    )
    stmt_id = insert_statement(
        account_id=account_id,
        period_start=parsed.period_start.isoformat(),
        period_end=parsed.period_end.isoformat(),
        opening_cents=parsed.opening_balance_cents,
        closing_cents=parsed.closing_balance_cents,
        source_pdf_path=str(pdf_path),
        parser_id=parser.parser_id,
    )
    rows = []
    for t in parsed.transactions:
        rows.append(
            {
                "statement_id": stmt_id,
                "account_id": account_id,
                "txn_date": t.txn_date.isoformat(),
                "post_date": t.post_date.isoformat() if t.post_date else None,
                "description": t.description,
                "raw_description": t.raw_description,
                "amount_cents": t.amount_cents,
                "currency": t.currency,
                "hash": txn_hash(account_id, t.txn_date.isoformat(), t.amount_cents, t.raw_description),
            }
        )
    inserted, skipped = insert_transactions(rows)
    status, _ = reconcile_statement(stmt_id) if stmt_id else ("unknown", None)
    record_ingest(source, external_id, raw_subject, raw_sender, filename, stmt_id, None)
    return IngestOutcome(True, stmt_id, parser.parser_id, inserted, skipped, status, None)
