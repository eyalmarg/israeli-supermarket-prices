"""
כלי עזר: מציג את שמות העמודות בפועל בכמה קובצי CSV לדוגמה מכל סוג
(חנויות / מחירים / מבצעים), כדי לוודא שהמיפוי בקובץ load_to_postgres.py
תואם למה שהחבילה il_supermarket_parsers בפועל מייצרת אצלכם.

אם עמודה חשובה לא מזוהה אצלכם - פשוט הוסיפו את השם המדויק שלה
לרשימת ה-candidates המתאימה בתוך COLUMN_MAP ב-load_to_postgres.py.

הרצה (אחרי etl/parse.py):
    python etl/inspect_csv.py
"""

import os
import sys
import glob
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

OUTPUTS_FOLDER = os.environ.get("OUTPUTS_FOLDER", "outputs")

CATEGORIES = {
    "stores (חנויות)": "store",
    "prices (מחירים)": "price",
    "promotions (מבצעים)": "promo",
}


def find_sample(keyword, limit=2):
    pattern = os.path.join(OUTPUTS_FOLDER, "**", "*.csv")
    matches = []
    for path in glob.iglob(pattern, recursive=True):
        if keyword in os.path.basename(path).lower():
            matches.append(path)
        if len(matches) >= limit:
            break
    return matches


def main():
    if not os.path.isdir(OUTPUTS_FOLDER):
        print(f"התיקייה {OUTPUTS_FOLDER} לא קיימת. הריצו קודם: python etl/parse.py")
        sys.exit(1)

    for label, keyword in CATEGORIES.items():
        print(f"\n=== {label} — קבצי לדוגמה שמכילים '{keyword}' בשם ===")
        samples = find_sample(keyword)
        if not samples:
            print("  (לא נמצא קובץ מתאים - בדקו ידנית בתיקיית outputs/)")
            continue
        for path in samples:
            print(f"\n  קובץ: {path}")
            try:
                df = pd.read_csv(path, nrows=3)
                print("  עמודות:", list(df.columns))
                print(df.head(2).to_string())
            except Exception as exc:  # pylint: disable=broad-except
                print(f"  שגיאה בקריאת הקובץ: {exc}")


if __name__ == "__main__":
    main()
