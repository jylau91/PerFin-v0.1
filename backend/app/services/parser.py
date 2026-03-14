"""
Wrapper around monopoly-core for parsing Singapore bank PDF statements.
Extracts transactions and basic statement metadata.
"""

import tempfile
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from monopoly.pipeline import Pipeline


@dataclass
class ParsedTransaction:
    date: date
    description: str
    amount: float
    balance: float | None
    polarity: str | None  # "CR" / "DR" / None


@dataclass
class ParseResult:
    bank: str
    account_type: str  # "credit" | "debit"
    period_start: date | None
    period_end: date | None
    transactions: list[ParsedTransaction]


def _detect_account_type(pipeline: Pipeline) -> str:
    """Determine if this is a credit or debit statement."""
    try:
        handler = pipeline.statement
        class_name = type(handler).__name__.lower()
        if "credit" in class_name:
            return "credit"
        return "debit"
    except Exception:
        return "unknown"


def _detect_bank(pipeline: Pipeline) -> str:
    """Extract bank name from the pipeline's bank handler."""
    try:
        bank_class = type(pipeline.statement).__mro__
        for cls in bank_class:
            name = cls.__name__.upper()
            for bank in ("DBS", "POSB", "OCBC", "UOB", "MAYBANK"):
                if bank in name:
                    return bank
        return "UNKNOWN"
    except Exception:
        return "UNKNOWN"


def parse_pdf(pdf_bytes: bytes, filename: str) -> ParseResult:
    """
    Parse a Singapore bank PDF statement from raw bytes.
    Returns structured ParseResult with transactions.
    """
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp.write(pdf_bytes)
        tmp_path = Path(tmp.name)

    try:
        pipeline = Pipeline(tmp_path)
        transactions_raw = pipeline.get_transactions()

        bank = _detect_bank(pipeline)
        account_type = _detect_account_type(pipeline)

        # Extract period from statement metadata
        period_start: date | None = None
        period_end: date | None = None
        try:
            stmt = pipeline.statement
            if hasattr(stmt, "statement_date"):
                period_end = stmt.statement_date
            if hasattr(stmt, "prev_statement_date"):
                period_start = stmt.prev_statement_date
        except Exception:
            pass

        parsed: list[ParsedTransaction] = []
        for txn in transactions_raw:
            try:
                txn_date = txn.date
                if isinstance(txn_date, str):
                    from datetime import datetime
                    txn_date = datetime.fromisoformat(txn_date).date()

                parsed.append(
                    ParsedTransaction(
                        date=txn_date,
                        description=txn.description,
                        amount=float(txn.amount),
                        balance=float(txn.balance) if txn.balance else None,
                        polarity=getattr(txn, "polarity", None),
                    )
                )
            except Exception:
                continue

        return ParseResult(
            bank=bank,
            account_type=account_type,
            period_start=period_start,
            period_end=period_end,
            transactions=parsed,
        )
    finally:
        tmp_path.unlink(missing_ok=True)
