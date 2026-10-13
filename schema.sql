CREATE TABLE IF NOT EXISTS platforms (
    name      TEXT PRIMARY KEY,
    fee_pct   REAL NOT NULL DEFAULT 0 CHECK (fee_pct >= 0),
    fee_fixed REAL NOT NULL DEFAULT 0 CHECK (fee_fixed >= 0)
);

-- starting values only, edit them in the app
INSERT OR IGNORE INTO platforms (name, fee_pct, fee_fixed) VALUES
    ('Vinted', 0, 0),
    ('Depop', 10, 0),
    ('eBay', 12.8, 0.30);

CREATE TABLE IF NOT EXISTS listings (
    id         INTEGER PRIMARY KEY,
    title      TEXT NOT NULL,
    brand      TEXT,
    size       TEXT,
    platform   TEXT NOT NULL REFERENCES platforms(name),
    cost_price REAL NOT NULL CHECK (cost_price >= 0),
    list_price REAL NOT NULL CHECK (list_price > 0),
    sale_price REAL,
    status     TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'sold')),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS shipments (
    id              INTEGER PRIMARY KEY,
    listing_id      INTEGER NOT NULL UNIQUE REFERENCES listings(id),
    carrier         TEXT,
    tracking_number TEXT,
    shipping_cost   REAL NOT NULL DEFAULT 0 CHECK (shipping_cost >= 0),
    status          TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'label_created', 'shipped', 'delivered', 'returned')),
    updated_at      TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_event      TEXT
);

-- API keys and tokens; vault.py encrypts the secret ones on Windows
CREATE TABLE IF NOT EXISTS settings (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
