from __future__ import annotations

import tempfile
from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def _temp_db(monkeypatch):
    td = tempfile.TemporaryDirectory()
    db_path = Path(td.name) / "test.db"
    monkeypatch.setenv("PERFIN_DB_PATH", str(db_path))
    monkeypatch.setenv("PERFIN_PASSPHRASE", "test")
    monkeypatch.setenv("PERFIN_SESSION_SECRET", "test-secret")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "")
    monkeypatch.setenv("AGENTMAIL_API_KEY", "")
    monkeypatch.setenv("AGENTMAIL_INBOX_ID", "")

    # Invalidate cached settings + db connection between tests.
    from app.config import get_settings
    get_settings.cache_clear()

    from app.db import engine as db_engine
    db_engine._conn = None

    yield db_path
    db_engine._conn = None
    td.cleanup()


@pytest.fixture
def migrated_db(_temp_db):
    from app.db.engine import get_conn
    from migrations.runner import apply_all

    conn = get_conn()
    apply_all(conn)
    return conn
