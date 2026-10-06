"""
יוצר תיקיית dumps קטנה לבדיקות, בשלושה מבני XML שונים שבהם הרשתות
באמת מפרסמות (שופרסל: asx:abap באותיות גדולות; המבנה הנפוץ Root/Items;
ויקטורי: Prices/Products ו-Branches/Branch). המחירים כאן מומצאים
ומשמשים לבדיקות בלבד.

    python tests/sample_dumps.py <תיקיית-יעד>
"""

import gzip
import os
import sys

SHUFERSAL = "7290027600007"
RAMI_LEVY = "7290058140886"
VICTORY = "7290696200003"

MILK = "7290004131074"
BREAD = "7290000000510"
EGGS = "7290000000565"
TOMATO_INTERNAL = "4011"


def _write(path, content, encoding="utf-8", gz=False):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    data = content.encode(encoding)
    if gz:
        data = gzip.compress(data)
    with open(path, "wb") as f:
        f.write(data)


def shufersal(base):
    folder = os.path.join(base, "Shufersal")
    _write(
        os.path.join(folder, f"Stores{SHUFERSAL}-000-202610060200.xml"),
        f"""<?xml version="1.0" encoding="utf-8"?>
<asx:abap xmlns:asx="http://www.sap.com/abapxml" version="1.0"><asx:values>
<CHAINID>{SHUFERSAL}</CHAINID><LASTUPDATEDATE>2026-10-06</LASTUPDATEDATE>
<STORES>
<STORE><CHAINID>{SHUFERSAL}</CHAINID><CHAINNAME>שופרסל</CHAINNAME><SUBCHAINID>1</SUBCHAINID>
<SUBCHAINNAME>שופרסל שלי</SUBCHAINNAME><STOREID>1</STOREID><BIKORETNO>9</BIKORETNO><STORETYPE>1</STORETYPE>
<STORENAME>שלי ת"א- בן יהודה</STORENAME><ADDRESS>בן יהודה 79</ADDRESS><CITY>תל אביב</CITY><ZIPCODE>6343504</ZIPCODE></STORE>
<STORE><CHAINID>{SHUFERSAL}</CHAINID><CHAINNAME>שופרסל</CHAINNAME><SUBCHAINID>2</SUBCHAINID>
<SUBCHAINNAME>שופרסל דיל</SUBCHAINNAME><STOREID>2</STOREID><BIKORETNO>9</BIKORETNO><STORETYPE>1</STORETYPE>
<STORENAME>דיל חיפה</STORENAME><ADDRESS>חלוצי התעשיה 1</ADDRESS><CITY>חיפה</CITY><ZIPCODE></ZIPCODE></STORE>
</STORES></asx:values></asx:abap>""",
    )

    def price_file(store, ts, items):
        rows = "".join(
            f"""<Item><PriceUpdateDate>2026-10-05 08:00</PriceUpdateDate><ItemCode>{code}</ItemCode>
<ItemType>{itype}</ItemType><ItemName>{name}</ItemName><ManufacturerName>{mfr}</ManufacturerName>
<ManufactureCountry>IL</ManufactureCountry><ManufacturerItemDescription>{name}</ManufacturerItemDescription>
<UnitQty>{unit}</UnitQty><Quantity>{qty}</Quantity><bIsWeighted>{w}</bIsWeighted><UnitOfMeasure>{uom}</UnitOfMeasure>
<QtyInPackage>0</QtyInPackage><ItemPrice>{price}</ItemPrice><UnitOfMeasurePrice>{uprice}</UnitOfMeasurePrice>
<AllowDiscount>1</AllowDiscount><ItemStatus>1</ItemStatus></Item>"""
            for code, itype, name, mfr, unit, qty, w, uom, price, uprice in items
        )
        _write(
            os.path.join(folder, f"PriceFull{SHUFERSAL}-{store:03d}-{ts}.xml"),
            f"""<?xml version="1.0" encoding="utf-8"?>
<root><ChainId>{SHUFERSAL}</ChainId><SubChainId>001</SubChainId><StoreId>{store:03d}</StoreId>
<BikoretNo>9</BikoretNo><Items Count="{len(items)}">{rows}</Items></root>""",
        )

    milk = (MILK, 1, "חלב תנובה טרי 3% בקרטון", "תנובה", "ליטר", "1.00", 0, "ליטר", "7.10", "7.10")
    bread = (BREAD, 1, "לחם אחיד פרוס", "אנג'ל", "גרם", "750.00", 0, "100 גרם", "8.20", "1.09")
    tomato = (TOMATO_INTERNAL, 0, "עגבניות", "", "קילוגרם", "1.00", 1, "קילוגרם", "6.90", "6.90")
    # תמונת מצב ישנה (מחיר חלב אחר) — חייבת להידרס ע"י החדשה
    old_milk = milk[:8] + ("9.99", "9.99")
    price_file(1, "202610050300", [old_milk, bread])
    price_file(1, "202610060300", [milk, bread, tomato])
    price_file(2, "202610060300", [milk[:8] + ("6.80", "6.80"), bread[:8] + ("7.90", "1.05")])
    # קובץ מבצעים — אסור שייטען
    _write(
        os.path.join(folder, f"PromoFull{SHUFERSAL}-001-202610060300.xml"),
        f"""<root><ChainId>{SHUFERSAL}</ChainId><StoreId>001</StoreId><Promotions><Promotion>
<PromotionId>1</PromotionId><Items><Item><ItemCode>{MILK}</ItemCode><ItemPrice>1.00</ItemPrice></Item></Items>
</Promotion></Promotions></root>""",
    )
    # קובץ עדכון חלקי (Price, לא PriceFull) — מדולג
    _write(
        os.path.join(folder, f"Price{SHUFERSAL}-001-202610061000.xml"),
        f"""<root><ChainId>{SHUFERSAL}</ChainId><StoreId>001</StoreId><Items><Item>
<ItemCode>{MILK}</ItemCode><ItemType>1</ItemType><ItemPrice>0.50</ItemPrice></Item></Items></root>""",
    )


def rami_levy(base):
    folder = os.path.join(base, "RamiLevy")
    _write(
        os.path.join(folder, f"Stores{RAMI_LEVY}-202610060200.xml"),
        f"""<?xml version="1.0" encoding="utf-8"?>
<Root><XmlDocVersion>1</XmlDocVersion><ChainId>{RAMI_LEVY}</ChainId><ChainName>רמי לוי שיווק השיקמה</ChainName>
<LastUpdateDate>2026-10-06</LastUpdateDate><LastUpdateTime>02:00:00</LastUpdateTime>
<SubChains><SubChain><SubChainId>001</SubChainId><SubChainName>רמי לוי</SubChainName>
<Stores>
<Store><StoreId>039</StoreId><BikoretNo>5</BikoretNo><StoreType>1</StoreType><StoreName>תלפיות</StoreName>
<Address>יד חרוצים 10</Address><City>ירושלים</City><ZipCode>0</ZipCode></Store>
<Store><StoreId>021</StoreId><BikoretNo>5</BikoretNo><StoreType>1</StoreType><StoreName>חיפה - צ'ק פוסט</StoreName>
<Address>דרך העצמאות</Address><City>חיפה</City><ZipCode>0</ZipCode></Store>
</Stores></SubChain></SubChains></Root>""",
    )
    for store, milk_price in ((39, "6.50"), (21, "6.70")):
        _write(
            os.path.join(folder, f"PriceFull{RAMI_LEVY}-{store:03d}-202610060300.xml"),
            f"""<?xml version="1.0" encoding="utf-8"?>
<Root><XmlDocVersion>1</XmlDocVersion><DllVerNo>1</DllVerNo><ChainId>{RAMI_LEVY}</ChainId>
<SubChainId>001</SubChainId><StoreId>{store:03d}</StoreId><BikoretNo>5</BikoretNo>
<Items Count="3">
<Item><PriceUpdateDate>2026-10-04T07:30:00.000</PriceUpdateDate><ItemCode>0{MILK}</ItemCode><ItemType>1</ItemType>
<ItemNm>חלב 3% תנובה קרטון 1 ל'</ItemNm><ManufacturerName>תנובה</ManufacturerName><ManufactureCountry>ישראל</ManufactureCountry>
<UnitQty>ליטר</UnitQty><Quantity>1</Quantity><UnitOfMeasure>ליטר</UnitOfMeasure><bIsWeighted>0</bIsWeighted>
<ItemPrice>{milk_price}</ItemPrice><UnitOfMeasurePrice>{milk_price}</UnitOfMeasurePrice><AllowDiscount>1</AllowDiscount><ItemStatus>1</ItemStatus></Item>
<Item><PriceUpdateDate>2026-10-04T07:30:00.000</PriceUpdateDate><ItemCode>{EGGS}</ItemCode><ItemType>1</ItemType>
<ItemNm>ביצים L 12 יח'</ItemNm><ManufacturerName>מגדלי ביצים</ManufacturerName>
<UnitQty>יחידה</UnitQty><Quantity>12</Quantity><UnitOfMeasure>יחידה</UnitOfMeasure><bIsWeighted>0</bIsWeighted>
<ItemPrice>12.90</ItemPrice><UnitOfMeasurePrice>1.08</UnitOfMeasurePrice></Item>
<Item><ItemCode>{BREAD}</ItemCode><ItemType>1</ItemType><ItemNm>לחם אחיד פרוס</ItemNm>
<ItemPrice>0</ItemPrice></Item>
</Items></Root>""",
            gz=(store == 21),
        )


def victory(base):
    folder = os.path.join(base, "VictoryNewSource")
    _write(
        os.path.join(folder, f"Stores{VICTORY}-000-202610060100.xml"),
        f"""<?xml version="1.0" encoding="utf-16"?>
<Store Date="06/10/2026" Time="01:00:00"><Branches>
<Branch><ChainID>{VICTORY}</ChainID><SubChainID>1</SubChainID><StoreID>7</StoreID><BikoretNo>3</BikoretNo>
<StoreType>1</StoreType><ChainName>ויקטורי</ChainName><SubChainName>ויקטורי</SubChainName>
<StoreName>ויקטורי ירושלים</StoreName><Address>בית הדפוס 12</Address><City>ירושלים</City><ZIPCode>0</ZIPCode></Branch>
</Branches></Store>""",
        encoding="utf-16",
    )
    _write(
        os.path.join(folder, f"PriceFull{VICTORY}-007-202610060200.xml"),
        f"""<?xml version="1.0" encoding="utf-16"?>
<Prices><ChainID>{VICTORY}</ChainID><SubChainID>001</SubChainID><StoreID>007</StoreID><BikoretNo>3</BikoretNo>
<Products>
<Product><PriceUpdateDate>2026/10/03 10:15:00</PriceUpdateDate><ItemCode>{MILK}</ItemCode><ItemType>1</ItemType>
<ItemName>חלב טרי 3% תנובה</ItemName><ManufactureName>תנובה</ManufactureName><ManufactureCountry>IL</ManufactureCountry>
<ManufactureItemDescription>חלב</ManufactureItemDescription><UnitQty>ליטר</UnitQty><Quantity>1.00</Quantity>
<UnitOfMeasure>ליטר</UnitOfMeasure><BisWeighted>0</BisWeighted><QtyInPackage>0</QtyInPackage>
<ItemPrice>6.90</ItemPrice><UnitOfMeasurePrice>6.90</UnitOfMeasurePrice><AllowDiscount>1</AllowDiscount><itemStatus>1</itemStatus></Product>
<Product><PriceUpdateDate>2026/10/03 10:15:00</PriceUpdateDate><ItemCode>{EGGS}</ItemCode><ItemType>1</ItemType>
<ItemName>ביצים גדולות 12</ItemName><ManufactureName>מגדלי ביצים</ManufactureName><UnitQty>יחידה</UnitQty>
<Quantity>12</Quantity><BisWeighted>0</BisWeighted><ItemPrice>13.50</ItemPrice><UnitOfMeasurePrice>1.13</UnitOfMeasurePrice></Product>
<Product><ItemCode>{BREAD}</ItemCode><ItemType>1</ItemType><ItemName>לחם אחיד</ItemName><ManufactureName>אנג'ל</ManufactureName>
<ItemPrice>8.00</ItemPrice></Product>
</Products></Prices>""",
        encoding="utf-16",
    )


def build(base):
    shufersal(base)
    rami_levy(base)
    victory(base)


if __name__ == "__main__":
    build(sys.argv[1] if len(sys.argv) > 1 else "dumps")
