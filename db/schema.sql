-- ============================================================
-- סכמת מסד נתונים: השוואת מחירי סופרמרקטים בישראל (מחירים רגילים בלבד)
--
-- המקור: קובצי PriceFull שכל רשת מפרסמת לפי חוק שקיפות המחירים.
-- קובצי מבצעים לא נטענים בכלל — כל מחיר כאן הוא המחיר הרגיל על המדף.
--
-- כדי שהמאגר ייכנס למסלול החינמי של Supabase (500MB), לא נשמר מחיר
-- לכל סניף. לכל (רשת, מוצר) נשמרים הזול / החציון / היקר מבין כל
-- הסניפים של הרשת, ומספר הסניפים.
--
-- האתר קורא את הנתונים דרך הפונקציות בסוף הקובץ (Supabase RPC) עם
-- מפתח ציבורי לקריאה בלבד. הכתיבה נעשית רק מ-GitHub Actions.
--
-- הקובץ אידמפוטנטי: אפשר להריץ אותו שוב בבטחה.
-- ============================================================

-- ------------------------------------------------------------
-- רשתות: מצב העדכון האחרון של כל רשת
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS chains (
    chain_key         TEXT PRIMARY KEY,        -- שם הסקרייפר, למשל SHUFERSAL
    supermarket_name  TEXT NOT NULL,           -- שם לתצוגה, למשל 'שופרסל'
    store_count       INTEGER NOT NULL DEFAULT 0,
    item_count        INTEGER NOT NULL DEFAULT 0,
    data_date         TIMESTAMP,               -- תאריך הקובץ העדכני ביותר שנטען
    updated_at        TIMESTAMPTZ,             -- מתי הנתונים של הרשת הוחלפו לאחרונה
    last_attempt_at   TIMESTAMPTZ,             -- ניסיון ההורדה האחרון (גם אם נכשל)
    last_error        TEXT
);

-- ------------------------------------------------------------
-- מחיר רגיל לכל (רשת, מוצר), מסוכם על פני כל הסניפים של הרשת
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS chain_prices (
    chain_key         TEXT NOT NULL REFERENCES chains (chain_key) ON DELETE CASCADE,
    item_code         TEXT NOT NULL,           -- ברקוד
    supermarket_name  TEXT NOT NULL,
    item_name         TEXT,
    manufacturer_name TEXT,
    quantity          NUMERIC(12,3),
    unit_qty          TEXT,
    is_weighted       BOOLEAN,
    min_price         NUMERIC(12,2) NOT NULL,
    median_price      NUMERIC(12,2) NOT NULL,
    max_price         NUMERIC(12,2) NOT NULL,
    store_count       INTEGER NOT NULL,
    last_update       TIMESTAMP,
    PRIMARY KEY (chain_key, item_code)
);

CREATE INDEX IF NOT EXISTS idx_chain_prices_item ON chain_prices (item_code);

-- ------------------------------------------------------------
-- קטלוג מוצרים לחיפוש — נבנה מחדש מ-chain_prices אחרי כל עדכון
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

CREATE INDEX IF NOT EXISTS idx_products_rank ON products (chain_count DESC, store_count DESC);

-- ------------------------------------------------------------
-- הרשאות: קריאה בלבד לציבור
-- ------------------------------------------------------------
ALTER TABLE chains       ENABLE ROW LEVEL SECURITY;
ALTER TABLE chain_prices ENABLE ROW LEVEL SECURITY;
ALTER TABLE products     ENABLE ROW LEVEL SECURITY;

DO $$
DECLARE t TEXT;
BEGIN
    FOREACH t IN ARRAY ARRAY['chains', 'chain_prices', 'products'] LOOP
        IF NOT EXISTS (
            SELECT 1 FROM pg_policies WHERE tablename = t AND policyname = 'public read'
        ) THEN
            EXECUTE format('CREATE POLICY "public read" ON %I FOR SELECT TO anon, authenticated USING (true)', t);
        END IF;
    END LOOP;
END $$;

-- ------------------------------------------------------------
-- בנייה מחדש של קטלוג המוצרים (נקרא מה-ETL)
-- ------------------------------------------------------------
CREATE OR REPLACE FUNCTION rebuild_products() RETURNS INTEGER
LANGUAGE plpgsql SET search_path = public AS $$
DECLARE n INTEGER;
BEGIN
    DELETE FROM products;
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
        SUM(store_count),
        MIN(min_price),
        MAX(max_price)
    FROM chain_prices
    GROUP BY item_code;
    GET DIAGNOSTICS n = ROW_COUNT;
    RETURN n;
END $$;

REVOKE EXECUTE ON FUNCTION rebuild_products() FROM PUBLIC, anon, authenticated;

-- ------------------------------------------------------------
-- פונקציות לאתר (נקראות דרך /rest/v1/rpc/...)
-- ------------------------------------------------------------

-- חיפוש לפי שם/יצרן (כל המילים חייבות להופיע) או לפי ברקוד
CREATE OR REPLACE FUNCTION search_products(q TEXT)
RETURNS SETOF products
LANGUAGE sql STABLE SET search_path = public AS $$
    WITH input AS (
        SELECT trim(regexp_replace(coalesce(q, ''), '\s+', ' ', 'g')) AS term
    ),
    words AS (
        SELECT '%' || replace(replace(replace(w, '\', '\\'), '%', '\%'), '_', '\_') || '%' AS pattern
        FROM input, unnest(string_to_array(term, ' ')) AS w
        WHERE w <> ''
        LIMIT 6
    )
    SELECT p.*
    FROM products p, input
    WHERE length(input.term) >= 2
      AND CASE
            WHEN replace(input.term, ' ', '') ~ '^[0-9]{5,}$'
                THEN p.item_code = coalesce(nullif(ltrim(replace(input.term, ' ', ''), '0'), ''), '0')
            ELSE NOT EXISTS (
                SELECT 1 FROM words
                WHERE NOT (p.item_name ILIKE words.pattern OR p.manufacturer_name ILIKE words.pattern)
            )
          END
    ORDER BY p.chain_count DESC, p.store_count DESC, length(p.item_name), p.item_name
    LIMIT 40
$$;

-- פרטי מוצר + השוואה בין הרשתות
CREATE OR REPLACE FUNCTION product_detail(code TEXT)
RETURNS JSON
LANGUAGE sql STABLE SET search_path = public AS $$
    SELECT json_build_object(
        'product', to_json(p),
        'chains', coalesce((
            SELECT json_agg(c ORDER BY c.median_price, c.min_price)
            FROM (
                SELECT cp.supermarket_name, cp.store_count, cp.min_price, cp.median_price,
                       cp.max_price, cp.last_update
                FROM chain_prices cp
                WHERE cp.item_code = p.item_code
            ) c
        ), '[]'::json)
    )
    FROM products p
    WHERE p.item_code = code
$$;

-- השוואת סל: לכל רשת — סכום המחיר החציוני (סניף "טיפוסי") וסכום המחיר הזול ביותר
-- items: [{"item_code": "...", "qty": 2}, ...]
CREATE OR REPLACE FUNCTION compare_basket(items JSONB)
RETURNS TABLE (
    supermarket_name TEXT,
    found_count      BIGINT,
    total            NUMERIC,
    total_min        NUMERIC,
    item_prices      JSON
)
LANGUAGE sql STABLE SET search_path = public AS $$
    WITH basket AS (
        SELECT x ->> 'item_code' AS item_code,
               least(greatest(coalesce((x ->> 'qty')::NUMERIC, 1), 0), 1000) AS qty
        FROM jsonb_array_elements(coalesce(items, '[]'::jsonb)) AS x
        LIMIT 100
    )
    SELECT cp.supermarket_name,
           COUNT(*),
           SUM(cp.median_price * b.qty),
           SUM(cp.min_price * b.qty),
           json_object_agg(cp.item_code, json_build_object('median', cp.median_price, 'min', cp.min_price))
    FROM chain_prices cp
    JOIN basket b ON b.item_code = cp.item_code
    GROUP BY cp.chain_key, cp.supermarket_name
    ORDER BY COUNT(*) DESC, SUM(cp.median_price * b.qty)
$$;

-- נתונים כלליים לכותרת האתר
CREATE OR REPLACE FUNCTION site_stats()
RETURNS JSON
LANGUAGE sql STABLE SET search_path = public AS $$
    SELECT json_build_object(
        'supermarket_count', (SELECT COUNT(*) FROM chains WHERE item_count > 0),
        'stores_count',      (SELECT COALESCE(SUM(store_count), 0) FROM chains WHERE item_count > 0),
        'products_count',    (SELECT COUNT(*) FROM products),
        'last_update',       (SELECT MAX(data_date) FROM chains WHERE item_count > 0),
        'chains', coalesce((
            SELECT json_agg(json_build_object(
                       'supermarket_name', supermarket_name,
                       'store_count', store_count,
                       'data_date', data_date)
                   ORDER BY supermarket_name)
            FROM chains WHERE item_count > 0
        ), '[]'::json)
    )
$$;
