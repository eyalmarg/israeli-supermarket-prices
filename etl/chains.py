"""
מיפוי בין קודי הרשתות הפנימיים של il_supermarket_scarper
(כפי שמופיעים ב-ENABLED_SCRAPERS / בשם תיקיית ה-dump) לבין
שם תצוגה בעברית לאתר.

הערה: חלק מהשמות הם ניחוש סביר על סמך שם הקוד (למשל MESHMAT_YOSEF,
YELLOW, HET_COHEN) - אם משהו לא מדויק, פשוט עדכנו כאן את המילון.
זה לא משפיע על תקינות הנתונים, רק על השם שמוצג באתר.
"""

CHAIN_DISPLAY_NAMES = {
    "BAREKET": "ברקת",
    "YAYNO_BITAN_AND_CARREFOUR": "יינות ביתן / קרפור",
    "COFIX": "קופיקס",
    "CITY_MARKET_KIRYATGAT": "סיטי מרקט קרית גת",
    "CITY_MARKET_SHOPS": "סיטי מרקט",
    "DOR_ALON": "דור אלון",
    "GOOD_PHARM": "גוד פארם",
    "HAZI_HINAM": "חצי חינם",
    "HET_COHEN": "ח. כהן",
    "KESHET": "קשת טעמים",
    "KING_STORE": "קינג סטור",
    "MAAYAN_2000": "מעיין 2000",
    "MAHSANI_ASHUK": "מחסני השוק",
    "MAHSANI_ASHUK_NEW_SOURCE": "מחסני השוק",
    "NETIV_HASED": "נתיב החסד",
    "MESHMAT_YOSEF_1": "משק את יוסף",
    "MESHMAT_YOSEF_2": "משק את יוסף",
    "OSHER_AD": "אושר עד",
    "POLIZER": "פוליצר",
    "RAMI_LEVY": "רמי לוי",
    "SALACH_DABACH": "סאלח דבאח",
    "SHEFA_BARCART_ASHEM": "שפע ברכת השם",
    "SHUFERSAL": "שופרסל",
    "SHUK_AHIR": "שוק העיר",
    "STOP_MARKET": "סטופ מרקט",
    "SUPER_PHARM": "סופר פארם",
    "SUPER_YUDA": "סופר יודה",
    "SUPER_SAPIR": "סופר ספיר",
    "FRESH_MARKET_AND_SUPER_DOSH": "פרש מרקט / סופר דוש",
    "QUIK": "קוויק",
    "TIV_TAAM": "טיב טעם",
    "VICTORY": "ויקטורי",
    "VICTORY_NEW_SOURCE": "ויקטורי",
    "YELLOW": "ילו",
    "YOHANANOF": "יוחננוף",
    "ZOL_VEBEGADOL": "זול ובגדול",
    "WOLT": "וולט מרקט",
}


def display_name(chain_code: str) -> str:
    """מחזיר שם תצוגה בעברית לקוד רשת, או את הקוד עצמו אם לא נמצא מיפוי."""
    if not chain_code:
        return "לא ידוע"
    key = chain_code.strip().upper()
    return CHAIN_DISPLAY_NAMES.get(key, chain_code)
