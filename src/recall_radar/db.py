import sqlite3
from pathlib import Path


def get_connection(db_path: str | Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS recalls (
            recall_id TEXT PRIMARY KEY,
            event_date TEXT NOT NULL,
            product_name TEXT NOT NULL,
            brand TEXT,
            reason TEXT,
            classification TEXT,
            states TEXT
        );

        CREATE TABLE IF NOT EXISTS pantry_items (
            item_id TEXT PRIMARY KEY,
            item_name TEXT NOT NULL,
            brand TEXT,
            quantity INTEGER,
            location TEXT
        );

        CREATE INDEX IF NOT EXISTS idx_recalls_brand ON recalls(brand);
        CREATE INDEX IF NOT EXISTS idx_recalls_event_date ON recalls(event_date);
        CREATE INDEX IF NOT EXISTS idx_pantry_brand ON pantry_items(brand);
        CREATE INDEX IF NOT EXISTS idx_pantry_location ON pantry_items(location);
        """
    )
    conn.commit()
