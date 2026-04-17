from __future__ import annotations

import io
import logging

import pdfplumber

from app.parsers.base import ParseError, StatementParser
from app.parsers.monopoly_adapter import MONOPOLY_BANKS, MonopolyAdapter
from app.parsers.trust_bank import TrustBankParser

log = logging.getLogger("perfin.parsers")


def _first_page_text(pdf_bytes: bytes, password: str | None) -> str:
    with pdfplumber.open(io.BytesIO(pdf_bytes), password=password) as pdf:
        if not pdf.pages:
            return ""
        return pdf.pages[0].extract_text() or ""


def all_parsers() -> list[StatementParser]:
    parsers: list[StatementParser] = [TrustBankParser()]
    for bank in MONOPOLY_BANKS:
        parsers.append(MonopolyAdapter(bank))
    return parsers


def detect_bank(pdf_bytes: bytes, password: str | None = None) -> StatementParser:
    try:
        first_text = _first_page_text(pdf_bytes, password)
    except Exception as exc:
        raise ParseError(f"Unable to read PDF first page: {exc}") from exc
    meta: dict = {}
    for parser in all_parsers():
        try:
            if parser.matches(first_text, meta):
                log.info("Detected parser: %s", parser.parser_id)
                return parser
        except Exception:
            continue
    raise ParseError("No parser matched this statement.")
