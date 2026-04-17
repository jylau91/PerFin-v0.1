from __future__ import annotations

from fastapi import APIRouter, Request

from app.config import get_settings
from app.db.engine import get_conn
from app.db.repo import last_poll
from app.deps import render
from app.services.net_worth import (
    cash_total_cents,
    credit_card_owed_cents,
    investments_total_cents,
)

router = APIRouter()


def _fmt_sgd(cents: int) -> str:
    sign = "-" if cents < 0 else ""
    cents = abs(int(cents))
    return f"{sign}S${cents // 100:,}.{cents % 100:02d}"


@router.get("/")
def dashboard(request: Request):
    conn = get_conn()
    accounts = conn.execute(
        """
        SELECT a.*, s.closing_balance_cents, s.period_end, s.reconcile_status
        FROM accounts a
        LEFT JOIN statements s ON s.id = (
          SELECT id FROM statements WHERE account_id = a.id
          ORDER BY period_end DESC LIMIT 1
        )
        ORDER BY a.type, a.name
        """
    ).fetchall()
    mismatches = conn.execute(
        """
        SELECT s.id, a.name, s.period_end, s.reconcile_delta_cents
        FROM statements s JOIN accounts a ON a.id = s.account_id
        WHERE s.reconcile_status = 'mismatch'
        ORDER BY s.period_end DESC LIMIT 10
        """
    ).fetchall()
    cash = cash_total_cents()
    cc = credit_card_owed_cents()
    inv = investments_total_cents()
    net_worth = cash - cc + inv
    poll = last_poll("agentmail")
    return render(
        request,
        "dashboard.html",
        accounts=accounts,
        mismatches=mismatches,
        cash=cash,
        cc=cc,
        inv=inv,
        net_worth=net_worth,
        last_poll=poll,
        agentmail_enabled=get_settings().agentmail_enabled,
        fmt=_fmt_sgd,
    )
