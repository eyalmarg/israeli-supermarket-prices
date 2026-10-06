from datetime import datetime
from decimal import Decimal

from sqlalchemy import text

from db import engine

# כל המחירים כאן הם מחירים רגילים (ItemPrice מקובצי PriceFull).
# מבצעים לא נטענים למסד הנתונים בכלל.

_STORE_JOIN = "LEFT JOIN stores s ON s.chain_id = p.chain_id AND s.store_id = p.store_id"


def _clean_value(v):
    if isinstance(v, Decimal):
        return float(v)
    if isinstance(v, datetime):
        return v.isoformat()  # זמן ישראל, בלי אזור זמן — הדפדפן מציג אותו כמו שהוא
    return v


def _clean(row):
    return {k: _clean_value(v) for k, v in dict(row).items()}


def _all(sql, params=None):
    with engine.connect() as conn:
        rows = conn.execute(text(sql), params or {}).mappings().all()
    return [_clean(r) for r in rows]


def _one(sql, params=None):
    rows = _all(sql, params)
    return rows[0] if rows else None


def search_products(term: str, limit: int = 40):
    """חיפוש מוצר לפי שם/יצרן (כל המילים חייבות להופיע) או לפי ברקוד."""
    columns = """
        item_code, item_name, manufacturer_name, quantity, unit_qty, is_weighted,
        chain_count, store_count, min_price, max_price
    """
    digits = term.replace(" ", "")
    if digits.isdigit() and len(digits) >= 5:
        return _all(
            f"SELECT {columns} FROM products WHERE item_code = :code",
            {"code": digits.lstrip("0") or "0"},
        )

    words = [w for w in term.split() if w][:6]
    params = {"limit": limit}
    conditions = []
    for i, word in enumerate(words):
        params[f"w{i}"] = f"%{word}%"
        conditions.append(f"(item_name ILIKE :w{i} OR manufacturer_name ILIKE :w{i})")
    return _all(
        f"""
        SELECT {columns}
        FROM products
        WHERE {' AND '.join(conditions)}
        ORDER BY chain_count DESC, store_count DESC, length(item_name), item_name
        LIMIT :limit
        """,
        params,
    )


def get_product(item_code: str, city: str | None = None):
    """פרטי מוצר + השוואה לפי רשת + רשימת כל הסניפים, אופציונלית בעיר מסוימת."""
    product = _one("SELECT * FROM products WHERE item_code = :code", {"code": item_code})
    if not product:
        return None
    params = {"code": item_code, "city": city}
    city_filter = "AND (:city IS NULL OR s.city = :city)"

    product["chains"] = _all(
        f"""
        SELECT
            p.supermarket_name,
            COUNT(*)                                                  AS store_count,
            MIN(p.item_price)                                         AS min_price,
            percentile_cont(0.5) WITHIN GROUP (ORDER BY p.item_price) AS median_price,
            MAX(p.item_price)                                         AS max_price,
            MAX(p.price_update_date)                                  AS last_update
        FROM prices p
        {_STORE_JOIN}
        WHERE p.item_code = :code {city_filter}
        GROUP BY p.supermarket_name
        ORDER BY min_price, median_price
        """,
        params,
    )
    product["stores"] = _all(
        f"""
        SELECT
            p.supermarket_name, p.store_id, s.store_name, s.sub_chain_name,
            s.address, s.city, p.item_price, p.unit_of_measure_price,
            p.unit_of_measure, p.price_update_date
        FROM prices p
        {_STORE_JOIN}
        WHERE p.item_code = :code {city_filter}
        ORDER BY p.item_price, p.supermarket_name, s.city
        LIMIT 500
        """,
        params,
    )
    return product


def compare_basket(items, city: str | None = None):
    """משווה סל קניות: לכל רשת — הסניף הזול ביותר מבין אלה שיש בהם הכי הרבה
    מהמוצרים בסל. מחזיר גם את המחיר של כל מוצר באותו סניף."""
    codes = [i["item_code"] for i in items]
    qtys = [i["qty"] for i in items]
    return _all(
        f"""
        WITH basket AS (
            SELECT * FROM unnest(CAST(:codes AS text[]), CAST(:qtys AS numeric[]))
                AS t(item_code, qty)
        ),
        per_store AS (
            SELECT p.supermarket_name, p.chain_id, p.store_id,
                   COUNT(*)                   AS found_count,
                   SUM(p.item_price * b.qty)  AS total
            FROM prices p
            JOIN basket b ON b.item_code = p.item_code
            {_STORE_JOIN}
            WHERE (:city IS NULL OR s.city = :city)
            GROUP BY p.supermarket_name, p.chain_id, p.store_id
        ),
        best_per_chain AS (
            SELECT DISTINCT ON (supermarket_name) *
            FROM per_store
            ORDER BY supermarket_name, found_count DESC, total ASC
        )
        SELECT
            r.supermarket_name, r.store_id, r.found_count, r.total,
            s.store_name, s.sub_chain_name, s.address, s.city,
            (SELECT json_object_agg(p.item_code, p.item_price)
               FROM prices p
              WHERE p.chain_id = r.chain_id AND p.store_id = r.store_id
                AND p.item_code = ANY(CAST(:codes AS text[]))) AS item_prices
        FROM best_per_chain r
        LEFT JOIN stores s ON s.chain_id = r.chain_id AND s.store_id = r.store_id
        ORDER BY r.found_count DESC, r.total ASC
        """,
        {"codes": codes, "qtys": qtys, "city": city},
    )


def list_cities():
    """ערים שיש בהן סניפים עם מחירים (בלי ערים שמופיעות רק כקוד מספרי)."""
    return [
        r["city"]
        for r in _all(
            """
            SELECT s.city, COUNT(*) AS n
            FROM stores s
            JOIN store_snapshots ss ON ss.chain_id = s.chain_id AND ss.store_id = s.store_id
            WHERE s.city IS NOT NULL AND s.city !~ '^[0-9]+$'
            GROUP BY s.city
            ORDER BY n DESC, s.city
            """
        )
    ]


def list_supermarkets():
    return _all(
        """
        SELECT supermarket_name,
               COUNT(*)            AS store_count,
               SUM(rows_loaded)    AS price_count,
               MAX(file_timestamp) AS last_update
        FROM store_snapshots
        GROUP BY supermarket_name
        ORDER BY supermarket_name
        """
    )


def get_stats():
    return _one(
        """
        SELECT
            (SELECT COUNT(DISTINCT supermarket_name) FROM store_snapshots) AS supermarket_count,
            (SELECT COUNT(*) FROM store_snapshots)                         AS stores_count,
            (SELECT COUNT(*) FROM products)                                AS products_count,
            (SELECT COALESCE(SUM(rows_loaded), 0) FROM store_snapshots)    AS prices_count,
            (SELECT MAX(file_timestamp) FROM store_snapshots)              AS last_update
        """
    ) or {}
