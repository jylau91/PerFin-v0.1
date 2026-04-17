-- PerFin initial schema.

CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY,
    applied_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS accounts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    type TEXT NOT NULL CHECK (type IN ('bank', 'credit_card', 'investment')),
    bank_id TEXT,
    currency TEXT NOT NULL DEFAULT 'SGD',
    opened_at TEXT,
    closed_at TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_accounts_type ON accounts(type);

CREATE TABLE IF NOT EXISTS statements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id INTEGER NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
    period_start TEXT NOT NULL,
    period_end TEXT NOT NULL,
    opening_balance_cents INTEGER,
    closing_balance_cents INTEGER,
    source_pdf_path TEXT,
    parser_id TEXT NOT NULL,
    parsed_at TEXT NOT NULL DEFAULT (datetime('now')),
    reconcile_status TEXT CHECK (reconcile_status IN ('ok','mismatch','unknown')) DEFAULT 'unknown',
    reconcile_delta_cents INTEGER,
    UNIQUE(account_id, period_start, period_end)
);

CREATE TABLE IF NOT EXISTS categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    parent_id INTEGER REFERENCES categories(id),
    is_system INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    statement_id INTEGER REFERENCES statements(id) ON DELETE SET NULL,
    account_id INTEGER NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
    txn_date TEXT NOT NULL,
    post_date TEXT,
    description TEXT NOT NULL,
    raw_description TEXT NOT NULL,
    amount_cents INTEGER NOT NULL,
    currency TEXT NOT NULL DEFAULT 'SGD',
    category_id INTEGER REFERENCES categories(id),
    is_transfer INTEGER NOT NULL DEFAULT 0,
    hash TEXT NOT NULL UNIQUE
);
CREATE INDEX IF NOT EXISTS idx_transactions_account_date ON transactions(account_id, txn_date);
CREATE INDEX IF NOT EXISTS idx_transactions_category ON transactions(category_id);

CREATE TABLE IF NOT EXISTS ingest_sources (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT NOT NULL CHECK (source IN ('upload','agentmail')),
    external_id TEXT,
    received_at TEXT NOT NULL DEFAULT (datetime('now')),
    raw_subject TEXT,
    raw_sender TEXT,
    attachment_filename TEXT,
    statement_id INTEGER REFERENCES statements(id) ON DELETE SET NULL,
    error TEXT,
    UNIQUE(source, external_id, attachment_filename)
);

CREATE TABLE IF NOT EXISTS holdings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id INTEGER NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
    symbol TEXT NOT NULL,
    quantity REAL NOT NULL,
    avg_cost_cents INTEGER,
    currency TEXT NOT NULL DEFAULT 'SGD',
    as_of_date TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_holdings_account_symbol ON holdings(account_id, symbol);

CREATE TABLE IF NOT EXISTS prices (
    symbol TEXT NOT NULL,
    as_of_date TEXT NOT NULL,
    close_cents INTEGER NOT NULL,
    currency TEXT NOT NULL DEFAULT 'USD',
    PRIMARY KEY(symbol, as_of_date)
);

CREATE TABLE IF NOT EXISTS ai_cache (
    key TEXT PRIMARY KEY,
    model TEXT NOT NULL,
    feature TEXT NOT NULL,
    request_json TEXT NOT NULL,
    response_json TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    tokens_in INTEGER,
    tokens_out INTEGER
);

CREATE TABLE IF NOT EXISTS ai_usage (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    month TEXT NOT NULL,
    tokens_in INTEGER NOT NULL DEFAULT 0,
    tokens_out INTEGER NOT NULL DEFAULT 0,
    UNIQUE(month)
);

CREATE TABLE IF NOT EXISTS net_worth_snapshots (
    as_of_date TEXT PRIMARY KEY,
    cash_cents INTEGER NOT NULL DEFAULT 0,
    investments_cents INTEGER NOT NULL DEFAULT 0,
    total_cents INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS broker_profiles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    broker_name TEXT NOT NULL UNIQUE,
    column_map_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS poll_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT NOT NULL,
    ran_at TEXT NOT NULL DEFAULT (datetime('now')),
    matched INTEGER NOT NULL DEFAULT 0,
    ingested INTEGER NOT NULL DEFAULT 0,
    skipped INTEGER NOT NULL DEFAULT 0,
    errored INTEGER NOT NULL DEFAULT 0,
    note TEXT
);

INSERT OR IGNORE INTO categories (name, is_system) VALUES
  ('Uncategorised', 1),
  ('Groceries', 1),
  ('Dining', 1),
  ('Transport', 1),
  ('Utilities', 1),
  ('Rent/Mortgage', 1),
  ('Entertainment', 1),
  ('Shopping', 1),
  ('Healthcare', 1),
  ('Salary', 1),
  ('Transfer', 1),
  ('Fees', 1),
  ('Insurance', 1);
