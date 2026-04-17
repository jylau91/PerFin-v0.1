from __future__ import annotations


def _seed(conn, opening, closing, txn_amounts):
    conn.execute(
        "INSERT INTO accounts (name, type, bank_id, currency) VALUES (?, 'bank', 'dbs', 'SGD')",
        ("DBS 001",),
    )
    aid = conn.execute("SELECT id FROM accounts").fetchone()["id"]
    conn.execute(
        """
        INSERT INTO statements
          (account_id, period_start, period_end, opening_balance_cents,
           closing_balance_cents, parser_id)
        VALUES (?, '2026-01-01', '2026-01-31', ?, ?, 'test')
        """,
        (aid, opening, closing),
    )
    sid = conn.execute("SELECT id FROM statements").fetchone()["id"]
    for i, amt in enumerate(txn_amounts):
        conn.execute(
            """
            INSERT INTO transactions
              (statement_id, account_id, txn_date, description, raw_description,
               amount_cents, currency, hash)
            VALUES (?, ?, '2026-01-15', 'x', 'x', ?, 'SGD', ?)
            """,
            (sid, aid, amt, f"h{i}"),
        )
    return sid


def test_exact_match(migrated_db):
    from app.reconcile import reconcile_statement

    sid = _seed(migrated_db, 10000, 10500, [500])
    status, delta = reconcile_statement(sid)
    assert status == "ok"
    assert delta == 0


def test_off_by_one_cent_tolerance(migrated_db):
    from app.reconcile import reconcile_statement

    sid = _seed(migrated_db, 10000, 10501, [500])
    status, delta = reconcile_statement(sid)
    assert status == "ok"
    assert delta == 1


def test_mismatch(migrated_db):
    from app.reconcile import reconcile_statement

    sid = _seed(migrated_db, 10000, 12345, [500])
    status, delta = reconcile_statement(sid)
    assert status == "mismatch"
    assert delta == 1845


def test_unknown_when_no_balances(migrated_db):
    from app.reconcile import reconcile_statement

    sid = _seed(migrated_db, None, None, [500])
    status, delta = reconcile_statement(sid)
    assert status == "unknown"
    assert delta is None
