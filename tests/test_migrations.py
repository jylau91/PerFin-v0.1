from __future__ import annotations


def test_apply_all_creates_expected_tables(migrated_db):
    conn = migrated_db
    rows = conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall()
    names = {r["name"] for r in rows}
    expected = {
        "accounts",
        "statements",
        "transactions",
        "categories",
        "holdings",
        "prices",
        "ai_cache",
        "ai_usage",
        "net_worth_snapshots",
        "ingest_sources",
        "broker_profiles",
        "poll_log",
        "schema_version",
    }
    assert expected.issubset(names), f"missing: {expected - names}"


def test_apply_all_is_idempotent(migrated_db):
    from migrations.runner import apply_all

    applied_again = apply_all(migrated_db)
    assert applied_again == []


def test_indexes_present(migrated_db):
    rows = migrated_db.execute(
        "SELECT name FROM sqlite_master WHERE type='index'"
    ).fetchall()
    names = {r["name"] for r in rows}
    assert "idx_transactions_account_date" in names
    assert "idx_holdings_account_symbol" in names


def test_seeded_categories(migrated_db):
    row = migrated_db.execute("SELECT COUNT(*) AS n FROM categories").fetchone()
    assert row["n"] >= 10
