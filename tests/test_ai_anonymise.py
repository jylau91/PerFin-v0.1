from __future__ import annotations

import re

from app.ai.anonymise import anonymise_merchant, anonymise_text, anonymise_txn_row


def test_redacts_account_numbers():
    out = anonymise_text("Transfer from 1234567890 to 9876543210")
    assert "1234567890" not in out
    assert "ACCT_XXX" in out


def test_redacts_card_numbers():
    out = anonymise_text("CARD 4111 1111 1111 1111 AUTH 1234")
    assert "4111" not in out
    assert "CARD_XXXX" in out


def test_redacts_emails_and_phones():
    out = anonymise_text("Contact: j.y@example.com +65 9123 4567")
    assert "example.com" not in out
    assert "9123" not in out


def test_merchant_safe_list_preserved():
    assert anonymise_merchant("NTUC FAIRPRICE 123 CLEMENTI") == "NTUC"
    assert anonymise_merchant("GRAB*TRIP-SG-38271") == "GRAB"


def test_merchant_fallback_short():
    result = anonymise_merchant("Some Random Merchant 1234567890")
    assert "1234567890" not in result
    assert len(result) <= 20


def test_anonymise_txn_row_removes_raw():
    row = {"description": "NTUC FAIRPRICE 123", "raw_description": "NTUC FAIRPRICE 123", "amount_cents": 500}
    out = anonymise_txn_row(row)
    assert "raw_description" not in out
    assert out["description"] == "NTUC"


def test_no_long_digit_runs_survive_end_to_end():
    samples = [
        "Payment to ACCT 11112222333344",
        "Card **** **** **** 4242 charge",
        "Ref: 4007-1234-5678 from 6591234567",
    ]
    joined = " ".join(anonymise_text(s) for s in samples)
    assert not re.search(r"\b\d{6,}\b", joined)
