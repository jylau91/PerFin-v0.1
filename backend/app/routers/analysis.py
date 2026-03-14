from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Transaction, Statement
from app.schemas import AnalysisSummaryOut, CategorySummary, MonthlySummary, TopMerchant

router = APIRouter(prefix="/analysis", tags=["analysis"])


def _build_date_filter(q, date_from, date_to):
    if date_from:
        q = q.where(Transaction.date >= date_from)
    if date_to:
        q = q.where(Transaction.date <= date_to)
    return q


@router.get("/summary", response_model=AnalysisSummaryOut)
async def get_summary(
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    q = select(
        Transaction.category,
        func.sum(Transaction.amount).label("total"),
        func.count(Transaction.id).label("count"),
    ).group_by(Transaction.category)
    q = _build_date_filter(q, date_from, date_to)

    rows = (await db.execute(q)).all()

    by_category = [
        CategorySummary(category=r.category, total=round(r.total, 2), count=r.count)
        for r in rows
    ]

    # Separate income vs. spend (Income category = positive cashflow)
    total_income = sum(c.total for c in by_category if c.category == "Income")
    total_spend = sum(c.total for c in by_category if c.category != "Income")

    return AnalysisSummaryOut(
        period_start=date_from,
        period_end=date_to,
        total_spend=round(total_spend, 2),
        total_income=round(total_income, 2),
        by_category=sorted(by_category, key=lambda x: x.total, reverse=True),
    )


@router.get("/monthly", response_model=list[MonthlySummary])
async def get_monthly(
    months: int = Query(6, ge=1, le=24),
    db: AsyncSession = Depends(get_db),
):
    # Get per-month, per-category totals
    q = select(
        func.to_char(Transaction.date, "YYYY-MM").label("month"),
        Transaction.category,
        func.sum(Transaction.amount).label("total"),
        func.count(Transaction.id).label("count"),
    ).group_by("month", Transaction.category).order_by("month")

    rows = (await db.execute(q)).all()

    # Aggregate into MonthlySummary objects
    monthly: dict[str, MonthlySummary] = {}
    for row in rows:
        if row.month not in monthly:
            monthly[row.month] = MonthlySummary(month=row.month, total=0, by_category=[])
        cat = CategorySummary(
            category=row.category, total=round(row.total, 2), count=row.count
        )
        monthly[row.month].by_category.append(cat)
        if row.category != "Income":
            monthly[row.month].total += row.total

    result = sorted(monthly.values(), key=lambda x: x.month)
    return result[-months:]


@router.get("/top-merchants", response_model=list[TopMerchant])
async def get_top_merchants(
    limit: int = Query(10, ge=1, le=50),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    q = select(
        Transaction.description,
        func.sum(Transaction.amount).label("total"),
        func.count(Transaction.id).label("count"),
    ).group_by(Transaction.description)
    q = _build_date_filter(q, date_from, date_to)
    q = q.order_by(func.sum(Transaction.amount).desc()).limit(limit)

    rows = (await db.execute(q)).all()
    return [
        TopMerchant(description=r.description, total=round(r.total, 2), count=r.count)
        for r in rows
    ]
