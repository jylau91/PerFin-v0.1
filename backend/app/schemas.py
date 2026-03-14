from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel


# ── Statement ──────────────────────────────────────────────────────────────────

class StatementBase(BaseModel):
    bank: str
    account_type: str
    period_start: Optional[date] = None
    period_end: Optional[date] = None
    filename: str


class StatementOut(StatementBase):
    id: int
    uploaded_at: datetime
    transaction_count: int = 0

    model_config = {"from_attributes": True}


# ── Transaction ────────────────────────────────────────────────────────────────

class TransactionOut(BaseModel):
    id: int
    statement_id: int
    date: date
    description: str
    amount: float
    balance: Optional[float] = None
    polarity: Optional[str] = None
    category: str
    raw_category: Optional[str] = None
    reviewed: bool

    model_config = {"from_attributes": True}


class TransactionCategoryUpdate(BaseModel):
    category: str


# ── Analysis ───────────────────────────────────────────────────────────────────

class CategorySummary(BaseModel):
    category: str
    total: float
    count: int


class MonthlySummary(BaseModel):
    month: str          # "2024-01"
    total: float
    by_category: list[CategorySummary]


class TopMerchant(BaseModel):
    description: str
    total: float
    count: int


class AnalysisSummaryOut(BaseModel):
    period_start: Optional[date]
    period_end: Optional[date]
    total_spend: float
    total_income: float
    by_category: list[CategorySummary]


# ── Upload response ────────────────────────────────────────────────────────────

class UploadResult(BaseModel):
    statement: StatementOut
    transactions_parsed: int
    transactions_categorised: int
