"""
שלב 1: הורדת קובצי המחירים הגולמיים (XML) מאתרי רשתות השיווק, לפי
רשימת הקישורים שמפורסמת ב-gov.il (חוק שקיפות מחירים):
https://www.gov.il/he/pages/cpfta_prices_regulations

משתמש בחבילת הקוד-הפתוח החינמית il_supermarket_scarper:
https://github.com/OpenIsraeliSupermarkets/israeli-supermarket-scarpers

מורידים רק שני סוגי קבצים:
  * Stores    — רשימת הסניפים (שם, כתובת, עיר)
  * PriceFull — המחיר הרגיל של כל מוצר בכל סניף (תמונת מצב מלאה)
קובצי מבצעים (Promo / PromoFull) לא מורדים בכלל.

הרצה:
    python etl/download.py

הגדרות (אופציונלי) דרך .env או משתני סביבה:
    ENABLED_SCRAPERS    - רשימת רשתות מופרדת בפסיקים, למשל SHUFERSAL,RAMI_LEVY
                          (ברירת מחדל: כל הרשתות)
    LIMIT               - מספר קבצים מקסימלי לכל רשת (לבדיקה מהירה)
    NUMBER_OF_PROCESSES - מספר רשתות שמורדות במקביל (ברירת מחדל: 4)
    KEEP_OLD_DUMPS      - 1 כדי לא למחוק הורדות קודמות לפני ההורדה
"""

import os
import shutil
import sys

from dotenv import load_dotenv

load_dotenv()

DUMPS_FOLDER = os.environ.get("DUMPS_FOLDER", "dumps")
FILE_TYPES = ["STORE_FILE", "PRICE_FULL_FILE"]


def _env_list(name):
    value = os.environ.get(name, "").strip()
    return [x.strip().upper() for x in value.split(",") if x.strip()] or None


def main():
    try:
        from il_supermarket_scarper import ScarpingTask, ScraperFactory
    except ImportError:
        print("חסרה החבילה il-supermarket-scraper. הריצו: pip install -r requirements.txt")
        sys.exit(1)

    scrapers = _env_list("ENABLED_SCRAPERS")
    if scrapers:
        known = set(ScraperFactory.all_scrapers_name())
        unknown = [s for s in scrapers if s not in known]
        if unknown:
            print(f"רשתות לא מוכרות: {unknown}")
            print(f"האפשרויות הן: {sorted(known)}")
            sys.exit(1)

    limit = os.environ.get("LIMIT", "").strip()
    limit = int(limit) if limit else None
    processes = int(os.environ.get("NUMBER_OF_PROCESSES", "4"))

    # כל הורדה היא תמונת מצב טרייה: מוחקים קבצים ישנים (וגם את קובצי
    # הסטטוס של הסקרייפר, אחרת הוא ידלג על קבצים שכבר "ראה").
    if os.path.isdir(DUMPS_FOLDER) and os.environ.get("KEEP_OLD_DUMPS") != "1":
        shutil.rmtree(DUMPS_FOLDER)
    os.makedirs(DUMPS_FOLDER, exist_ok=True)

    print(f"מוריד קובצי סניפים ומחירים מלאים לתיקייה: {os.path.abspath(DUMPS_FOLDER)}")
    print(f"רשתות: {', '.join(scrapers) if scrapers else 'כולן'}")
    print("זה יכול לקחת זמן (עשרות רשתות, מאות סניפים) — יש סבלנות...")

    task = ScarpingTask(
        enabled_scrapers=scrapers,
        files_types=FILE_TYPES,
        multiprocessing=processes,
        output_configuration={"output_mode": "disk", "base_storage_path": DUMPS_FOLDER},
        status_configuration={
            "database_type": "json",
            "base_path": os.path.join(DUMPS_FOLDER, "status"),
        },
    )
    task.start(limit=limit)
    task.join()

    xml_count = sum(
        1
        for _root, _dirs, files in os.walk(DUMPS_FOLDER)
        for f in files
        if not f.endswith(".json")
    )
    print(f"הורדה הושלמה: {xml_count} קבצים.")
    if xml_count == 0:
        print("לא הורד אף קובץ. שימו לב: חלק מאתרי הרשתות חסומים לגלישה מחוץ לישראל.")
        sys.exit(1)
    print("השלב הבא: python etl/load.py")


if __name__ == "__main__":
    main()
