-- ============================================================
-- סכמת מסד נתונים: מחירי סופרמרקטים בישראל (מחירים רגילים בלבד)
--
-- המקור: קובצי Stores ו-PriceFull שכל רשת מפרסמת לפי חוק שקיפות
-- המחירים. קובצי המבצעים (Promo/PromoFull) לא נטענים בכלל, כך
-- שכל מחיר באתר הוא המחיר הרגיל על המדף (ItemPrice).
-- ============================================================

CREATE EXTENSION IF NOT EXISTS pg_trgm;  -- חיפוש טקסט מהיר (ILIKE)

-- ------------------------------------------------------------
-- 1) סניפים — מקובצי Stores
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS stores (
    chain_id          TEXT NOT NULL,          -- מזהה רשת (GLN, 13 ספרות)
    store_id          TEXT NOT NULL,          -- מספר סניף בתוך הרשת (בלי אפסים מובילים)
    supermarket_name  TEXT NOT NULL,          -- שם הרשת בעברית, למשל 'שופרסל'
    sub_chain_id      TEXT,
    sub_chain_name    TEXT,                   -- תת-רשת, למשל 'שופרסל דיל'
    store_name        TEXT,
    address           TEXT,
    city              TEXT,
    source_file       TEXT,
    loaded_at         TIMESTAMP NOT NULL DEFAULT now(),
    PRIMARY KEY (chain_id, store_id)
);

CREATE INDEX IF NOT EXISTS idx_stores_city ON stores (city);

-- ------------------------------------------------------------
-- 2) מחירים — מקובצי PriceFull (תמונת מצב מלאה לכל סניף)
--    שורה אחת לכל (רשת, סניף, מוצר). טעינה חוזרת מחליפה את
--    כל המחירים של הסניף בתמונת המצב החדשה.
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS prices (
    chain_id              TEXT NOT NULL,
    store_id              TEXT NOT NULL,
    item_code             TEXT NOT NULL,      -- ברקוד
    supermarket_name      TEXT NOT NULL,
    item_name             TEXT,
    manufacturer_name     TEXT,
    quantity              NUMERIC(12,3),      -- כמות באריזה (למשל 1.000)
    unit_qty              TEXT,               -- יחידת הכמות (ליטר / ק"ג / יחידה...)
    unit_of_measure       TEXT,               -- יחידה למחיר ליחידה (למשל '100 גרם')
    is_weighted           BOOLEAN,            -- מוצר שקיל: המחיר הוא לק"ג
    item_price            NUMERIC(12,2) NOT NULL,  -- המחיר הרגיל
    unit_of_measure_price NUMERIC(12,2),
    price_update_date     TIMESTAMP,
    PRIMARY KEY (chain_id, store_id, item_code)
);

CREATE INDEX IF NOT EXISTS idx_prices_item_code ON prices (item_code);

-- ------------------------------------------------------------
-- 3) קטלוג מוצרים — טבלה נגזרת מ-prices, נבנית מחדש בסוף כל טעינה.
--    משמשת לחיפוש מהיר בלי לסרוק עשרות מיליוני שורות.
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS products (
    item_code         TEXT PRIMARY KEY,
    item_name         TEXT,
    manufacturer_name TEXT,
    quantity          NUMERIC(12,3),
    unit_qty          TEXT,
    is_weighted       BOOLEAN,
    chain_count       INTEGER NOT NULL,
    store_count       INTEGER NOT NULL,
    min_price         NUMERIC(12,2),
    max_price         NUMERIC(12,2)
);

CREATE INDEX IF NOT EXISTS idx_products_name_trgm ON products USING gin (item_name gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_products_mfr_trgm  ON products USING gin (manufacturer_name gin_trgm_ops);

-- ------------------------------------------------------------
-- 4) יומן טעינה — איזה קובץ נטען אחרון לכל סניף (מונע דריסה של
--    תמונת מצב חדשה בישנה, ומציג באתר מתי הנתונים עודכנו)
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS store_snapshots (
    chain_id          TEXT NOT NULL,
    store_id          TEXT NOT NULL,
    supermarket_name  TEXT NOT NULL,
    source_file       TEXT NOT NULL,
    file_timestamp    TIMESTAMP,
    rows_loaded       INTEGER NOT NULL,
    loaded_at         TIMESTAMP NOT NULL DEFAULT now(),
    PRIMARY KEY (chain_id, store_id)
);
