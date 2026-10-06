# מחיר·עגלה — השוואת מחירי סופרמרקטים בישראל

אתר שמשווה מחירי מוצרים בין רשתות השיווק בישראל, על בסיס קובצי המחירים
שכל רשת מחויבת לפרסם לפי
[חוק קידום התחרות בענף המזון ("חוק שקיפות מחירים")](https://www.gov.il/he/pages/cpfta_prices_regulations).

- **חיפוש מוצר** לפי שם, יצרן או ברקוד
- **השוואה בין הרשתות** — לכל רשת: המחיר בסניף הזול, בסניף הטיפוסי (חציון) ובסניף היקר
- **השוואת סל קניות** — כמה עולה הסל בכל רשת, ואילו מוצרים חסרים בה

**מחירים רגילים בלבד.** האתר מציג את המחיר הרגיל על המדף (`ItemPrice` מקובצי
`PriceFull`). קובצי המבצעים (`Promo` / `PromoFull`) לא מורדים בכלל, כך שמבצעים,
הנחות כמות והנחות מועדון לא משפיעים על שום מחיר באתר.

## איך זה בנוי

הכול רץ בענן, בחינם, בלי שום התקנה:

```
GitHub Actions (כל יום ב-05:17 בערך)
   │  לכל רשת, במקביל: הורדת קובצי PriceFull → סיכום על פני כל הסניפים
   ▼
Supabase (PostgreSQL)
   │  chain_prices — לכל (רשת, מוצר): זול / חציון / יקר, מספר סניפים
   │  products     — קטלוג לחיפוש
   │  פונקציות SQL לקריאה בלבד: search_products, product_detail, compare_basket, site_stats
   ▼
Render (אתר סטטי, תיקיית frontend/)
      הדפדפן קורא ישירות מ-Supabase עם מפתח ציבורי לקריאה בלבד
```

- **למה בלי פירוט סניפים?** כל המחירים מכל הסניפים הם כמה GB, והמסלול החינמי של
  Supabase מוגבל ל-500MB. לכן נשמר לכל רשת סיכום של המחיר בסניפים שלה.
- **רשת שההורדה שלה נכשלה** (האתר שלה למטה, או חוסם גישה מחוץ לישראל) — הנתונים
  הקודמים שלה נשארים, ובתחתית האתר מופיע התאריך של הנתונים של כל רשת.
- **ההשוואה היא לפי ברקוד.** קודים פנימיים של רשת (`ItemType=0`, בעיקר ירקות ופירות
  במשקל) לא נכללים, כי הם שונים בכל רשת.
- **מוצר שקיל** — המחיר הוא לק"ג, ובסל הכמות היא בק"ג.

## הקמה (פעם אחת)

1. **Supabase**: להריץ את `db/schema.sql` ב-SQL Editor של הפרויקט.
2. **GitHub**: ב-Settings → Secrets and variables → Actions להוסיף secret בשם
   `DATABASE_URL` עם מחרוזת החיבור מ-Supabase: Connect → **Session pooler**
   (עם הסיסמה של מסד הנתונים במקום `[YOUR-PASSWORD]`).
   GitHub Actions לא תומך ב-IPv6, ולכן צריך את ה-pooler ולא את החיבור הישיר.
3. **הרצה ראשונה**: בלשונית Actions → Update prices → Run workflow.
4. **Render**: Static Site מהריפו, Publish directory: `frontend`, בלי פקודת build.

כתובת Supabase והמפתח הציבורי נמצאים ב-`frontend/js/config.js`.

## קבצים

```
.github/workflows/update-prices.yml   העדכון היומי
db/schema.sql                         טבלאות, הרשאות ופונקציות לאתר
etl/download.py                       הורדת קובצי PriceFull של רשת (il-supermarket-scraper)
etl/xml_reader.py                     קריאת ה-XML של כל הרשתות (מבנים שונים, UTF-16, gzip)
etl/aggregate.py                      סיכום רשת: הקובץ העדכני לכל סניף → זול/חציון/יקר
etl/publish.py                        הורדה + סיכום + כתיבה למסד הנתונים
etl/chains.py                         שמות הרשתות בעברית
frontend/                             האתר (HTML / CSS / JS סטטיים)
tests/                                בדיקות + קובצי XML לדוגמה בשלושה מבנים
```

עדכון ידני של רשת אחת (צריך `DATABASE_URL` בסביבה):
```bash
pip install -r requirements.txt
python etl/publish.py SHUFERSAL RAMI_LEVY --finalize
```

בדיקות:
```bash
pip install pytest && python -m pytest tests
```

## הערות

- הקבצים מורדים בעזרת חבילת הקוד-הפתוח
  [`il-supermarket-scraper`](https://github.com/OpenIsraeliSupermarkets/israeli-supermarket-scarpers).
  כשרשת משנה את האתר שלה, ההורדה שלה עלולה להישבר לזמן מה עד שהחבילה מתעדכנת.
- המחירים מתפרסמים לפי חובה חוקית לשקיפות צרכנית. האתר מציג אותם להשוואה בלבד,
  והם עשויים להשתנות ולא תמיד עדכניים לרגע זה.
