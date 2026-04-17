from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date


@dataclass
class TxnRow:
    txn_date: date
    post_date: date | None
    description: str
    raw_description: str
    amount_cents: int
    currency: str = "SGD"


@dataclass
class ParseResult:
    bank_id: str
    account_type: str  # 'bank' or 'credit_card'
    account_number: str
    period_start: date
    period_end: date
    opening_balance_cents: int | None
    closing_balance_cents: int | None
    currency: str
    transactions: list[TxnRow] = field(default_factory=list)
    raw_text: str = ""


class StatementParser(ABC):
    bank_id: str = ""
    parser_id: str = ""

    @abstractmethod
    def matches(self, first_page_text: str, meta: dict) -> bool: ...

    @abstractmethod
    def parse(self, pdf_bytes: bytes, password: str | None = None) -> ParseResult: ...


class ParseError(Exception):
    """Raised when a parser cannot extract a valid statement."""
