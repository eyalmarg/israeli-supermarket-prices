"""
הורדת קובצי המחירים הגולמיים (XML) מאתרי רשתות השיווק, לפי רשימת
הקישורים שמפורסמת ב-gov.il (חוק שקיפות מחירים):
https://www.gov.il/he/pages/cpfta_prices_regulations

משתמש בחבילת הקוד-הפתוח il_supermarket_scarper:
https://github.com/OpenIsraeliSupermarkets/israeli-supermarket-scarpers

מורידים רק קובצי PriceFull — המחיר הרגיל של כל מוצר בכל סניף.
קובצי מבצעים (Promo / PromoFull) לא מורדים בכלל.
"""

import os
import shutil

PRICE_FILE_TYPES = ["PRICE_FULL_FILE"]


def all_chains():
    from il_supermarket_scarper import ScraperFactory

    return ScraperFactory.all_scrapers_name()


def chain_folder(chain_key):
    """שם התיקייה שהסקרייפר יוצר לרשת, למשל RAMI_LEVY -> RamiLevy"""
    from il_supermarket_scarper import DumpFolderNames

    return DumpFolderNames[chain_key].value


def download_chain(chain_key, dumps_folder, limit=None, timeout_seconds=60 * 45):
    """מוריד את קובצי PriceFull של רשת אחת לתיקייה נקייה. מחזיר את נתיב התיקייה."""
    from il_supermarket_scarper import ScarpingTask

    if os.path.isdir(dumps_folder):
        shutil.rmtree(dumps_folder)
    os.makedirs(dumps_folder)

    task = ScarpingTask(
        enabled_scrapers=[chain_key],
        files_types=PRICE_FILE_TYPES,
        multiprocessing=1,
        output_configuration={"output_mode": "disk", "base_storage_path": dumps_folder},
        status_configuration={
            "database_type": "json",
            "base_path": os.path.join(dumps_folder, "status"),
        },
        timeout_in_seconds=timeout_seconds,
    )
    task.start(limit=limit)
    task.join()
    return os.path.join(dumps_folder, chain_folder(chain_key))
