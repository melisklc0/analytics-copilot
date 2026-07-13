"""Generate a small, FK-consistent Olist sample from the full dataset.

Usage:
    uv run python scripts/make_sample.py [--orders N]

Reads the full CSVs from data/raw/olist-dataset/ and writes a referentially
consistent subset to data/seed/olist-sample/. The subset is committed to git so
a fresh `docker compose up` can seed a populated warehouse without downloading
the ~128 MB Kaggle dataset.

Selection strategy:
    1. Take the N most recent orders (by purchase timestamp) — a contiguous
       recent slice keeps the monthly-revenue time series dense rather than
       sparse.
    2. Filter every child/parent table to match: customers referenced by those
       orders, then order_items (→ products, sellers), payments, and reviews.
    3. geolocation is skipped entirely (no staging model consumes it).
    4. category_translation is copied whole (2.6 KB).
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

# Some Olist review comments are large; raise the field size ceiling.
csv.field_size_limit(10_000_000)

RAW_DIR = Path(__file__).parent.parent / "data" / "raw" / "olist-dataset"
OUT_DIR = Path(__file__).parent.parent / "data" / "seed" / "olist-sample"

DEFAULT_ORDERS = 15_000

FILES = {
    "customers": "olist_customers_dataset.csv",
    "orders": "olist_orders_dataset.csv",
    "order_items": "olist_order_items_dataset.csv",
    "products": "olist_products_dataset.csv",
    "sellers": "olist_sellers_dataset.csv",
    "reviews": "olist_order_reviews_dataset.csv",
    "payments": "olist_order_payments_dataset.csv",
    "category_translation": "product_category_name_translation.csv",
}


def read_rows(name: str) -> tuple[list[str], list[dict[str, str]]]:
    path = RAW_DIR / FILES[name]
    with path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames or []
        return fieldnames, list(reader)


def write_rows(name: str, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    path = OUT_DIR / FILES[name]
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f"  {FILES[name]:<45} {len(rows):>7,} rows")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--orders", type=int, default=DEFAULT_ORDERS)
    args = parser.parse_args()

    missing = [f for f in FILES.values() if not (RAW_DIR / f).exists()]
    if missing:
        print(f"Missing full CSVs in {RAW_DIR}:", file=sys.stderr)
        for f in missing:
            print(f"  {f}", file=sys.stderr)
        sys.exit(1)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Generating sample of {args.orders:,} orders -> {OUT_DIR}")

    # 1. Pick the N most recent orders.
    orders_fields, orders = read_rows("orders")
    orders.sort(key=lambda r: r["order_purchase_timestamp"], reverse=True)
    orders = orders[: args.orders]
    order_ids = {r["order_id"] for r in orders}
    customer_ids = {r["customer_id"] for r in orders}
    write_rows("orders", orders_fields, orders)

    # 2. customers referenced by selected orders.
    cust_fields, customers = read_rows("customers")
    customers = [r for r in customers if r["customer_id"] in customer_ids]
    write_rows("customers", cust_fields, customers)

    # 3. order_items → collect product/seller ids.
    item_fields, items = read_rows("order_items")
    items = [r for r in items if r["order_id"] in order_ids]
    product_ids = {r["product_id"] for r in items}
    seller_ids = {r["seller_id"] for r in items}
    write_rows("order_items", item_fields, items)

    # 4. payments + reviews keyed by order_id.
    pay_fields, payments = read_rows("payments")
    write_rows(
        "payments", pay_fields, [r for r in payments if r["order_id"] in order_ids]
    )

    rev_fields, reviews = read_rows("reviews")
    write_rows(
        "reviews", rev_fields, [r for r in reviews if r["order_id"] in order_ids]
    )

    # 5. products + sellers referenced by items.
    prod_fields, products = read_rows("products")
    write_rows(
        "products", prod_fields, [r for r in products if r["product_id"] in product_ids]
    )

    sell_fields, sellers = read_rows("sellers")
    write_rows(
        "sellers", sell_fields, [r for r in sellers if r["seller_id"] in seller_ids]
    )

    # 6. category_translation — copy whole (tiny).
    cat_fields, categories = read_rows("category_translation")
    write_rows("category_translation", cat_fields, categories)

    print("Done.")


if __name__ == "__main__":
    main()
