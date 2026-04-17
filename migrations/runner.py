from __future__ import annotations

import re
import sqlite3
import sys
from pathlib import Path

MIGRATIONS_DIR = Path(__file__).parent
MIGRATION_PATTERN = re.compile(r"^(\d{4})_.*\.sql$")


def discovered_migrations() -> list[tuple[int, Path]]:
    out: list[tuple[int, Path]] = []
    for p in sorted(MIGRATIONS_DIR.iterdir()):
        m = MIGRATION_PATTERN.match(p.name)
        if m:
            out.append((int(m.group(1)), p))
    return out


def current_version(conn: sqlite3.Connection) -> int:
    conn.execute(
        "CREATE TABLE IF NOT EXISTS schema_version (version INTEGER PRIMARY KEY, "
        "applied_at TEXT NOT NULL DEFAULT (datetime('now')))"
    )
    row = conn.execute("SELECT COALESCE(MAX(version), 0) FROM schema_version").fetchone()
    return int(row[0])


def apply_all(conn: sqlite3.Connection) -> list[int]:
    applied: list[int] = []
    version = current_version(conn)
    for v, path in discovered_migrations():
        if v <= version:
            continue
        sql = path.read_text()
        conn.executescript(sql)
        conn.execute("INSERT INTO schema_version (version) VALUES (?)", (v,))
        applied.append(v)
    return applied


def main() -> int:
    from app.db.engine import get_conn

    conn = get_conn()
    applied = apply_all(conn)
    if applied:
        print(f"Applied migrations: {applied}")
    else:
        print("Schema up to date.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
