import csv
import sqlite3
from pathlib import Path


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def ingest_recalls(conn: sqlite3.Connection, recalls_path: Path) -> int:
    rows = _read_csv(recalls_path)
    conn.executemany(
        """
        INSERT INTO recalls (
            recall_id, event_date, product_name, brand, reason, classification, states
        ) VALUES (
            :recall_id, :event_date, :product_name, :brand, :reason, :classification, :states
        )
        ON CONFLICT(recall_id) DO UPDATE SET
            event_date=excluded.event_date,
            product_name=excluded.product_name,
            brand=excluded.brand,
            reason=excluded.reason,
            classification=excluded.classification,
            states=excluded.states
        """,
        rows,
    )
    conn.commit()
    return len(rows)


def ingest_pantry(conn: sqlite3.Connection, pantry_path: Path) -> int:
    rows = _read_csv(pantry_path)
    conn.executemany(
        """
        INSERT INTO pantry_items (
            item_id, item_name, brand, quantity, location
        ) VALUES (
            :item_id, :item_name, :brand, :quantity, :location
        )
        ON CONFLICT(item_id) DO UPDATE SET
            item_name=excluded.item_name,
            brand=excluded.brand,
            quantity=excluded.quantity,
            location=excluded.location
        """,
        rows,
    )
    conn.commit()
    return len(rows)
