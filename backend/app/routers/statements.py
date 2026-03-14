from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Statement, Transaction
from app.schemas import StatementOut, UploadResult
from app.services.categoriser import categorise_transactions
from app.services.parser import parse_pdf

router = APIRouter(prefix="/statements", tags=["statements"])


@router.post("", response_model=UploadResult)
async def upload_statement(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted")

    pdf_bytes = await file.read()
    if len(pdf_bytes) == 0:
        raise HTTPException(status_code=400, detail="Empty file")

    try:
        result = parse_pdf(pdf_bytes, file.filename)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Failed to parse PDF: {e}")

    statement = Statement(
        bank=result.bank,
        account_type=result.account_type,
        period_start=result.period_start,
        period_end=result.period_end,
        filename=file.filename,
    )
    db.add(statement)
    await db.flush()  # get statement.id

    descriptions = [t.description for t in result.transactions]
    categories = categorise_transactions(descriptions)

    txns = []
    for txn, category in zip(result.transactions, categories):
        t = Transaction(
            statement_id=statement.id,
            date=txn.date,
            description=txn.description,
            amount=txn.amount,
            balance=txn.balance,
            polarity=txn.polarity,
            category=category,
            raw_category=category,
        )
        db.add(t)
        txns.append(t)

    await db.commit()
    await db.refresh(statement)

    stmt_out = StatementOut(
        id=statement.id,
        bank=statement.bank,
        account_type=statement.account_type,
        period_start=statement.period_start,
        period_end=statement.period_end,
        filename=statement.filename,
        uploaded_at=statement.uploaded_at,
        transaction_count=len(txns),
    )

    return UploadResult(
        statement=stmt_out,
        transactions_parsed=len(txns),
        transactions_categorised=len([c for c in categories if c != "Other"]),
    )


@router.get("", response_model=list[StatementOut])
async def list_statements(db: AsyncSession = Depends(get_db)):
    rows = await db.execute(
        select(Statement, func.count(Transaction.id).label("cnt"))
        .outerjoin(Transaction)
        .group_by(Statement.id)
        .order_by(Statement.uploaded_at.desc())
    )
    out = []
    for stmt, cnt in rows:
        s = StatementOut.model_validate(stmt)
        s.transaction_count = cnt
        out.append(s)
    return out


@router.delete("/{statement_id}", status_code=204)
async def delete_statement(statement_id: int, db: AsyncSession = Depends(get_db)):
    stmt = await db.get(Statement, statement_id)
    if not stmt:
        raise HTTPException(status_code=404, detail="Statement not found")
    await db.delete(stmt)
    await db.commit()
