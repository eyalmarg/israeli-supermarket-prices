from sqlalchemy import text
from db import engine


def search_products(term: str, limit: int = 30):
    """מחפש שמות מוצרים לפי מילת חיפוש, מחזיר עבור כל item_code
    את הטווח (מינ/מקס) של מחירים ואת מספר הרשתות שמוכרות אותו."""
    sql = text(
        """
        SELECT
            item_code,
            MAX(item_name)              AS item_name,
            COUNT(DISTINCT supermarket_name) AS supermarket_count,
            MIN(item_price)             AS min_price,
            MAX(item_price)             AS max_price
        FROM prices
        WHERE item_name ILIKE :term
          AND item_price IS NOT NULL
        GROUP BY item_code
        ORDER BY supermarket_count DESC, item_name
        LIMIT :limit
        """
    )
    with engine.connect() as conn:
        rows = conn.execute(sql, {"term": f"%{term}%", "limit": limit}).mappings().all()
    return [dict(r) for r in rows]


def compare_item(item_code: str):
    """משווה מחיר של פריט ספציפי בין כל הרשתות/סניפים, וכולל מבצע פעיל אם יש."""
    sql = text(
        """
        SELECT
            p.supermarket_name,
            p.store_id,
            s.city,
            s.store_name,
            p.item_name,
            p.item_price,
            p.unit_of_measure_price,
            p.unit_of_measure,
            p.price_update_date,
            pr.discounted_price,
            pr.promotion_description
        FROM prices p
        LEFT JOIN stores s
            ON s.supermarket_name = p.supermarket_name AND s.store_id = p.store_id
        LEFT JOIN promotions pr
            ON pr.supermarket_name = p.supermarket_name
           AND pr.store_id = p.store_id
           AND pr.item_code = p.item_code
           AND (pr.promotion_end_date IS NULL OR pr.promotion_end_date >= now())
        WHERE p.item_code = :item_code
          AND p.item_price IS NOT NULL
        ORDER BY COALESCE(pr.discounted_price, p.item_price) ASC
        LIMIT 200
        """
    )
    with engine.connect() as conn:
        rows = conn.execute(sql, {"item_code": item_code}).mappings().all()
    return [dict(r) for r in rows]


def list_supermarkets():
    sql = text(
        """
        SELECT supermarket_name, COUNT(*) AS item_count, MAX(loaded_at) AS last_loaded
        FROM prices
        GROUP BY supermarket_name
        ORDER BY supermarket_name
        """
    )
    with engine.connect() as conn:
        rows = conn.execute(sql).mappings().all()
    return [dict(r) for r in rows]


def get_stats():
    sql = text(
        """
        SELECT
            (SELECT COUNT(*) FROM stores)                       AS stores_count,
            (SELECT COUNT(*) FROM prices)                        AS prices_count,
            (SELECT COUNT(*) FROM promotions)                     AS promotions_count,
            (SELECT COUNT(DISTINCT supermarket_name) FROM prices) AS supermarket_count,
            (SELECT MAX(loaded_at) FROM prices)                    AS last_loaded
        """
    )
    with engine.connect() as conn:
        row = conn.execute(sql).mappings().first()
    return dict(row) if row else {}
