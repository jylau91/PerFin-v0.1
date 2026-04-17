from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date, datetime

from app.parsers.base import ParseError, ParseResult, StatementParser, TxnRow

log = logging.getLogger("perfin.parsers.monopoly")

# Banks in monopoly-core we wrap. Keep these as strings so we don't import
# monopoly at module import time (keeps tests fast when the dep is missing).
MONOPOLY_BANKS: list[str] = ["dbs", "posb", "ocbc", "uob"]

_MARKERS: dict[str, list[str]] = {
    "dbs": ["DBS Bank Ltd", "DBS CARD"],
    "posb": ["POSB"],
    "ocbc": ["OCBC", "Oversea-Chinese Banking"],
    "uob": ["United Overseas Bank", "UOB "],
}


@dataclass
class _Coerced:
    period_start: date
    period_end: date
    opening: int | None
    closing: int | None
    currency: str
    account_number: str
    account_type: str
    transactions: list[TxnRow]
    raw_text: str


def _to_cents(amount: float | int | str) -> int:
    if isinstance(amount, str):
        amount = float(amount.replace(",", ""))
    return int(round(float(amount) * 100))


def _as_date(v) -> date:
    if isinstance(v, date):
        return v
    if isinstance(v, datetime):
        return v.date()
    return datetime.fromisoformat(str(v)).date()


class MonopolyAdapter(StatementParser):
    """Delegates PDF parsing to monopoly-core; normalises output to ParseResult."""

    def __init__(self, bank: str) -> None:
        self.bank_id = bank
        self.parser_id = f"monopoly:{bank}"
        self._markers = _MARKERS.get(bank, [bank.upper()])

    def matches(self, first_page_text: str, meta: dict) -> bool:
        upper = first_page_text.upper()
        return any(m.upper() in upper for m in self._markers)

    def parse(self, pdf_bytes: bytes, password: str | None = None) -> ParseResult:
        try:
            result = self._parse_with_monopoly(pdf_bytes, password)
        except ParseError:
            raise
        except Exception as exc:
            raise ParseError(f"monopoly parse failed for {self.bank_id}: {exc}") from exc
        return ParseResult(
            bank_id=self.bank_id,
            account_type=result.account_type,
            account_number=result.account_number,
            period_start=result.period_start,
            period_end=result.period_end,
            opening_balance_cents=result.opening,
            closing_balance_cents=result.closing,
            currency=result.currency,
            transactions=result.transactions,
            raw_text=result.raw_text,
        )

    def _parse_with_monopoly(self, pdf_bytes: bytes, password: str | None) -> _Coerced:
        try:
            import monopoly.pipeline as pipeline  # type: ignore
        except Exception as exc:
            raise ParseError(
                "monopoly-core not installed. Run `uv sync` (or `pip install monopoly-core`)."
            ) from exc

        # monopoly works on file paths; write a temp file.
        import tempfile

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=True) as tmp:
            tmp.write(pdf_bytes)
            tmp.flush()
            passwords = [password] if password else None
            try:
                parsed = pipeline.Pipeline(tmp.name, passwords=passwords).extract()
            except AttributeError:
                # Older monopoly versions: fall back to public helper.
                from monopoly import parse_statement  # type: ignore

                parsed = parse_statement(tmp.name, passwords=passwords)

        statement = getattr(parsed, "statement", parsed)
        txns_raw = getattr(parsed, "transactions", None) or getattr(statement, "transactions", [])

        transactions: list[TxnRow] = []
        for t in txns_raw:
            txn_date = _as_date(getattr(t, "transaction_date", None) or t["transaction_date"])
            post_date_val = getattr(t, "posting_date", None)
            post_date = _as_date(post_date_val) if post_date_val else None
            description = getattr(t, "description", None) or str(t.get("description", ""))
            amount = getattr(t, "amount", None)
            if amount is None:
                amount = t["amount"]
            transactions.append(
                TxnRow(
                    txn_date=txn_date,
                    post_date=post_date,
                    description=str(description).strip(),
                    raw_description=str(description).strip(),
                    amount_cents=_to_cents(amount),
                )
            )

        period = getattr(statement, "statement_date", None) or getattr(statement, "period", None)
        period_start = _as_date(getattr(statement, "period_start", None) or getattr(period, "start", None))
        period_end = _as_date(getattr(statement, "period_end", None) or getattr(period, "end", None))
        opening = getattr(statement, "opening_balance", None)
        closing = getattr(statement, "closing_balance", None)
        currency = getattr(statement, "currency", None) or "SGD"
        account_number = (
            getattr(statement, "account_number", None)
            or getattr(statement, "account_id", None)
            or ""
        )
        account_type = "credit_card" if "card" in (getattr(statement, "statement_type", "") or "").lower() else "bank"

        return _Coerced(
            period_start=period_start,
            period_end=period_end,
            opening=_to_cents(opening) if opening is not None else None,
            closing=_to_cents(closing) if closing is not None else None,
            currency=str(currency),
            account_number=str(account_number),
            account_type=account_type,
            transactions=transactions,
            raw_text="",
        )
