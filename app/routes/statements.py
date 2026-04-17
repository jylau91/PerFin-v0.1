from __future__ import annotations

from fastapi import APIRouter, File, Form, Request, UploadFile
from fastapi.responses import RedirectResponse

from app.db.engine import get_conn
from app.deps import render
from app.importers.agentmail import poll_and_ingest
from app.services.ingest import ingest_pdf

router = APIRouter(prefix="/statements", tags=["statements"])


@router.get("")
def list_statements(request: Request):
    conn = get_conn()
    rows = conn.execute(
        """
        SELECT s.*, a.name AS account_name, a.type AS account_type
        FROM statements s JOIN accounts a ON a.id = s.account_id
        ORDER BY s.period_end DESC
        LIMIT 100
        """
    ).fetchall()
    return render(request, "statements/list.html", statements=rows)


@router.get("/upload")
def upload_form(request: Request):
    return render(request, "statements/upload.html", result=None)


@router.post("/upload")
async def upload_submit(
    request: Request,
    pdf: UploadFile = File(...),
    password: str = Form(default=""),
):
    data = await pdf.read()
    outcome = ingest_pdf(
        pdf_bytes=data,
        filename=pdf.filename or "upload.pdf",
        password=password or None,
        source="upload",
        external_id=None,
        raw_subject=None,
        raw_sender=None,
    )
    return render(request, "statements/upload.html", result=outcome)


@router.post("/pull-agentmail")
def pull_agentmail(request: Request):
    report = poll_and_ingest()
    html = render(request, "statements/_pull_result.html", report=report)
    return html


@router.get("/{statement_id}")
def statement_detail(request: Request, statement_id: int):
    conn = get_conn()
    stmt = conn.execute(
        "SELECT s.*, a.name AS account_name FROM statements s JOIN accounts a ON a.id=s.account_id WHERE s.id=?",
        (statement_id,),
    ).fetchone()
    if not stmt:
        return RedirectResponse("/statements", status_code=303)
    txns = conn.execute(
        "SELECT * FROM transactions WHERE statement_id=? ORDER BY txn_date",
        (statement_id,),
    ).fetchall()
    return render(request, "statements/detail.html", statement=stmt, txns=txns)
