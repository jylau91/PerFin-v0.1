from __future__ import annotations

import io
import re
from datetime import date, datetime

import pdfplumber

from app.parsers.base import ParseError, ParseResult, StatementParser, TxnRow

# Iterate on these regexes once a real Trust Bank statement is in hand.
# Trust statements are typically credit-card PDFs; line format is a best-effort
# template based on the common SG credit-card layout. Adjust as needed.
TRUST_TEMPLATE: dict[str, re.Pattern[str]] = {
    "issuer": re.compile(r"Trust\s+Bank\s+Singapore", re.IGNORECASE),
    "period": re.compile(
        r"Statement\s+Period[:\s]+(\d{1,2}\s+\w{3,9}\s+\d{4})\s+(?:to|-)\s+(\d{1,2}\s+\w{3,9}\s+\d{4})",
        re.IGNORECASE,
    ),
    "closing": re.compile(
        r"(?:New\s+Balance|Closing\s+Balance|Total\s+Amount\s+Due)\s*[:\-]?\s*S?\$?\s*([\d,]+\.\d{2})",
        re.IGNORECASE,
    ),
    "opening": re.compile(
        r"(?:Previous\s+Balance|Opening\s+Balance)\s*[:\-]?\s*S?\$?\s*([\d,]+\.\d{2})",
        re.IGNORECASE,
    ),
    "account_number": re.compile(
        r"(?:Card|Account)\s+Number[:\s]+(\*{0,12}\d{4,})",
        re.IGNORECASE,
    ),
    "txn_line": re.compile(
        r"^(?P<txn>\d{1,2}\s+\w{3})\s+(?P<post>\d{1,2}\s+\w{3})\s+"
        r"(?P<desc>.+?)\s+S?\$?\s*(?P<amount>[\d,]+\.\d{2})(?P<cr>\s*CR)?\s*$"
    ),
}


def _parse_date(s: str, period_end: date | None = None) -> date:
    s = s.strip()
    for fmt in ("%d %b %Y", "%d %B %Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    for fmt in ("%d %b", "%d %B"):
        try:
            parsed = datetime.strptime(s, fmt).date()
            year = (period_end or date.today()).year
            return parsed.replace(year=year)
        except ValueError:
            continue
    raise ParseError(f"Trust parser: unparseable date '{s}'")


def _to_cents(raw: str) -> int:
    return int(round(float(raw.replace(",", "")) * 100))


class TrustBankParser(StatementParser):
    bank_id = "trust"
    parser_id = "trust:v1"

    def matches(self, first_page_text: str, meta: dict) -> bool:
        return bool(TRUST_TEMPLATE["issuer"].search(first_page_text or ""))

    def parse(self, pdf_bytes: bytes, password: str | None = None) -> ParseResult:
        try:
            with pdfplumber.open(io.BytesIO(pdf_bytes), password=password) as pdf:
                pages_text = [p.extract_text() or "" for p in pdf.pages]
        except Exception as exc:
            raise ParseError(f"Trust parser: PDF read failed: {exc}") from exc

        full_text = "\n".join(pages_text)
        if not TRUST_TEMPLATE["issuer"].search(full_text):
            raise ParseError("Trust parser: issuer marker not found")

        period_m = TRUST_TEMPLATE["period"].search(full_text)
        if not period_m:
            raise ParseError("Trust parser: could not locate statement period")
        period_start = _parse_date(period_m.group(1))
        period_end = _parse_date(period_m.group(2))

        closing_m = TRUST_TEMPLATE["closing"].search(full_text)
        closing_cents = _to_cents(closing_m.group(1)) if closing_m else None
        opening_m = TRUST_TEMPLATE["opening"].search(full_text)
        opening_cents = _to_cents(opening_m.group(1)) if opening_m else None

        acct_m = TRUST_TEMPLATE["account_number"].search(full_text)
        account_number = acct_m.group(1) if acct_m else ""

        transactions: list[TxnRow] = []
        for line in full_text.splitlines():
            line = line.strip()
            m = TRUST_TEMPLATE["txn_line"].match(line)
            if not m:
                continue
            txn_d = _parse_date(m.group("txn"), period_end)
            post_d = _parse_date(m.group("post"), period_end)
            amount_cents = _to_cents(m.group("amount"))
            # CR flag = payment/refund: credit to card (reduces balance) → negative amount.
            # Normal charges are positive amounts (spending).
            if not m.group("cr"):
                amount_cents = amount_cents  # purchase
            else:
                amount_cents = -amount_cents
            desc = m.group("desc").strip()
            transactions.append(
                TxnRow(
                    txn_date=txn_d,
                    post_date=post_d,
                    description=desc,
                    raw_description=desc,
                    amount_cents=amount_cents,
                )
            )

        return ParseResult(
            bank_id="trust",
            account_type="credit_card",
            account_number=account_number,
            period_start=period_start,
            period_end=period_end,
            opening_balance_cents=opening_cents,
            closing_balance_cents=closing_cents,
            currency="SGD",
            transactions=transactions,
            raw_text=full_text,
        )
