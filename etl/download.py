"""
שלב 1: הורדת קובצי המחירים הגולמיים (XML) מכל רשתות השיווק בישראל,
כפי שמפורסמות באתר הרשות להגנת הצרכן (chp.co.il / gov.il).

משתמש בחבילת הקוד-הפתוח החינמית il_supermarket_scarper:
https://github.com/OpenIsraeliSupermarkets/israeli-supermarket-scarpers

הרצה:
    python etl/download.py

הגדרות (אופציונלי) דרך .env או משתני סביבה:
    ENABLED_SCRAPERS   - רשימת רשתות מופרדת בפסיקים (ברירת מחדל: הכל)
    ENABLED_FILE_TYPES - STORE_FILE,PRICE_FILE,PROMO_FILE (ברירת מחדל: הכל)
    LIMIT              - מספר קבצים מקסימלי (שימושי לבדיקה מהירה)
    NUMBER_OF_PROCESSES- מספר תהליכים מקבילים (ברירת מחדל: 4)

שימו לב: מכיוון שהרשתות מעלות קבצים חדשים כל הזמן, יש להריץ סקריפט
זה בכל פעם שרוצים לרענן את הנתונים (אפשר לתזמן עם cron / Task Scheduler).
"""

import os
import sys
from dotenv import load_dotenv

load_dotenv()

DUMPS_FOLDER = os.environ.get("DUMPS_FOLDER", "dumps")

# מיישרים את שמות משתני הסביבה לאלה שהחבילה מצפה להם (כפי שמתועד ב-README
# של הפרויקט, אותם משתנים המשמשים גם את גרסת ה-Docker שלו).
os.environ.setdefault("STORAGE_PATH", DUMPS_FOLDER)
os.environ.setdefault("NUMBER_OF_PROCESSES", os.environ.get("NUMBER_OF_PROCESSES", "4"))


def main():
    os.makedirs(DUMPS_FOLDER, exist_ok=True)

    try:
        from il_supermarket_scarper import ScarpingTask
    except ImportError:
        print("חסרה החבילה il-supermarket-scraper. הריצו: pip install -r requirements.txt")
        sys.exit(1)

    print(f"מתחיל הורדה של קבצי מחירים גולמיים לתיקייה: {DUMPS_FOLDER}")
    print("זה יכול לקחת זמן (עשרות רשתות, אלפי סניפים) - יש סבלנות...")

    task = ScarpingTask()
    task.start()

    print("הורדה הושלמה.")
    print(f"קבצים גולמיים נמצאים בתיקייה: {os.path.abspath(DUMPS_FOLDER)}")
    print("השלב הבא: python etl/parse.py")


if __name__ == "__main__":
    main()
