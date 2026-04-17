from __future__ import annotations

from fastapi import APIRouter, Request

from app.ai.client import BudgetExceeded
from app.deps import render

router = APIRouter(prefix="/ai", tags=["ai"])


@router.get("")
def ai_home(request: Request):
    return render(request, "ai/home.html")


@router.post("/spend-analysis")
def spend_analysis(request: Request):
    from app.ai import spend_analysis as sa

    try:
        result = sa.analyse()
    except BudgetExceeded as exc:
        return render(request, "ai/_error.html", message=str(exc))
    return render(request, "ai/_spend_analysis.html", result=result)


@router.post("/anomalies")
def anomalies(request: Request):
    from app.ai import anomalies as an

    try:
        result = an.flag()
    except BudgetExceeded as exc:
        return render(request, "ai/_error.html", message=str(exc))
    return render(request, "ai/_anomalies.html", result=result)


@router.post("/save-plan")
def save_plan(request: Request):
    from app.ai import save_plan as sp

    try:
        result = sp.generate()
    except BudgetExceeded as exc:
        return render(request, "ai/_error.html", message=str(exc))
    return render(request, "ai/_save_plan.html", result=result)
