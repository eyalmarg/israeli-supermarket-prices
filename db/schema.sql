-- ============================================================
-- סכמת מסד נתונים: מחירי סופרמרקטים בישראל
-- 3 טבלאות, כל אחת מהווה UNION של הנתונים מכל הרשתות,
-- עם עמודת supermarket_name שמזהה מאיזו רשת הגיעה כל שורה.
-- ============================================================

CREATE EXTENSION IF NOT EXISTS pg_trgm;  -- לחיפוש טקסט מהיר (LIKE / ILIKE)

-- ------------------------------------------------------------
-- 1) חנויות (Union של קובצי "Stores" מכל הרשתות)
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS stores (
    id                BIGSERIAL PRIMARY KEY,
    supermarket_name  TEXT NOT NULL,          -- שם הרשת המנורמל, למשל 'שופרסל'
    chain_id          TEXT,
    sub_chain_id      TEXT,
    store_id          TEXT NOT NULL,
    store_type        TEXT,
    store_name        TEXT,
    address           TEXT,
    city              TEXT,
    zip_code          TEXT,
    last_update       TIMESTAMP,
    source_file       TEXT,                   -- שם קובץ המקור (למעקב/דיבוג)
    loaded_at         TIMESTAMP NOT NULL DEFAULT now(),
    UNIQUE (supermarket_name, chain_id, sub_chain_id, store_id)
);

CREATE INDEX IF NOT EXISTS idx_stores_supermarket ON stores (supermarket_name);
CREATE INDEX IF NOT EXISTS idx_stores_city        ON stores (city);

-- ------------------------------------------------------------
-- 2) מחירים (Union של קובצי "PriceFull/Price" מכל הרשתות)
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS prices (
    id                    BIGSERIAL PRIMARY KEY,
    supermarket_name      TEXT NOT NULL,
    chain_id              TEXT,
    sub_chain_id          TEXT,
    store_id              TEXT,
    item_code             TEXT NOT NULL,
    item_type             TEXT,
    item_name             TEXT,
    manufacturer_name     TEXT,
    manufacture_country   TEXT,
    unit_qty              TEXT,
    quantity              NUMERIC(12,3),
    unit_of_measure       TEXT,
    is_weighted           BOOLEAN,
    qty_in_package        NUMERIC(12,3),
    item_price            NUMERIC(12,2),
    unit_of_measure_price NUMERIC(12,2),
    allow_discount        BOOLEAN,
    item_status           TEXT,
    price_update_date     TIMESTAMP,
    source_file           TEXT,
    loaded_at             TIMESTAMP NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_prices_supermarket ON prices (supermarket_name);
CREATE INDEX IF NOT EXISTS idx_prices_item_code   ON prices (item_code);
CREATE INDEX IF NOT EXISTS idx_prices_store       ON prices (supermarket_name, store_id);
CREATE INDEX IF NOT EXISTS idx_prices_item_name_trgm ON prices USING gin (item_name gin_trgm_ops);

-- ------------------------------------------------------------
-- 3) מבצעים (Union של קובצי "PromoFull/Promo" מכל הרשתות)
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS promotions (
    id                      BIGSERIAL PRIMARY KEY,
    supermarket_name        TEXT NOT NULL,
    chain_id                TEXT,
    sub_chain_id             TEXT,
    store_id                TEXT,
    promotion_id             TEXT,
    promotion_description    TEXT,
    item_code                TEXT,
    discounted_price          NUMERIC(12,2),
    discount_rate             NUMERIC(6,2),
    min_qty                   NUMERIC(12,3),
    max_qty                   NUMERIC(12,3),
    promotion_start_date      TIMESTAMP,
    promotion_end_date        TIMESTAMP,
    club_id                    TEXT,           -- מבצע מועדון (אם רלוונטי)
    source_file                TEXT,
    loaded_at                  TIMESTAMP NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_promo_supermarket ON promotions (supermarket_name);
CREATE INDEX IF NOT EXISTS idx_promo_item_code   ON promotions (item_code);
CREATE INDEX IF NOT EXISTS idx_promo_dates        ON promotions (promotion_start_date, promotion_end_date);

-- ------------------------------------------------------------
-- טבלת סטטוס עזר: מתי כל רשת עודכנה לאחרונה (לתצוגה באתר)
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS load_log (
    id                BIGSERIAL PRIMARY KEY,
    supermarket_name  TEXT NOT NULL,
    table_name        TEXT NOT NULL,
    rows_loaded       INTEGER NOT NULL,
    loaded_at         TIMESTAMP NOT NULL DEFAULT now()
);
