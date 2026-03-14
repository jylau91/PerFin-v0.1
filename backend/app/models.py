from datetime import date, datetime
from enum import Enum

from sqlalchemy import Date, DateTime, Float, ForeignKey, Integer, String, Boolean, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Bank(str, Enum):
    DBS = "DBS"
    POSB = "POSB"
    OCBC = "OCBC"
    UOB = "UOB"
    MAYBANK = "MAYBANK"
    UNKNOWN = "UNKNOWN"


class AccountType(str, Enum):
    CREDIT = "credit"
    DEBIT = "debit"


class Category(str, Enum):
    FOOD_DRINK = "Food & Drink"
    TRANSPORT = "Transport"
    SHOPPING = "Shopping"
    GROCERIES = "Groceries"
    HEALTHCARE = "Healthcare"
    ENTERTAINMENT = "Entertainment"
    BILLS_UTILITIES = "Bills & Utilities"
    TRAVEL = "Travel"
    EDUCATION = "Education"
    INCOME = "Income"
    OTHER = "Other"


class Statement(Base):
    __tablename__ = "statements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    bank: Mapped[str] = mapped_column(String(20))
    account_type: Mapped[str] = mapped_column(String(10))
    period_start: Mapped[date | None] = mapped_column(Date, nullable=True)
    period_end: Mapped[date | None] = mapped_column(Date, nullable=True)
    filename: Mapped[str] = mapped_column(String(255))
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    transactions: Mapped[list["Transaction"]] = relationship(
        back_populates="statement", cascade="all, delete-orphan"
    )


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    statement_id: Mapped[int] = mapped_column(Integer, ForeignKey("statements.id"))
    date: Mapped[date] = mapped_column(Date)
    description: Mapped[str] = mapped_column(String(500))
    amount: Mapped[float] = mapped_column(Float)
    balance: Mapped[float | None] = mapped_column(Float, nullable=True)
    polarity: Mapped[str | None] = mapped_column(String(5), nullable=True)  # CR / DR
    category: Mapped[str] = mapped_column(String(50), default="Other")
    raw_category: Mapped[str | None] = mapped_column(String(50), nullable=True)
    reviewed: Mapped[bool] = mapped_column(Boolean, default=False)

    statement: Mapped["Statement"] = relationship(back_populates="transactions")
