import argparse
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from dotenv import load_dotenv

# ── Path setup ────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))
load_dotenv(PROJECT_ROOT / ".env")

from features.sheets_client import get_sheet
from features.agent_tools import log_sale


THAI_TZ = timezone(timedelta(hours=7))


def parse_sale_item(item: str) -> tuple[str, int, float]:
    parts = item.split(":")
    if len(parts) != 3 and len(parts) != 6:
        raise ValueError(
            "รูปแบบต้องเป็น เมนู:จำนวน:ราคา หรือ รหัสสินค้า:แบรนด์:รุ่น:ไซส์:จำนวน:ราคา"
        )

    if len(parts) == 6:
        sku = parts[0].strip()
        brand = parts[1].strip()
        model = parts[2].strip()
        size = parts[3].strip()
        
        menu_parts = []
        if sku and sku != "ไม่ระบุ":
            menu_parts.append(sku)
        if brand and brand != "ไม่ระบุ":
            menu_parts.append(brand)
        if model and model != "ไม่ระบุ":
            menu_parts.append(model)
        
        display_name = " ".join(menu_parts) if menu_parts else "ไม่ระบุ"
        menu = f"{display_name}_{size}" if size and size != "ทั่วไป" else display_name
        
        qty_str = parts[4]
        price_str = parts[5]
    else:
        menu = parts[0].strip()
        qty_str = parts[1]
        price_str = parts[2]

    if not menu:
        raise ValueError("ชื่อเมนูไม่สามารถเว้นว่างได้")

    try:
        quantity = int(qty_str)
    except ValueError as exc:
        raise ValueError("จำนวนต้องเป็นจำนวนเต็ม") from exc

    try:
        price = float(price_str)
    except ValueError as exc:
        raise ValueError("ราคาต้องเป็นตัวเลข") from exc

    return menu, quantity, price


def main() -> int:
    load_dotenv()

    parser = argparse.ArgumentParser(
        description="เพิ่มยอดขายไปยัง Google Sheet โดยรับรูปแบบ รหัสสินค้า:แบรนด์:รุ่น:ไซส์:จำนวน:ราคา หรือ รองเท้า:จำนวน:ราคา"
    )
    parser.add_argument(
        "sale",
        help="ยอดขายในรูปแบบ เช่น NK-001:Nike:Dunk Low:42:1:3500 หรือ Nike_42:1:3500",
    )
    args = parser.parse_args()

    try:
        menu, quantity, price = parse_sale_item(args.sale)
    except ValueError as exc:
        print(f"ข้อผิดพลาด: {exc}", file=sys.stderr)
        return 1

    total = quantity * price
    now_iso = datetime.now(THAI_TZ).isoformat()

    # แยกรายละเอียดออกมาจากเมนู
    clean_menu = menu.strip()
    size = "ทั่วไป"
    for sep in ["_", " "]:
        if sep in clean_menu:
            parts = clean_menu.rsplit(sep, 1)
            last_part = parts[1].strip()
            if last_part.isalnum() or last_part.replace(".", "", 1).isdigit():
                size = last_part
                clean_menu = parts[0].strip()
                break

    sku = "ไม่ระบุ"
    brand = "ไม่ระบุ"
    model = "ไม่ระบุ"
    words = clean_menu.split()
    if words:
        first_word = words[0]
        if "-" in first_word or (len(first_word) >= 4 and any(c.isdigit() for c in first_word) and any(c.isalpha() for c in first_word)):
            sku = first_word
            words = words[1:]
        
        if words:
            brand = words[0]
            if len(words) > 1:
                model = " ".join(words[1:])
            else:
                model = "ทั่วไป"
        else:
            brand = "ทั่วไป"
            model = "ทั่วไป"

    try:
        result = log_sale(
            sku=sku,
            brand=brand,
            model=model,
            size=size,
            quantity=quantity,
            price=price
        )
    except FileNotFoundError as exc:
        print(
            "ข้อผิดพลาด: ไม่พบไฟล์ service account ที่ระบุใน GOOGLE_SERVICE_ACCOUNT_FILE",
            file=sys.stderr,
        )
        print(f"รายละเอียด: {exc}", file=sys.stderr)
        print(
            "ตรวจสอบว่าไฟล์ JSON ถูกวางไว้ในตำแหน่งที่ถูกต้องหรือแก้ไขค่า GOOGLE_SERVICE_ACCOUNT_FILE ใน .env",
            file=sys.stderr,
        )
        return 1
    except RuntimeError as exc:
        print(f"ข้อผิดพลาด: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"ข้อผิดพลาด: {exc}", file=sys.stderr)
        return 1

    print("เพิ่มยอดขายเรียบร้อย:", [result["timestamp"], sku, brand, model, size, quantity, price, result["total"]])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
