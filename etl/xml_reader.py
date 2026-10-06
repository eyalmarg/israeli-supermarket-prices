"""
קורא XML גנרי לקובצי Stores ו-PriceFull של חוק שקיפות המחירים.

כל רשת מפרסמת "בערך" את אותו מבנה אחיד, אבל עם הבדלים קטנים:
אותיות גדולות/קטנות (ItemCode / ITEMCODE), שמות עטיפה שונים
(Items/Item, Products/Product, STORES/STORE), namespaces (asx:abap)
ושמות שדות חלופיים (ItemName / ItemNm). במקום לכתוב מפרסר לכל רשת,
הקורא מזהה "שורת מוצר" כאלמנט שיש לו ילדים ItemCode ו-ItemPrice,
ו"שורת סניף" כאלמנט עם StoreId ושם/כתובת/עיר — בלי תלות בשמות העטיפה.

הקבצים מעובדים בזרימה (iterparse) כך שגם קבצים של מאות MB לא נטענים
לזיכרון בבת אחת.
"""

import gzip
import io
import re
import zipfile
from datetime import datetime

from lxml import etree

# שדות "הקשר" שמופיעים פעם אחת בראש הקובץ (או בראש תת-רשת) וחלים על
# כל השורות שאחריהם.
CONTEXT_FIELDS = {"chainid", "chainname", "subchainid", "subchainname", "storeid"}

ITEM_ALIASES = {
    "item_code": ["itemcode"],
    "item_type": ["itemtype"],
    "item_name": ["itemname", "itemnm"],
    "manufacturer_name": ["manufacturername", "manufacturename", "manufacturname"],
    "quantity": ["quantity"],
    "unit_qty": ["unitqty"],
    "unit_of_measure": ["unitofmeasure"],
    "is_weighted": ["bisweighted", "isweighted", "blsweighted"],
    "item_price": ["itemprice"],
    "unit_of_measure_price": ["unitofmeasureprice"],
    "price_update_date": ["priceupdatedate", "priceupdatetime"],
    "store_id": ["storeid"],
}

STORE_ALIASES = {
    "store_id": ["storeid"],
    "store_name": ["storename"],
    "address": ["address"],
    "city": ["city"],
    "sub_chain_id": ["subchainid"],
    "sub_chain_name": ["subchainname"],
    "chain_id": ["chainid"],
}

_STORE_MARKERS = {"storename", "address", "city"}


def _local(tag) -> str:
    """'{namespace}ItemCode' -> 'itemcode'"""
    if not isinstance(tag, str):
        return ""
    return tag.rsplit("}", 1)[-1].lower()


def _text(elem):
    t = elem.text
    if t is None:
        return None
    t = t.strip()
    return t or None


def _open(path):
    """פותח קובץ XML, גם אם הוא בעצם gzip/zip (יש רשתות שמגישות כך)."""
    with open(path, "rb") as f:
        magic = f.read(4)
    if magic[:2] == b"\x1f\x8b":
        return gzip.open(path, "rb")
    if magic[:2] == b"PK":
        with zipfile.ZipFile(path) as zf:
            name = zf.namelist()[0]
            return io.BytesIO(zf.read(name))
    return open(path, "rb")


def _iter_rows(path, is_row):
    """עובר על הקובץ ומחזיר (row_dict, context_dict) לכל אלמנט ש-is_row מאשר."""
    context = {}
    with _open(path) as fh:
        parser = etree.iterparse(
            fh,
            events=("end",),
            recover=True,
            huge_tree=True,
            resolve_entities=False,
            no_network=True,
            remove_comments=True,
        )
        for _event, elem in parser:
            tag = _local(elem.tag)
            if len(elem) == 0:
                if tag in CONTEXT_FIELDS:
                    value = _text(elem)
                    if value is not None:
                        context[tag] = value
                continue

            children = {}
            for child in elem:
                ctag = _local(child.tag)
                if ctag and len(child) == 0:
                    children[ctag] = _text(child)
            if not is_row(children):
                continue

            yield children, context
            # שחרור זיכרון: מוחקים את השורה ואת האחים שכבר עובדו
            elem.clear()
            parent = elem.getparent()
            if parent is not None:
                while elem.getprevious() is not None:
                    del parent[0]


def _pick(children, aliases):
    for name in aliases:
        if children.get(name) is not None:
            return children[name]
    return None


def _num(value):
    if value is None:
        return None
    try:
        return float(value.replace(",", ""))
    except ValueError:
        return None


def _bool(value):
    if value is None:
        return None
    return value.strip().lower() in ("1", "true", "כן", "y", "yes")


_DATE_FORMATS = (
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d %H:%M",
    "%Y-%m-%dT%H:%M:%S",
    "%Y/%m/%d %H:%M:%S",
    "%Y/%m/%d %H:%M",
    "%Y-%m-%d",
    "%Y/%m/%d",
    "%d/%m/%Y %H:%M:%S",
    "%d/%m/%Y %H:%M",
    "%d/%m/%Y",
)


def _date(value):
    if not value:
        return None
    value = value.strip()
    value = re.sub(r"\.\d+$", "", value)  # מילישניות
    value = re.sub(r"(Z|[+-]\d\d:?\d\d)$", "", value)  # אזור זמן
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    return None


def normalize_id(value):
    """'001' -> '1' כדי שמספר סניף/ברקוד יתאים בין קבצים שונים."""
    if value is None:
        return None
    value = value.strip()
    if value.isdigit():
        return value.lstrip("0") or "0"
    return value or None


def file_kind(file_name: str):
    """'prices' / 'stores' / None לפי שם הקובץ. קובצי מבצעים ועדכונים חלקיים מדולגים."""
    lower = file_name.lower()
    if "promo" in lower:
        return None
    if "pricefull" in lower:
        return "prices"
    if "store" in lower:
        return "stores"
    return None


def file_timestamp(file_name: str):
    """מחלץ את חותמת הזמן מהשם, למשל PriceFull7290027600007-001-202610060300.xml"""
    matches = re.findall(r"(20\d{2})(\d{2})(\d{2})(\d{2})(\d{2})", file_name)
    for y, mo, d, h, mi in reversed(matches):
        try:
            return datetime(int(y), int(mo), int(d), int(h), int(mi))
        except ValueError:
            continue
    return None


def read_prices(path):
    """מחזיר רשימת מחירים רגילים מקובץ PriceFull.

    מדלג על:
      * קודים פנימיים של הרשת (ItemType=0) — הם לא ברקוד ולא ניתנים להשוואה בין רשתות
      * שורות בלי מחיר או עם מחיר 0
    """

    def is_item(children):
        return "itemcode" in children and "itemprice" in children

    rows = []
    for children, context in _iter_rows(path, is_item):
        item_type = _pick(children, ITEM_ALIASES["item_type"])
        code = normalize_id(_pick(children, ITEM_ALIASES["item_code"]))
        if not code:
            continue
        if item_type is not None and item_type.strip() == "0":
            continue
        if item_type is None and code.isdigit() and len(code) < 7:
            continue  # בלי ItemType: קוד קצר הוא כמעט תמיד קוד פנימי
        price = _num(_pick(children, ITEM_ALIASES["item_price"]))
        if price is None or price <= 0:
            continue
        rows.append(
            {
                "chain_id": normalize_id(context.get("chainid")),
                "store_id": normalize_id(
                    _pick(children, ITEM_ALIASES["store_id"]) or context.get("storeid")
                ),
                "item_code": code,
                "item_name": _pick(children, ITEM_ALIASES["item_name"]),
                "manufacturer_name": _pick(children, ITEM_ALIASES["manufacturer_name"]),
                "quantity": _num(_pick(children, ITEM_ALIASES["quantity"])),
                "unit_qty": _pick(children, ITEM_ALIASES["unit_qty"]),
                "unit_of_measure": _pick(children, ITEM_ALIASES["unit_of_measure"]),
                "is_weighted": _bool(_pick(children, ITEM_ALIASES["is_weighted"])),
                "item_price": price,
                "unit_of_measure_price": _num(
                    _pick(children, ITEM_ALIASES["unit_of_measure_price"])
                ),
                "price_update_date": _date(_pick(children, ITEM_ALIASES["price_update_date"])),
            }
        )
    return rows


def read_stores(path):
    """מחזיר רשימת סניפים מקובץ Stores."""

    def is_store(children):
        return "storeid" in children and bool(_STORE_MARKERS & children.keys())

    rows = []
    for children, context in _iter_rows(path, is_store):
        store_id = normalize_id(_pick(children, STORE_ALIASES["store_id"]))
        if not store_id:
            continue
        rows.append(
            {
                "chain_id": normalize_id(
                    _pick(children, STORE_ALIASES["chain_id"]) or context.get("chainid")
                ),
                "store_id": store_id,
                "sub_chain_id": _pick(children, STORE_ALIASES["sub_chain_id"])
                or context.get("subchainid"),
                "sub_chain_name": _pick(children, STORE_ALIASES["sub_chain_name"])
                or context.get("subchainname"),
                "store_name": _pick(children, STORE_ALIASES["store_name"]),
                "address": _pick(children, STORE_ALIASES["address"]),
                "city": _pick(children, STORE_ALIASES["city"]),
            }
        )
    return rows
