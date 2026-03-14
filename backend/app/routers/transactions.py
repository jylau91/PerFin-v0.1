from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Transaction
from app.schemas import TransactionCategoryUpdate, TransactionOut

router = APIRouter(prefix="/transactions", tags=["transactions"])


@router.get("", response_model=list[TransactionOut])
async def list_transactions(
    statement_id: Optional[int] = Query(None),
    category: Optional[str] = Query(None),
    bank: Optional[str] = Query(None),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    limit: int = Query(200, le=1000),
    offset: int = Query(0),
    db: AsyncSession = Depends(get_db),
):
    q = select(Transaction).order_by(Transaction.date.desc())

    if statement_id is not None:
        q = q.where(Transaction.statement_id == statement_id)
    if category:
        q = q.where(Transaction.category == category)
    if date_from:
        q = q.where(Transaction.date >= date_from)
    if date_to:
        q = q.where(Transaction.date <= date_to)

    q = q.offset(offset).limit(limit)
    rows = await db.execute(q)
    return rows.scalars().all()


@router.patch("/{transaction_id}", response_model=TransactionOut)
async def update_category(
    transaction_id: int,
    body: TransactionCategoryUpdate,
    db: AsyncSession = Depends(get_db),
):
    txn = await db.get(Transaction, transaction_id)
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")
    txn.category = body.category
    txn.reviewed = True
    await db.commit()
    await db.refresh(txn)
    return txn
