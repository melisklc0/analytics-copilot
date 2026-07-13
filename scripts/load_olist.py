"""Load Olist CSV files into PostgreSQL raw schema via COPY.

Usage:
    uv run python scripts/load_olist.py

Loads from the committed sample by default so a fresh `docker compose up` seeds a
populated warehouse with no Kaggle download. Point OLIST_DATA_DIR at the full
dataset to load everything:

    OLIST_DATA_DIR=data/raw/olist-dataset uv run python scripts/load_olist.py

Full dataset: https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce
"""

from __future__ import annotations

import sys
from pathlib import Path

import psycopg

from analytics_copilot.core.config import get_settings

# The data directory comes from Settings.olist_data_dir (env: OLIST_DATA_DIR),
# defaulting to the committed FK-consistent sample. The sample omits geolocation
# (no staging model consumes it) — missing CSVs are skipped, so both the sample
# and the full dataset load cleanly.

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
    s = get_settings()
    dataset_dir = s.olist_data_dir
    if not dataset_dir.exists():
        print(f"Data directory not found: {dataset_dir}", file=sys.stderr)
        sys.exit(1)

    # Tables whose CSV is present. Absent files are skipped (the sample omits
    # geolocation), but an entirely empty directory is a misconfiguration.
    present = [(t, f) for t, f in TABLES if (dataset_dir / f).exists()]
    skipped = [f for t, f in TABLES if not (dataset_dir / f).exists()]
    if not present:
        print(f"No Olist CSVs found in {dataset_dir}", file=sys.stderr)
        sys.exit(1)

    print(
        f"Loading from {dataset_dir} into "
        f"{s.postgres_host}:{s.postgres_port}/{s.postgres_db}..."
    )
    for f in skipped:
        print(f"  (skip) {f} not present")

    with psycopg.connect(dsn(), autocommit=False) as conn:
        with conn.cursor() as cur:
            # Idempotent: skip if already seeded so repeated `docker compose up`
            # never clobbers the warehouse. Set SEED_FORCE=1 to reload anyway
            # (e.g. after switching OLIST_DATA_DIR to the full dataset); each
            # table is truncated before load, so a forced run cleanly replaces.
            cur.execute("SELECT COUNT(*) FROM raw.orders")
            row = cur.fetchone()
            existing = int(row[0]) if row else 0
            if existing > 0 and not s.seed_force:
                print(
                    f"Already seeded ({existing:,} orders) — skipping. "
                    "Set SEED_FORCE=1 to reload."
                )
                return
            if existing > 0:
                print(f"SEED_FORCE set — reloading over {existing:,} existing orders.")

            for table, filename in present:
                print(f"  {filename} -> raw.{table}", end="", flush=True)
                count = load_table(cur, table, dataset_dir / filename)
                print(f"  ({count:,} rows)")
        conn.commit()

    print("Done.")


if __name__ == "__main__":
    main()
