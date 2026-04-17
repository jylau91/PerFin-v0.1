from __future__ import annotations

import logging
from datetime import date

from app.db.engine import get_conn

log = logging.getLogger("perfin.prices")


def _to_cents(value: float) -> int:
    return int(round(float(value) * 100))


def refresh_prices() -> int:
    """Fetch latest close for each held symbol via yfinance. Returns rows written."""
    conn = get_conn()
    symbols = [r["symbol"] for r in conn.execute("SELECT DISTINCT symbol FROM holdings").fetchall()]
    if not symbols:
        return 0
    try:
        import yfinance as yf
    except Exception as exc:
        log.warning("yfinance not available: %s", exc)
        return 0
    today = date.today().isoformat()
    written = 0
    for sym in symbols:
        try:
            t = yf.Ticker(sym)
            hist = t.history(period="5d")
            if hist.empty:
                continue
            close = float(hist["Close"].iloc[-1])
            currency = getattr(t.info, "currency", None) if hasattr(t, "info") else "USD"
            conn.execute(
                "INSERT OR REPLACE INTO prices (symbol, as_of_date, close_cents, currency) VALUES (?, ?, ?, ?)",
                (sym, today, _to_cents(close), currency or "USD"),
            )
            written += 1
        except Exception as exc:
            log.warning("price fetch failed for %s: %s", sym, exc)
    return written
