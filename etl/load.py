"""
שלב 2: קריאת קובצי ה-XML שהורדו (dumps/) וטעינתם ל-PostgreSQL.

  * קובצי Stores    -> טבלת stores
  * קובצי PriceFull -> טבלת prices (מחיר רגיל בלבד)
  * בסוף: בנייה מחדש של טבלת products (קטלוג לחיפוש מהיר)

כל קובץ PriceFull הוא תמונת מצב מלאה של סניף אחד, ולכן טעינה שלו
מחליפה את כל המחירים של אותו סניף. אם כבר נטען קובץ חדש יותר לאותו
סניף — הקובץ הישן מדולג. כך אפשר להריץ שוב ושוב בלי כפילויות.

הרצה (אחרי etl/download.py):
    python etl/load.py
"""

import csv
import io
import os
import sys
import time
from collections import Counter
from datetime import datetime

import psycopg2
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from chains import display_name  # noqa: E402
from xml_reader import file_kind, file_timestamp, read_prices, read_stores  # noqa: E402

load_dotenv()

DUMPS_FOLDER = os.environ.get("DUMPS_FOLDER", "dumps")
SCHEMA_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "db", "schema.sql")

PRICE_COLUMNS = [
    "chain_id",
    "store_id",
    "item_code",
    "supermarket_name",
    "item_name",
    "manufacturer_name",
    "quantity",
    "unit_qty",
    "unit_of_measure",
    "is_weighted",
    "item_price",
    "unit_of_measure_price",
    "price_update_date",
]

STORE_COLUMNS = [
    "chain_id",
    "store_id",
    "supermarket_name",
    "sub_chain_id",
    "sub_chain_name",
    "store_name",
    "address",
    "city",
    "source_file",
]


def connect():
    return psycopg2.connect(
        host=os.environ.get("DB_HOST", "localhost"),
        port=os.environ.get("DB_PORT", "5432"),
        dbname=os.environ.get("DB_NAME", "supermarket_prices"),
        user=os.environ.get("DB_USER", "postgres"),
        password=os.environ.get("DB_PASSWORD", "postgres"),
    )


def find_dump_files(dumps_folder):
    """מחזיר [(kind, chain_folder, path, timestamp)] לכל קובץ רלוונטי ב-dumps/<רשת>/..."""
    found = []
    for root, _dirs, files in os.walk(dumps_folder):
        rel = os.path.relpath(root, dumps_folder)
        chain_folder = rel.split(os.sep)[0]
        if chain_folder in (".", "status"):
            continue
        for name in files:
            kind = file_kind(name)
            if kind is None:
                continue
            path = os.path.join(root, name)
            ts = file_timestamp(name) or datetime.fromtimestamp(os.path.getmtime(path))
            found.append((kind, chain_folder, path, ts))
    found.sort(key=lambda f: f[3])  # מהישן לחדש — החדש ביותר דורס
    return found


def _copy(cur, table, columns, rows):
    buf = io.StringIO()
    writer = csv.writer(buf)
    for row in rows:
        writer.writerow(["" if row.get(c) is None else row[c] for c in columns])
    buf.seek(0)
    cur.copy_expert(
        f"COPY {table} ({', '.join(columns)}) FROM STDIN WITH (FORMAT csv, NULL '')",
        buf,
    )


def _most_common(rows, key):
    counts = Counter(r[key] for r in rows if r.get(key))
    return counts.most_common(1)[0][0] if counts else None


def load_stores(conn, path, chain_folder):
    rows = read_stores(path)
    supermarket = display_name(chain_folder)
    dedup = {}
    for r in rows:
        r["chain_id"] = r["chain_id"] or chain_folder
        r["supermarket_name"] = supermarket
        r["source_file"] = os.path.basename(path)
        dedup[(r["chain_id"], r["store_id"])] = r
    if not dedup:
        return 0
    with conn, conn.cursor() as cur:
        cur.execute("CREATE TEMP TABLE tmp_stores (LIKE stores INCLUDING DEFAULTS) ON COMMIT DROP")
        _copy(cur, "tmp_stores", STORE_COLUMNS, dedup.values())
        cur.execute(
            f"""
            INSERT INTO stores ({', '.join(STORE_COLUMNS)})
            SELECT {', '.join(STORE_COLUMNS)} FROM tmp_stores
            ON CONFLICT (chain_id, store_id) DO UPDATE SET
                {', '.join(f'{c} = EXCLUDED.{c}' for c in STORE_COLUMNS[2:])},
                loaded_at = now()
            """
        )
    return len(dedup)


def load_prices(conn, path, chain_folder, ts):
    """טוען קובץ PriceFull אחד. מחזיר מספר שורות, או None אם דולג."""
    rows = read_prices(path)
    if not rows:
        return 0

    supermarket = display_name(chain_folder)
    chain_id = _most_common(rows, "chain_id") or chain_folder
    store_id = _most_common(rows, "store_id")
    if not store_id:
        print(f"  ⚠ לא נמצא מספר סניף בקובץ, מדלג: {path}")
        return 0

    dedup = {}
    for r in rows:
        r["chain_id"] = chain_id
        r["store_id"] = store_id
        r["supermarket_name"] = supermarket
        dedup[r["item_code"]] = r

    with conn, conn.cursor() as cur:
        cur.execute(
            "SELECT file_timestamp FROM store_snapshots WHERE chain_id = %s AND store_id = %s",
            (chain_id, store_id),
        )
        existing = cur.fetchone()
        if existing and existing[0] and existing[0] > ts:
            return None  # כבר יש תמונת מצב חדשה יותר לסניף הזה

        cur.execute(
            "DELETE FROM prices WHERE chain_id = %s AND store_id = %s", (chain_id, store_id)
        )
        _copy(cur, "prices", PRICE_COLUMNS, dedup.values())
        cur.execute(
            """
            INSERT INTO store_snapshots
                (chain_id, store_id, supermarket_name, source_file, file_timestamp, rows_loaded)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (chain_id, store_id) DO UPDATE SET
                supermarket_name = EXCLUDED.supermarket_name,
                source_file = EXCLUDED.source_file,
                file_timestamp = EXCLUDED.file_timestamp,
                rows_loaded = EXCLUDED.rows_loaded,
                loaded_at = now()
            """,
            (chain_id, store_id, supermarket, os.path.basename(path), ts, len(dedup)),
        )
    return len(dedup)


def rebuild_products(conn):
    """בונה מחדש את קטלוג המוצרים: שם נפוץ, מספר רשתות/סניפים, טווח מחירים."""
    with conn, conn.cursor() as cur:
        cur.execute("TRUNCATE products")
        cur.execute(
            """
            INSERT INTO products
                (item_code, item_name, manufacturer_name, quantity, unit_qty, is_weighted,
                 chain_count, store_count, min_price, max_price)
            SELECT
                item_code,
                mode() WITHIN GROUP (ORDER BY item_name),
                mode() WITHIN GROUP (ORDER BY manufacturer_name),
                mode() WITHIN GROUP (ORDER BY quantity),
                mode() WITHIN GROUP (ORDER BY unit_qty),
                bool_or(is_weighted),
                COUNT(DISTINCT supermarket_name),
                COUNT(*),
                MIN(item_price),
                MAX(item_price)
            FROM prices
            GROUP BY item_code
            """
        )
        cur.execute("SELECT (SELECT COUNT(*) FROM products), (SELECT COUNT(*) FROM prices)")
        counts = cur.fetchone()
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute("ANALYZE stores; ANALYZE prices; ANALYZE products;")
    conn.autocommit = False
    return counts


def main():
    if not os.path.isdir(DUMPS_FOLDER):
        print(f"התיקייה {DUMPS_FOLDER} לא קיימת. הריצו קודם: python etl/download.py")
        sys.exit(1)

    conn = connect()
    with conn, conn.cursor() as cur, open(SCHEMA_PATH, encoding="utf-8") as f:
        cur.execute(f.read())

    files = find_dump_files(DUMPS_FOLDER)
    store_files = [f for f in files if f[0] == "stores"]
    price_files = [f for f in files if f[0] == "prices"]
    print(f"נמצאו {len(store_files)} קובצי סניפים ו-{len(price_files)} קובצי מחירים מלאים")

    started = time.time()
    totals = Counter()
    for _kind, chain_folder, path, _ts in store_files:
        try:
            totals["stores"] += load_stores(conn, path, chain_folder)
        except Exception as exc:  # pylint: disable=broad-except
            conn.rollback()
            print(f"  ⚠ שגיאה בקובץ סניפים {path}: {exc}")

    for i, (_kind, chain_folder, path, ts) in enumerate(price_files, 1):
        try:
            n = load_prices(conn, path, chain_folder, ts)
        except Exception as exc:  # pylint: disable=broad-except
            conn.rollback()
            print(f"  ⚠ שגיאה בקובץ מחירים {path}: {exc}")
            continue
        if n is None:
            totals["skipped"] += 1
        else:
            totals["prices"] += n
        if i % 50 == 0 or i == len(price_files):
            print(f"  {i}/{len(price_files)} קובצי מחירים ({totals['prices']:,} מחירים)")

    print("בונה קטלוג מוצרים לחיפוש...")
    product_count, price_count = rebuild_products(conn)
    conn.close()

    print("\n=== סיכום טעינה ===")
    print(f"  סניפים:  {totals['stores']:,}")
    print(f"  מחירים:  {price_count:,}")
    print(f"  מוצרים:  {product_count:,}")
    if totals["skipped"]:
        print(f"  קבצים ישנים שדולגו (יש כבר נתונים חדשים יותר): {totals['skipped']}")
    print(f"  זמן: {time.time() - started:.0f} שניות")
    print("\nאפשר להריץ את האתר: ./run_server.sh")


if __name__ == "__main__":
    main()
