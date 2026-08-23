"""
שלב 3: טעינת כל קובצי ה-CSV (מכל הרשתות) לתוך 3 טבלאות ב-PostgreSQL:
stores, prices, promotions - כאשר כל טבלה היא UNION של הנתונים מכל
הרשתות, עם עמודת supermarket_name שמזהה את המקור.

הרצה (אחרי etl/parse.py, ואחרי יצירת הסכמה עם db/schema.sql):
    python etl/load_to_postgres.py

הערה חשובה על מיפוי עמודות:
העמודות הסטנדרטיות בקובצי המחירים הישראליים (לפי "המבנה האחיד" של
חוק שקיפות המחירים) הן בד"כ: ItemCode, ItemName, ManufacturerName,
ItemPrice, UnitOfMeasurePrice, Quantity, UnitOfMeasure, PriceUpdateDate
וכו'. מכיוון שלכל רשת יכולות להיות התאמות קטנות, המיפוי למטה גמיש:
לכל עמודת יעד יש רשימת "מועמדים" אפשריים, וההתאמה מתבצעת ללא תלות
ברישיות/קווים תחתונים/רווחים. אם אצלכם עמודה מסוימת לא מזוהה,
הריצו קודם etl/inspect_csv.py ותוסיפו את השם המדויק שחסר.
"""

import os
import re
import sys
import glob
import pandas as pd
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(__file__))
from chains import display_name  # noqa: E402

load_dotenv()

OUTPUTS_FOLDER = os.environ.get("OUTPUTS_FOLDER", "outputs")

DB_HOST = os.environ.get("DB_HOST", "localhost")
DB_PORT = os.environ.get("DB_PORT", "5432")
DB_NAME = os.environ.get("DB_NAME", "supermarket_prices")
DB_USER = os.environ.get("DB_USER", "postgres")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "postgres")

DB_URL = f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

CHUNK_SIZE = 5000


def _norm(name: str) -> str:
    """מנרמל שם עמודה להשוואה: אותיות קטנות, בלי רווחים/קווים תחתונים."""
    return re.sub(r"[\s_\-]+", "", str(name)).lower()


# ------------------------------------------------------------------
# מיפוי עמודות: target_column -> רשימת שמות מקור אפשריים (candidates)
# ------------------------------------------------------------------
STORE_COLUMN_MAP = {
    "chain_id":     ["chainid", "chainname"],
    "sub_chain_id": ["subchainid"],
    "store_id":     ["storeid", "storenumber"],
    "store_type":   ["storetype"],
    "store_name":   ["storename"],
    "address":      ["address"],
    "city":         ["city"],
    "zip_code":     ["zipcode"],
    "last_update":  ["lastupdatedate", "lastupdatetime", "bikoretno"],
}

PRICE_COLUMN_MAP = {
    "chain_id":              ["chainid"],
    "sub_chain_id":           ["subchainid"],
    "store_id":               ["storeid"],
    "item_code":              ["itemcode", "barcode"],
    "item_type":              ["itemtype"],
    "item_name":              ["itemname", "itemnm"],
    "manufacturer_name":      ["manufacturername", "manufactorname"],
    "manufacture_country":    ["manufacturecountry", "manufactorcountry"],
    "unit_qty":                ["unitqty", "unitofmeasure"],
    "quantity":                 ["quantity"],
    "unit_of_measure":          ["unitofmeasure", "unitmeasure"],
    "is_weighted":               ["bisweighted", "isweighted"],
    "qty_in_package":             ["qtyinpackage"],
    "item_price":                  ["itemprice", "price"],
    "unit_of_measure_price":        ["unitofmeasureprice"],
    "allow_discount":                ["allowdiscount"],
    "item_status":                     ["itemstatus"],
    "price_update_date":                ["priceupdatedate", "priceupdatetime"],
}

PROMO_COLUMN_MAP = {
    "chain_id":                 ["chainid"],
    "sub_chain_id":              ["subchainid"],
    "store_id":                   ["storeid"],
    "promotion_id":                 ["promotionid"],
    "promotion_description":         ["promotiondescription"],
    "item_code":                       ["itemcode", "barcode"],
    "discounted_price":                  ["discountedprice"],
    "discount_rate":                       ["discountrate"],
    "min_qty":                               ["minqty"],
    "max_qty":                                 ["maxqty"],
    "promotion_start_date":                     ["promotionstartdate"],
    "promotion_end_date":                         ["promotionenddate"],
    "club_id":                                     ["clubid"],
}

TABLE_CONFIG = {
    "stores":     {"keyword": "store", "column_map": STORE_COLUMN_MAP},
    "prices":     {"keyword": "price", "column_map": PRICE_COLUMN_MAP},
    "promotions": {"keyword": "promo", "column_map": PROMO_COLUMN_MAP},
}


def categorize_file(filename: str):
    """מזהה לאיזו טבלה שייך קובץ, לפי מילות מפתח בשם הקובץ.
    בודק promo לפני price כי 'promofull' מכיל גם 'price'-דמוי מילים לעיתים."""
    lower = filename.lower()
    if "promo" in lower:
        return "promotions"
    if "store" in lower:
        return "stores"
    if "price" in lower:
        return "prices"
    return None


def extract_chain_code(path: str, outputs_folder: str) -> str:
    """מנסה לחלץ את קוד הרשת מתוך מבנה התיקיות (outputs/<CHAIN_CODE>/...).
    אם אין תת-תיקייה כזו, נופל חזרה לחלק הראשון של שם הקובץ."""
    rel = os.path.relpath(path, outputs_folder)
    parts = rel.split(os.sep)
    if len(parts) > 1:
        return parts[0]
    # fallback: קידומת שם הקובץ עד לתו לא-אלפאנומרי ראשון
    base = os.path.splitext(os.path.basename(path))[0]
    match = re.match(r"[A-Za-z]+", base)
    return match.group(0) if match else base


def map_columns(df: pd.DataFrame, column_map: dict) -> pd.DataFrame:
    normalized_source = {_norm(c): c for c in df.columns}
    result = pd.DataFrame(index=df.index)
    for target, candidates in column_map.items():
        found_col = None
        for cand in candidates:
            if cand in normalized_source:
                found_col = normalized_source[cand]
                break
        result[target] = df[found_col] if found_col else None
    return result


def coerce_types(df: pd.DataFrame, table: str) -> pd.DataFrame:
    numeric_cols = {
        "prices": ["quantity", "qty_in_package", "item_price", "unit_of_measure_price"],
        "promotions": ["discounted_price", "discount_rate", "min_qty", "max_qty"],
        "stores": [],
    }
    bool_cols = {"prices": ["is_weighted", "allow_discount"], "promotions": [], "stores": []}
    date_cols = {
        "prices": ["price_update_date"],
        "promotions": ["promotion_start_date", "promotion_end_date"],
        "stores": ["last_update"],
    }

    for col in numeric_cols.get(table, []):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    for col in bool_cols.get(table, []):
        if col in df.columns:
            df[col] = (
                df[col]
                .astype(str)
                .str.strip()
                .isin(["1", "1.0", "true", "True", "כן"])
            )
    for col in date_cols.get(table, []):
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")
    return df


def load_file(engine, path: str, table: str, supermarket: str):
    column_map = TABLE_CONFIG[table]["column_map"]
    try:
        df = pd.read_csv(path, dtype=str, low_memory=False)
    except Exception as exc:  # pylint: disable=broad-except
        print(f"  ⚠ דילוג על קובץ שלא נקרא: {path} ({exc})")
        return 0

    if df.empty:
        return 0

    mapped = map_columns(df, column_map)
    mapped["supermarket_name"] = supermarket
    mapped["source_file"] = os.path.basename(path)
    mapped = coerce_types(mapped, table)

    # דרישת מינימום: לשורות מחיר/מבצע חייב להיות item_code; לחנות - store_id
    if table == "prices":
        mapped = mapped.dropna(subset=["item_code"])
    elif table == "stores":
        mapped = mapped.dropna(subset=["store_id"])

    if mapped.empty:
        return 0

    mapped.to_sql(table, engine, if_exists="append", index=False, method="multi", chunksize=CHUNK_SIZE)
    return len(mapped)


def main():
    if not os.path.isdir(OUTPUTS_FOLDER):
        print(f"התיקייה {OUTPUTS_FOLDER} לא קיימת. הריצו קודם: python etl/parse.py")
        sys.exit(1)

    engine = create_engine(DB_URL)

    # ודא שהסכמה קיימת (מריץ את schema.sql אם הטבלאות עוד לא נוצרו)
    schema_path = os.path.join(os.path.dirname(__file__), "..", "db", "schema.sql")
    with engine.begin() as conn:
        with open(schema_path, "r", encoding="utf-8") as f:
            conn.execute(text(f.read()))

    pattern = os.path.join(OUTPUTS_FOLDER, "**", "*.csv")
    all_files = list(glob.iglob(pattern, recursive=True))
    print(f"נמצאו {len(all_files)} קובצי CSV בתיקייה {OUTPUTS_FOLDER}")

    totals = {"stores": 0, "prices": 0, "promotions": 0}
    log_rows = []

    for path in all_files:
        table = categorize_file(os.path.basename(path))
        if table is None:
            continue
        chain_code = extract_chain_code(path, OUTPUTS_FOLDER)
        supermarket = display_name(chain_code)

        n = load_file(engine, path, table, supermarket)
        if n:
            totals[table] += n
            log_rows.append({"supermarket_name": supermarket, "table_name": table, "rows_loaded": n})

    if log_rows:
        pd.DataFrame(log_rows).to_sql("load_log", engine, if_exists="append", index=False)

    print("\n=== סיכום טעינה ===")
    for table, count in totals.items():
        print(f"  {table}: {count} שורות")
    print("\nהטעינה הושלמה. אפשר להריץ את השרת: python backend/app.py")


if __name__ == "__main__":
    main()
