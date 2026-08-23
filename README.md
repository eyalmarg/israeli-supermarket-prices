# מחיר·עגלה — השוואת מחירי סופרמרקטים בישראל

אתר מקומי (רץ אצלכם על המחשב) שמוריד את קובצי המחירים הרשמיים
שכל רשתות השיווק בישראל מחויבות לפרסם על-פי
[חוק קידום התחרות בענפי המזון והפארם](https://www.gov.il/he/pages/cpfta_prices_regulations)
("חוק שקיפות מחירים"), מאחד אותם למסד נתונים אחד, ומאפשר לחפש
מוצר ולהשוות מחיר בין כל הרשתות.

כל הכלים בפרויקט **חינמיים וקוד-פתוח**: Python, PostgreSQL, Flask,
ושתי חבילות קוד-פתוח קהילתיות שמטפלות בהורדה ובפירסור של הקבצים.

## איך זה בנוי

```
gov.il (רשימת קישורים)
        │
        ▼
il_supermarket_scarper  (מוריד XML גולמי מכל רשת)  →  dumps/
        │
        ▼
il_supermarket_parsers  (ממיר ל-CSV מנורמל)         →  outputs/
        │
        ▼
etl/load_to_postgres.py (מאחד ל-3 טבלאות + supermarket_name) → PostgreSQL
        │
        ▼
Flask API + אתר חיפוש/השוואה (backend/app.py)
```

3 הטבלאות במסד הנתונים (ראו `db/schema.sql`):

| טבלה | תוכן | מקור |
|---|---|---|
| `stores` | כל הסניפים של כל הרשתות | קובצי "Stores" |
| `prices` | כל המחירים של כל המוצרים בכל סניף | קובצי "PriceFull" |
| `promotions` | כל המבצעים הפעילים | קובצי "PromoFull" |

כל טבלה היא **UNION** של הנתונים מכל הרשתות, עם עמודת
`supermarket_name` שמזהה מאיזו רשת הגיעה כל שורה.

---

## התקנה (פעם אחת)

### 1. דרישות מוקדמות
- Python 3.10+
- PostgreSQL (חינמי): [הורדה מ-postgresql.org](https://www.postgresql.org/download/)
  לחלופין ב-macOS: `brew install postgresql`, ב-Ubuntu: `sudo apt install postgresql`

### 2. יצירת מסד הנתונים
```bash
# פותחים psql ומריצים:
createdb supermarket_prices
```

### 3. הגדרת הפרויקט
```bash
cd israeli-supermarket-prices
python -m venv venv
source venv/bin/activate        # ב-Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# ערכו את .env עם פרטי ה-Postgres שלכם (משתמש/סיסמה שהגדרתם בהתקנה)
```

---

## הרצה

### שלב 1: הבאת הנתונים (ETL)
```bash
./run_etl.sh
```
זה מריץ ברצף: הורדה → פירסור → טעינה למסד הנתונים.
**זה עשוי לקחת זמן** — יש כ-35 רשתות עם אלפי קבצים.

לבדיקה מהירה בהתחלה, מומלץ להגביל את ההיקף כדי לוודא שהכל עובד
לפני הרצה מלאה. ב-`.env` בטלו את ההערה (`#`) משורות אלו:
```
ENABLED_SCRAPERS=SHUFERSAL,RAMI_LEVY
LIMIT=5
```
כך תורידו רק כמה קבצים משתי רשתות, ותוכלו לוודא שהכול עובד תוך דקה-שתיים.
כשהכול תקין — מחקו/כבו את ההגבלות והריצו שוב על מלוא הנתונים.

**חשוב:** בין `etl/download.py` ל-`etl/parse.py` מומלץ להריץ:
```bash
python etl/inspect_csv.py
```
זה מציג את שמות העמודות בפועל בקבצי ה-CSV שנוצרו, כדי לוודא שהמיפוי
ב-`etl/load_to_postgres.py` תואם. אם עמודה חשובה לא מזוהה — פשוט
הוסיפו את שמה המדויק לרשימת ה-`candidates` המתאימה בקובץ הזה.

### שלב 2: הרצת האתר
```bash
./run_server.sh
```
ואז פתחו בדפדפן: **http://localhost:5000**

### עדכון נתונים (ריצה חוזרת)
כדי לרענן מחירים, פשוט הריצו שוב `./run_etl.sh`. שימו לב שהוא
**מוסיף** שורות חדשות (לא מוחק ישנות) — אם תרצו טבלה "נקייה" בכל
ריצה, אפשר להוסיף `TRUNCATE stores, prices, promotions;` בתחילת
`etl/load_to_postgres.py`, או להריץ ב-psql לפני כל ריענון.

---

## מבנה הפרויקט

```
db/schema.sql              סכמת ה-SQL (3 הטבלאות)
etl/chains.py               מיפוי קוד-רשת → שם עברי
etl/download.py              שלב 1: הורדת XML גולמי
etl/parse.py                  שלב 2: המרה ל-CSV
etl/inspect_csv.py             כלי עזר: בדיקת שמות עמודות בפועל
etl/load_to_postgres.py         שלב 3: טעינה למסד הנתונים
backend/app.py                   שרת Flask + API
backend/queries.py                שאילתות SQL
frontend/templates/index.html      דף האתר
frontend/static/                    CSS + JS
```

## הערות חשובות

- **תלות בחבילות קהילתיות**: הפרויקט משתמש ב-
  [`il_supermarket_scarper`](https://github.com/OpenIsraeliSupermarkets/israeli-supermarket-scarpers)
  ו-[`il_supermarket_parsers`](https://github.com/OpenIsraeliSupermarkets/israeli-supermarket-parsers) —
  חבילות קוד-פתוח בתחזוקה קהילתית (מוגדרות ע"י המתחזקים כ"beta").
  לפעמים רשת משנה את הפורמט שלה ושוברת את הסקרייפר לזמן מה — זה
  תקין וקורה גם למתחזקים עצמם (יש להם בדיקות אוטומטיות יומיות).
- **גישה מחוץ לישראל**: חלק מאתרי הרשתות חסומים ל-IP-ים מחוץ לישראל.
  אם מריצים את זה מחו"ל, ייתכן שחלק מהרשתות ייכשלו בהורדה.
  זה לא באג בקוד שלכם.
- **שימוש אישי**: המחירים שייכים לרשתות ומתפרסמים על-פי חובה
  חוקית לצורך שקיפות צרכנית. הפרויקט הזה הוא כלי אישי להצגה
  וניתוח של נתונים אלה, ולא שירות מסחרי.
