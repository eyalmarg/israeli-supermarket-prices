"""בדיקות לקורא ה-XML על קבצים בשלושת המבנים של sample_dumps.py.

    pip install pytest && python -m pytest tests
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "etl"))
sys.path.insert(0, HERE)

import sample_dumps  # noqa: E402
from aggregate import aggregate_chain, find_price_files  # noqa: E402
from xml_reader import file_kind, read_prices, read_stores  # noqa: E402


def _build(tmp_path):
    sample_dumps.build(str(tmp_path))
    return tmp_path


def test_file_kind_skips_promotions_and_partial_updates():
    assert file_kind("PriceFull7290027600007-001-202610060300.xml") == "prices"
    assert file_kind("Stores7290027600007-000-202610060200.xml") == "stores"
    assert file_kind("PromoFull7290027600007-001-202610060300.xml") is None
    assert file_kind("Promo7290027600007-001-202610060300.xml") is None
    assert file_kind("Price7290027600007-001-202610061000.xml") is None


def test_find_price_files_only_pricefull(tmp_path):
    base = _build(tmp_path)
    names = [os.path.basename(p) for _ts, p in find_price_files(str(base / "Shufersal"))]
    assert len(names) == 3
    assert all(n.startswith("PriceFull") for n in names)


def test_aggregate_chain_uses_newest_file_per_store(tmp_path):
    base = _build(tmp_path)
    rows, store_count, data_date = aggregate_chain(str(base / "Shufersal"))
    by_code = {r["item_code"]: r for r in rows}
    assert store_count == 2
    assert data_date.day == 6
    milk = by_code[sample_dumps.MILK]
    # סניף 1: 7.10 (הקובץ הישן עם 9.99 מדולג), סניף 2: 6.80
    assert (milk["min_price"], milk["median_price"], milk["max_price"]) == (6.80, 6.95, 7.10)
    assert milk["store_count"] == 2
    assert sample_dumps.TOMATO_INTERNAL not in by_code


def test_read_prices_shufersal(tmp_path):
    base = _build(tmp_path)
    rows = read_prices(base / "Shufersal" / "PriceFull7290027600007-001-202610060300.xml")
    by_code = {r["item_code"]: r for r in rows}
    # עגבניות עם ItemType=0 (קוד פנימי) לא נכללות
    assert set(by_code) == {sample_dumps.MILK, sample_dumps.BREAD}
    milk = by_code[sample_dumps.MILK]
    assert milk["item_price"] == 7.10
    assert milk["store_id"] == "1"
    assert milk["chain_id"] == sample_dumps.SHUFERSAL
    assert milk["is_weighted"] is False


def test_read_prices_gzip_leading_zeros_and_itemnm(tmp_path):
    base = _build(tmp_path)
    rows = read_prices(base / "RamiLevy" / "PriceFull7290058140886-021-202610060300.xml")
    by_code = {r["item_code"]: r for r in rows}
    # ברקוד עם 0 מוביל מנורמל; מחיר 0 מדולג
    assert set(by_code) == {sample_dumps.MILK, sample_dumps.EGGS}
    assert by_code[sample_dumps.MILK]["item_name"].startswith("חלב")
    assert by_code[sample_dumps.MILK]["price_update_date"].hour == 7


def test_read_prices_victory_utf16(tmp_path):
    base = _build(tmp_path)
    rows = read_prices(base / "VictoryNewSource" / "PriceFull7290696200003-007-202610060200.xml")
    by_code = {r["item_code"]: r for r in rows}
    assert by_code[sample_dumps.EGGS]["item_price"] == 13.50
    assert by_code[sample_dumps.EGGS]["manufacturer_name"] == "מגדלי ביצים"
    assert by_code[sample_dumps.EGGS]["store_id"] == "7"


def test_read_stores_all_layouts(tmp_path):
    base = _build(tmp_path)
    shufersal = read_stores(base / "Shufersal" / "Stores7290027600007-000-202610060200.xml")
    assert {(s["store_id"], s["city"], s["sub_chain_name"]) for s in shufersal} == {
        ("1", "תל אביב", "שופרסל שלי"),
        ("2", "חיפה", "שופרסל דיל"),
    }
    rami = read_stores(base / "RamiLevy" / "Stores7290058140886-202610060200.xml")
    assert {s["store_id"] for s in rami} == {"39", "21"}
    assert all(s["chain_id"] == sample_dumps.RAMI_LEVY for s in rami)
    assert all(s["sub_chain_name"] == "רמי לוי" for s in rami)
    victory = read_stores(base / "VictoryNewSource" / "Stores7290696200003-000-202610060100.xml")
    assert victory[0]["city"] == "ירושלים"
