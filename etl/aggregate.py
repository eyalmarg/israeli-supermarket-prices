"""
סיכום המחירים של רשת אחת על פני כל הסניפים שלה.

מקבל תיקייה עם קובצי PriceFull של רשת (dumps/<רשת>/), לוקח לכל סניף
רק את הקובץ העדכני ביותר, ומחזיר לכל מוצר: המחיר הזול / החציוני /
היקר בין הסניפים, מספר הסניפים, והשם/היצרן/הגודל הנפוצים ביותר.
"""

import os
from array import array
from collections import Counter
from datetime import datetime
from statistics import median

from xml_reader import file_kind, file_timestamp, read_prices


def find_price_files(folder):
    """[(timestamp, path)] לכל קובצי PriceFull בתיקייה, מהחדש לישן."""
    found = []
    for root, _dirs, files in os.walk(folder):
        for name in files:
            if file_kind(name) != "prices":
                continue
            path = os.path.join(root, name)
            ts = file_timestamp(name) or datetime.fromtimestamp(os.path.getmtime(path))
            found.append((ts, path))
    found.sort(reverse=True)
    return found


class _Item:
    __slots__ = ("prices", "names", "manufacturers", "sizes", "weighted", "last_update")

    def __init__(self):
        self.prices = array("d")
        self.names = Counter()
        self.manufacturers = Counter()
        self.sizes = Counter()
        self.weighted = False
        self.last_update = None


def _top(counter):
    return counter.most_common(1)[0][0] if counter else None


def aggregate_chain(folder):
    """מחזיר (rows, store_count, data_date). rows ריק אם אין קובצי מחירים."""
    items = {}
    seen_stores = set()
    data_date = None

    for ts, path in find_price_files(folder):
        rows = read_prices(path)
        if not rows:
            continue
        stores = Counter(r["store_id"] for r in rows if r["store_id"])
        store = stores.most_common(1)[0][0] if stores else path
        if store in seen_stores:
            continue  # כבר נקרא קובץ חדש יותר לאותו סניף
        seen_stores.add(store)
        data_date = max(data_date, ts) if data_date else ts

        seen_codes = set()
        for r in rows:
            code = r["item_code"]
            if code in seen_codes:
                continue
            seen_codes.add(code)
            item = items.get(code)
            if item is None:
                item = items[code] = _Item()
            item.prices.append(r["item_price"])
            if r["item_name"]:
                item.names[r["item_name"]] += 1
            if r["manufacturer_name"]:
                item.manufacturers[r["manufacturer_name"]] += 1
            if r["quantity"] is not None or r["unit_qty"]:
                item.sizes[(r["quantity"], r["unit_qty"])] += 1
            if r["is_weighted"]:
                item.weighted = True
            if r["price_update_date"] and (
                item.last_update is None or r["price_update_date"] > item.last_update
            ):
                item.last_update = r["price_update_date"]

    result = []
    for code, item in items.items():
        quantity, unit_qty = _top(item.sizes) or (None, None)
        result.append(
            {
                "item_code": code,
                "item_name": _top(item.names),
                "manufacturer_name": _top(item.manufacturers),
                "quantity": quantity,
                "unit_qty": unit_qty,
                "is_weighted": item.weighted,
                "min_price": round(min(item.prices), 2),
                "median_price": round(median(item.prices), 2),
                "max_price": round(max(item.prices), 2),
                "store_count": len(item.prices),
                "last_update": item.last_update,
            }
        )
    return result, len(seen_stores), data_date
