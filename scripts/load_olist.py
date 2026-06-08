"""Load Olist CSV files into PostgreSQL raw schema via COPY.

Usage:
    uv run python scripts/load_olist.py

Expects CSVs in data/raw/olist-dataset/.
Download from: https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce
"""

from __future__ import annotations

import sys
from pathlib import Path

import psycopg

from analytics_copilot.core.config import get_settings

DATASET_DIR = Path(__file__).parent.parent / "data" / "raw" / "olist-dataset"

# (raw table, csv filename) in dependency order — parents before children.
TABLES: list[tuple[str, str]] = [
    ("customers", "olist_customers_dataset.csv"),
    ("orders", "olist_orders_dataset.csv"),
    ("order_items", "olist_order_items_dataset.csv"),
    ("products", "olist_products_dataset.csv"),
    ("sellers", "olist_sellers_dataset.csv"),
    ("reviews", "olist_order_reviews_dataset.csv"),
    ("payments", "olist_order_payments_dataset.csv"),
    ("geolocation", "olist_geolocation_dataset.csv"),
    ("category_translation", "product_category_name_translation.csv"),
]


def dsn() -> str:
    s = get_settings()
    return (
        f"host={s.postgres_host} "
        f"port={s.postgres_port} "
        f"dbname={s.postgres_db} "
        f"user={s.postgres_user} "
        f"password={s.postgres_password.get_secret_value()}"
    )


def load_table(cur: psycopg.Cursor, table: str, path: Path) -> int:
    # utf-8-sig strips the BOM that Excel-exported CSVs prepend.
    with path.open(encoding="utf-8-sig") as f:
        columns = f.readline().strip()  # first line = header
        data = f.read()  # rest = rows

    cur.execute(f"TRUNCATE raw.{table} RESTART IDENTITY CASCADE")

    with cur.copy(
        f"COPY raw.{table} ({columns}) FROM STDIN WITH (FORMAT CSV, NULL '')"
    ) as copy:
        copy.write(data)

    cur.execute(f"SELECT COUNT(*) FROM raw.{table}")
    row = cur.fetchone()
    return int(row[0]) if row else 0


def main() -> None:
    missing = [f for _, f in TABLES if not (DATASET_DIR / f).exists()]
    if missing:
        print(f"Missing files in {DATASET_DIR}:", file=sys.stderr)
        for f in missing:
            print(f"  {f}", file=sys.stderr)
        sys.exit(1)

    s = get_settings()
    print(
        f"Connecting to PostgreSQL @ {s.postgres_host}:{s.postgres_port}/{s.postgres_db}..."
    )

    with psycopg.connect(dsn(), autocommit=False) as conn:
        with conn.cursor() as cur:
            for table, filename in TABLES:
                print(f"  {filename} → raw.{table}", end="", flush=True)
                count = load_table(cur, table, DATASET_DIR / filename)
                print(f"  ({count:,} rows)")
        conn.commit()

    print("Done.")


if __name__ == "__main__":
    main()
