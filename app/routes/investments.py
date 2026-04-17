from __future__ import annotations

from fastapi import APIRouter, File, Form, Request, UploadFile

from app.db.engine import get_conn
from app.deps import render
from app.importers.investments import import_csv, save_profile, sniff_columns

router = APIRouter(prefix="/investments", tags=["investments"])


@router.get("")
def list_investments(request: Request):
    conn = get_conn()
    holdings = conn.execute(
        """
        SELECT h.symbol, SUM(h.quantity) AS qty, h.currency, a.name AS account_name,
               (SELECT close_cents FROM prices p WHERE p.symbol = h.symbol
                  ORDER BY p.as_of_date DESC LIMIT 1) AS close_cents
        FROM holdings h JOIN accounts a ON a.id = h.account_id
        GROUP BY h.symbol, h.currency, a.name
        ORDER BY h.symbol
        """
    ).fetchall()
    return render(request, "investments/list.html", holdings=holdings)


@router.get("/import")
def import_form(request: Request):
    return render(request, "investments/import.html", columns=None, result=None)


@router.post("/import/sniff")
async def import_sniff(request: Request, csv_file: UploadFile = File(...), broker_name: str = Form(...)):
    data = await csv_file.read()
    cols = sniff_columns(data)
    # Stash bytes in the session? Here we base64 in hidden input for simplicity.
    import base64

    encoded = base64.b64encode(data).decode()
    return render(
        request,
        "investments/import.html",
        columns=cols,
        encoded=encoded,
        broker_name=broker_name,
        result=None,
    )


@router.post("/import/apply")
async def import_apply(
    request: Request,
    broker_name: str = Form(...),
    encoded: str = Form(...),
    account_name: str = Form(...),
    symbol_col: str = Form(...),
    quantity_col: str = Form(...),
    avg_cost_col: str = Form(default=""),
    currency_col: str = Form(default=""),
    as_of_date_col: str = Form(default=""),
):
    import base64

    data = base64.b64decode(encoded)
    column_map = {"symbol": symbol_col, "quantity": quantity_col}
    if avg_cost_col:
        column_map["avg_cost"] = avg_cost_col
    if currency_col:
        column_map["currency"] = currency_col
    if as_of_date_col:
        column_map["as_of_date"] = as_of_date_col
    save_profile(broker_name, column_map)
    result = import_csv(data, column_map, account_name)
    return render(request, "investments/import.html", columns=None, result=result)
