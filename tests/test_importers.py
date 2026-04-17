from __future__ import annotations

CSV_BYTES = (
    b"Symbol,Qty,Avg Price,Ccy,Date\n"
    b"AAPL,10,150.25,USD,2026-04-01\n"
    b"MSFT,5,400.00,USD,2026-04-01\n"
)


def test_sniff_columns(migrated_db):
    from app.importers.investments import sniff_columns

    cols = sniff_columns(CSV_BYTES)
    assert cols == ["Symbol", "Qty", "Avg Price", "Ccy", "Date"]


def test_import_csv_inserts_holdings(migrated_db):
    from app.importers.investments import import_csv

    column_map = {
        "symbol": "Symbol",
        "quantity": "Qty",
        "avg_cost": "Avg Price",
        "currency": "Ccy",
        "as_of_date": "Date",
    }
    result = import_csv(CSV_BYTES, column_map, "IBKR Main")
    assert result.inserted == 2
    assert result.errors == []
    rows = migrated_db.execute("SELECT symbol, quantity, currency FROM holdings ORDER BY symbol").fetchall()
    assert [r["symbol"] for r in rows] == ["AAPL", "MSFT"]
    assert rows[0]["currency"] == "USD"


def test_import_csv_missing_required_field(migrated_db):
    from app.importers.investments import import_csv

    result = import_csv(CSV_BYTES, {"symbol": "Symbol"}, "IBKR Main")
    assert result.inserted == 0
    assert result.errors
