import os
import sqlite3
import sys
from contextlib import closing
from pathlib import Path

import vault

ROOT = Path(__file__).parent
# the packaged app unpacks to a temporary folder, so its data lives in AppData instead
FROZEN = getattr(sys, "frozen", False)
DATA_DIR = Path(os.environ["APPDATA"]) / "LogisticsTracker" if FROZEN else ROOT
DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DATA_DIR / "tracker.db"

SECRET_SETTINGS = ("ship24_api_key", "ebay_client_secret", "ebay_refresh_token")
# must match the CHECK in schema.sql
SHIPMENT_STATUSES = ["pending", "label_created", "shipped", "delivered", "returned"]


def connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init():
    with closing(connect()) as conn, conn:
        conn.executescript((ROOT / "schema.sql").read_text())
        # databases created before tracking was added
        columns = {row["name"] for row in conn.execute("PRAGMA table_info(shipments)")}
        if "last_event" not in columns:
            conn.execute("ALTER TABLE shipments ADD COLUMN last_event TEXT")
        # keys saved in plain text by older versions
        for row in conn.execute("SELECT key, value FROM settings").fetchall():
            if row["key"] in SECRET_SETTINGS:
                conn.execute(
                    "UPDATE settings SET value = ? WHERE key = ?", (vault.lock(row["value"]), row["key"])
                )


def query(sql, params=()):
    with closing(connect()) as conn:
        return [dict(row) for row in conn.execute(sql, params)]


def execute(sql, params=()):
    with closing(connect()) as conn, conn:
        conn.execute(sql, params)


def add_listing(title, brand, size, platform, cost_price, list_price):
    execute(
        "INSERT INTO listings (title, brand, size, platform, cost_price, list_price)"
        " VALUES (?, ?, ?, ?, ?, ?)",
        (title, brand, size, platform, cost_price, list_price),
    )


def update_listing(listing_id, title, brand, size, platform, cost_price, list_price):
    execute(
        "UPDATE listings SET title = ?, brand = ?, size = ?, platform = ?,"
        " cost_price = ?, list_price = ? WHERE id = ?",
        (title, brand, size, platform, cost_price, list_price, listing_id),
    )


def delete_listing(listing_id):
    # sold listings stay: their shipment and profit history point at them
    execute("DELETE FROM listings WHERE id = ? AND status = 'active'", (listing_id,))


def active_listings():
    return query(
        "SELECT l.*, p.fee_pct, p.fee_fixed FROM listings l"
        " JOIN platforms p ON p.name = l.platform"
        " WHERE l.status = 'active' ORDER BY l.created_at DESC"
    )


def mark_sold(listing_id, sale_price, shipping_cost):
    # one transaction: a sold listing always has a shipment
    with closing(connect()) as conn, conn:
        conn.execute(
            "UPDATE listings SET status = 'sold', sale_price = ? WHERE id = ?",
            (sale_price, listing_id),
        )
        conn.execute(
            "INSERT INTO shipments (listing_id, shipping_cost) VALUES (?, ?)",
            (listing_id, shipping_cost),
        )


def shipments():
    return query(
        "SELECT s.id, l.title, l.platform, l.sale_price, s.carrier, s.tracking_number,"
        " s.shipping_cost, s.status, s.last_event, s.updated_at FROM shipments s"
        " JOIN listings l ON l.id = s.listing_id ORDER BY s.updated_at DESC"
    )


def update_shipment(shipment_id, status, carrier, tracking_number):
    execute(
        "UPDATE shipments SET status = ?, carrier = ?, tracking_number = ?,"
        " updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        (status, carrier, tracking_number, shipment_id),
    )


def update_tracking(shipment_id, status, last_event):
    execute(
        "UPDATE shipments SET status = ?, last_event = ?,"
        " updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        (status, last_event, shipment_id),
    )


def settings():
    return {row["key"]: vault.unlock(row["value"]) for row in query("SELECT key, value FROM settings")}


def save_settings(values):
    with closing(connect()) as conn, conn:
        conn.executemany(
            "INSERT INTO settings (key, value) VALUES (?, ?)"
            " ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            [(key, vault.lock(value) if key in SECRET_SETTINGS else value) for key, value in values.items()],
        )


def sold_listings():
    return query(
        "SELECT l.sale_price, l.cost_price, p.fee_pct, p.fee_fixed, s.shipping_cost, s.status"
        " FROM listings l JOIN platforms p ON p.name = l.platform"
        " JOIN shipments s ON s.listing_id = l.id WHERE l.status = 'sold'"
    )
