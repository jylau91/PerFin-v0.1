from __future__ import annotations

from app.parsers.trust_bank import TrustBankParser, _parse_date, _to_cents


def test_trust_matches_on_issuer_text():
    p = TrustBankParser()
    assert p.matches("Trust Bank Singapore Limited", {})
    assert not p.matches("DBS Bank Ltd Statement", {})


def test_parse_date_dd_mmm_yyyy():
    d = _parse_date("15 Jan 2026")
    assert d.year == 2026
    assert d.month == 1
    assert d.day == 15


def test_parse_date_dd_mmm_uses_period_year():
    from datetime import date

    d = _parse_date("03 Feb", period_end=date(2026, 2, 28))
    assert d.year == 2026


def test_parse_date_year_crossing_prefers_period_start_year():
    from datetime import date

    # Statement period 15 Dec 2025 → 14 Jan 2026: "31 Dec" belongs to 2025.
    ps, pe = date(2025, 12, 15), date(2026, 1, 14)
    d = _parse_date("31 Dec", period_start=ps, period_end=pe)
    assert d == date(2025, 12, 31)

    # "05 Jan" belongs to 2026.
    d2 = _parse_date("05 Jan", period_start=ps, period_end=pe)
    assert d2 == date(2026, 1, 5)


def test_to_cents_handles_commas():
    assert _to_cents("1,234.56") == 123456


def test_txn_line_regex_captures_cr_flag():
    from app.parsers.trust_bank import TRUST_TEMPLATE

    line = "15 Jan 16 Jan NTUC FAIRPRICE CLEMENTI S$ 23.45"
    m = TRUST_TEMPLATE["txn_line"].match(line)
    assert m is not None
    assert m.group("desc").startswith("NTUC")
    assert not m.group("cr")

    cr_line = "20 Jan 21 Jan PAYMENT RECEIVED THANK YOU S$ 1,200.00 CR"
    m2 = TRUST_TEMPLATE["txn_line"].match(cr_line)
    assert m2 is not None
    assert m2.group("cr").strip() == "CR"


def test_registry_raises_when_no_match():
    from app.parsers.base import ParseError
    from app.parsers.registry import detect_bank

    # Minimal non-PDF bytes should make pdfplumber raise → ParseError.
    try:
        detect_bank(b"not a pdf")
    except ParseError:
        return
    raise AssertionError("expected ParseError")
