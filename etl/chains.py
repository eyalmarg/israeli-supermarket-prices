"""
מיפוי בין שמות תיקיות ההורדה של il_supermarket_scarper (dumps/<תיקייה>)
לבין שם תצוגה בעברית לאתר.

הסקרייפר שומר כל רשת בתיקייה בשם CamelCase (למשל dumps/RamiLevy),
ולכן המפתחות כאן הם שמות התיקיות האלה. אם שם מסוים לא מדויק — פשוט
עדכנו כאן; זה משפיע רק על השם שמוצג באתר.
"""

CHAIN_DISPLAY_NAMES = {
    "Bareket": "ברקת",
    "YaynotBitanAndCarrefour": "יינות ביתן / קרפור",
    "CityMarketKiryatGat": "סיטי מרקט קרית גת",
    "CityMarketShops": "סיטי מרקט",
    "DorAlon": "דור אלון",
    "GoodPharm": "גוד פארם",
    "HaziHinam": "חצי חינם",
    "HetCohen": "ח. כהן",
    "HetCohenNewSource": "ח. כהן",
    "Keshet": "קשת טעמים",
    "KingStore": "קינג סטור",
    "Maayan2000": "מעיין 2000",
    "MahsaniAShuk": "מחסני השוק",
    "MahsaniAShukNewSource": "מחסני השוק",
    "NetivHased": "נתיב החסד",
    "MeshnatYosef1": "משנת יוסף",
    "MeshnatYosef2": "משנת יוסף",
    "Osherad": "אושר עד",
    "Polizer": "פוליצר",
    "RamiLevy": "רמי לוי",
    "SalachDabach": "סאלח דבאח",
    "ShefaBarcartAshem": "שפע ברכת השם",
    "Shufersal": "שופרסל",
    "ShukAhir": "שוק העיר",
    "StopMarket": "סטופ מרקט",
    "SuperPharm": "סופר פארם",
    "SuperYuda": "סופר יודה",
    "SuperSapir": "סופר ספיר",
    "FreshMarketAndSuperDosh": "פרש מרקט / סופר דוש",
    "TivTaam": "טיב טעם",
    "Victory": "ויקטורי",
    "VictoryNewSource": "ויקטורי",
    "Yellow": "ילו",
    "Yohananof": "יוחננוף",
    "ZolVeBegadol": "זול ובגדול",
    "Wolt": "וולט מרקט",
}

_BY_LOWER = {k.lower(): v for k, v in CHAIN_DISPLAY_NAMES.items()}


def display_name(folder_name: str) -> str:
    """מחזיר שם תצוגה בעברית לתיקיית רשת, או את שם התיקייה עצמו אם לא נמצא מיפוי."""
    if not folder_name:
        return "לא ידוע"
    key = folder_name.strip().replace("_", "").lower()
    return _BY_LOWER.get(key, folder_name)
