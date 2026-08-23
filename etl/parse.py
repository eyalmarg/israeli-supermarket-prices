"""
שלב 2: המרת קובצי ה-XML הגולמיים ל-CSV מנורמל, לכל רשת בנפרד.

משתמש בחבילת הקוד-הפתוח החינמית il_supermarket_parsers, שמטפלת
בהבדלים הקטנים בין הסכמות של הרשתות השונות:
https://github.com/OpenIsraeliSupermarkets/israeli-supermarket-parsers

הרצה (אחרי etl/download.py):
    python etl/parse.py
"""

import os
import sys
from dotenv import load_dotenv

load_dotenv()

DUMPS_FOLDER = os.environ.get("DUMPS_FOLDER", "dumps")
OUTPUTS_FOLDER = os.environ.get("OUTPUTS_FOLDER", "outputs")


def main():
    if not os.path.isdir(DUMPS_FOLDER):
        print(f"התיקייה {DUMPS_FOLDER} לא קיימת. הריצו קודם: python etl/download.py")
        sys.exit(1)

    os.makedirs(OUTPUTS_FOLDER, exist_ok=True)

    try:
        from il_supermarket_parsers import ConvertingTask
    except ImportError:
        print("חסרה החבילה il-supermarket-parsers. הריצו: pip install -r requirements.txt")
        sys.exit(1)

    print(f"ממיר קבצים מ-{DUMPS_FOLDER} ל-CSV בתיקייה {OUTPUTS_FOLDER} ...")

    task = ConvertingTask(
        source_configuration={"folder": DUMPS_FOLDER},
        output_configuration=[{"output_mode": "csv", "output_folder": OUTPUTS_FOLDER}],
        status_configuration={"database_type": "json", "base_path": OUTPUTS_FOLDER},
    )
    task.start()
    task.join()

    print("פירסור הושלם.")
    print(f"קובצי CSV מנורמלים נמצאים בתיקייה: {os.path.abspath(OUTPUTS_FOLDER)}")
    print("מומלץ להריץ קודם: python etl/inspect_csv.py   (כדי לוודא שהמיפוי בהתאמה)")
    print("השלב הבא: python etl/load_to_postgres.py")


if __name__ == "__main__":
    main()
