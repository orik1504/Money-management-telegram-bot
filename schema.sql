-- Run once in Supabase: SQL Editor -> New query -> paste -> Run.

CREATE TABLE IF NOT EXISTS expenses (
    id          BIGSERIAL PRIMARY KEY,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    category    TEXT NOT NULL,
    amount      NUMERIC(12, 2) NOT NULL CHECK (amount > 0)
);

CREATE TABLE IF NOT EXISTS incomes (
    id          BIGSERIAL PRIMARY KEY,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    source      TEXT NOT NULL,
    amount      NUMERIC(12, 2) NOT NULL CHECK (amount > 0)
);

CREATE TABLE IF NOT EXISTS investments (
    id          BIGSERIAL PRIMARY KEY,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    amount      NUMERIC(12, 2) NOT NULL CHECK (amount > 0)
);

-- One row per month the budget was set/changed. A month without a row
-- uses the most recent earlier row.
CREATE TABLE IF NOT EXISTS budgets (
    month       DATE PRIMARY KEY,
    amount      NUMERIC(12, 2) NOT NULL CHECK (amount >= 0)
);

CREATE INDEX IF NOT EXISTS expenses_created_at_idx ON expenses (created_at);
CREATE INDEX IF NOT EXISTS incomes_created_at_idx ON incomes (created_at);

-- Block Supabase's public REST API from these tables. The bot connects as the
-- table owner via Postgres directly, so it is not affected.
ALTER TABLE expenses    ENABLE ROW LEVEL SECURITY;
ALTER TABLE incomes     ENABLE ROW LEVEL SECURITY;
ALTER TABLE investments ENABLE ROW LEVEL SECURITY;
ALTER TABLE budgets     ENABLE ROW LEVEL SECURITY;
