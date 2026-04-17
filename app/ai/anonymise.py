from __future__ import annotations

import re

ACCOUNT_RE = re.compile(r"\b\d{6,}\b")
CARD_RE = re.compile(r"\b(?:\d[ -]?){12,19}\b")
EMAIL_RE = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")
PHONE_RE = re.compile(r"\+?\d[\d\s-]{7,}\d")

NAME_TOKENS = {"MR", "MRS", "MS", "MDM", "DR"}

SAFE_MERCHANTS = (
    "NTUC", "FAIRPRICE", "SHENG SIONG", "COLD STORAGE",
    "GIANT", "DON DON DONKI", "GRAB", "GOJEK", "TADA",
    "SINGTEL", "STARHUB", "M1", "SP SERVICES", "CIRCLES LIFE",
    "NETFLIX", "SPOTIFY", "AMAZON", "SHOPEE", "LAZADA",
    "MCDONALD", "STARBUCKS", "KFC", "SUBWAY",
)


def anonymise_text(s: str) -> str:
    s = CARD_RE.sub("CARD_XXXX", s)
    s = ACCOUNT_RE.sub("ACCT_XXX", s)
    s = EMAIL_RE.sub("EMAIL_REDACTED", s)
    s = PHONE_RE.sub("PHONE_REDACTED", s)
    return s


def anonymise_merchant(desc: str) -> str:
    upper = desc.upper()
    for safe in SAFE_MERCHANTS:
        if safe in upper:
            return safe
    cleaned = anonymise_text(desc)
    tokens = [t for t in re.split(r"[\s/\-_]+", cleaned) if t]
    if not tokens:
        return "MERCHANT"
    return tokens[0][:20].upper()


def anonymise_txn_row(row: dict) -> dict:
    out = dict(row)
    out.pop("raw_description", None)
    out["description"] = anonymise_merchant(row.get("description", ""))
    return out
