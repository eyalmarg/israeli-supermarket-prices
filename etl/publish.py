"""
עדכון המאגר: הורדה + סיכום + כתיבה ל-PostgreSQL (Supabase), רשת אחת בכל פעם.

    python etl/publish.py SHUFERSAL          # מוריד ומעדכן רשת אחת
    python etl/publish.py --all              # כל הרשתות, אחת אחרי השנייה
    python etl/publish.py --finalize         # בונה מחדש את קטלוג המוצרים לחיפוש

ב-GitHub Actions כל רשת רצה במקביל בג'וב נפרד, ובסוף ג'וב אחד מריץ --finalize.

אם ההורדה של רשת נכשלה (למשל האתר שלה למטה) — הנתונים הקודמים שלה
נשארים במאגר, ורק נרשם שהניסיון נכשל.

חיבור למסד הנתונים: משתנה הסביבה DATABASE_URL, למשל
postgresql://postgres.<ref>:<password>@aws-0-eu-central-1.pooler.supabase.com:5432/postgres
"""

import argparse
import csv
import io
import os
import sys
import tempfile
import time
import traceback

import psycopg2

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from aggregate import aggregate_chain  # noqa: E402
from chains import display_name  # noqa: E402

COLUMNS = [
    "chain_key",
    "item_code",
    "supermarket_name",
    "item_name",
    "manufacturer_name",
    "quantity",
    "unit_qty",
    "is_weighted",
    "min_price",
    "median_price",
    "max_price",
    "store_count",
    "last_update",
]


def connect():
    url = os.environ.get("DATABASE_URL")
    if not url:
        sys.exit("חסר משתנה הסביבה DATABASE_URL (מחרוזת החיבור ל-Postgres)")
    return psycopg2.connect(url)


def _ensure_chain(cur, chain_key, name):
    cur.execute(
        """
        INSERT INTO chains (chain_key, supermarket_name) VALUES (%s, %s)
        ON CONFLICT (chain_key) DO UPDATE SET supermarket_name = EXCLUDED.supermarket_name
        """,
        (chain_key, name),
    )


def record_failure(conn, chain_key, name, error):
    with conn, conn.cursor() as cur:
        _ensure_chain(cur, chain_key, name)
        cur.execute(
            "UPDATE chains SET last_attempt_at = now(), last_error = %s WHERE chain_key = %s",
            (error[:2000], chain_key),
        )


def write_chain(conn, chain_key, name, rows, store_count, data_date):
    """מחליף את כל המחירים של הרשת בתמונת המצב החדשה, בטרנזקציה אחת."""
    buf = io.StringIO()
    writer = csv.writer(buf)
    for r in rows:
        r = {**r, "chain_key": chain_key, "supermarket_name": name}
        writer.writerow(["" if r.get(c) is None else r[c] for c in COLUMNS])
    buf.seek(0)

    with conn, conn.cursor() as cur:
        _ensure_chain(cur, chain_key, name)
        cur.execute("DELETE FROM chain_prices WHERE chain_key = %s", (chain_key,))
        cur.copy_expert(
            f"COPY chain_prices ({', '.join(COLUMNS)}) FROM STDIN WITH (FORMAT csv, NULL '')",
            buf,
        )
        cur.execute(
            """
            UPDATE chains SET store_count = %s, item_count = %s, data_date = %s,
                   updated_at = now(), last_attempt_at = now(), last_error = NULL
            WHERE chain_key = %s
            """,
            (store_count, len(rows), data_date, chain_key),
        )


def publish_folder(conn, chain_key, name, folder):
    rows, store_count, data_date = aggregate_chain(folder)
    if not rows:
        record_failure(conn, chain_key, name, "לא נמצאו קובצי מחירים")
        print(f"[{chain_key}] לא נמצאו קובצי מחירים — הנתונים הקודמים נשארים")
        return False
    write_chain(conn, chain_key, name, rows, store_count, data_date)
    print(f"[{chain_key}] {name}: {store_count} סניפים, {len(rows):,} מוצרים, נתונים מ-{data_date}")
    return True


def publish_chain(conn, chain_key, limit=None):
    from download import chain_folder, download_chain

    name = display_name(chain_folder(chain_key))
    started = time.time()
    with tempfile.TemporaryDirectory(prefix=f"dumps-{chain_key}-") as tmp:
        try:
            folder = download_chain(chain_key, tmp, limit=limit)
            ok = publish_folder(conn, chain_key, name, folder)
        except Exception as exc:  # pylint: disable=broad-except
            conn.rollback()
            traceback.print_exc()
            record_failure(conn, chain_key, name, f"{type(exc).__name__}: {exc}")
            ok = False
    print(f"[{chain_key}] {time.time() - started:.0f} שניות")
    return ok


def finalize(conn):
    with conn, conn.cursor() as cur:
        cur.execute("SELECT rebuild_products()")
        count = cur.fetchone()[0]
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute("ANALYZE chains; ANALYZE chain_prices; ANALYZE products;")
    print(f"קטלוג המוצרים נבנה מחדש: {count:,} מוצרים")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("chains", nargs="*", help="שמות רשתות, למשל SHUFERSAL RAMI_LEVY")
    parser.add_argument("--all", action="store_true", help="כל הרשתות")
    parser.add_argument("--finalize", action="store_true", help="בניית קטלוג המוצרים מחדש")
    parser.add_argument("--limit", type=int, help="מספר קבצים מקסימלי לרשת (לבדיקה)")
    parser.add_argument(
        "--from-folder",
        metavar="DIR",
        help="בלי הורדה: לטעון תיקיית dumps קיימת (DIR/<תיקיית רשת>), למשל לבדיקות",
    )
    args = parser.parse_args()

    conn = connect()

    if args.from_folder:
        for folder in sorted(os.listdir(args.from_folder)):
            path = os.path.join(args.from_folder, folder)
            if os.path.isdir(path) and folder != "status":
                publish_folder(conn, folder, display_name(folder), path)
    else:
        from download import all_chains

        chain_keys = all_chains() if args.all else [c.upper() for c in args.chains]
        for chain_key in chain_keys:
            publish_chain(conn, chain_key, limit=args.limit)

    if args.finalize or args.all or args.from_folder:
        finalize(conn)
    conn.close()


if __name__ == "__main__":
    main()
