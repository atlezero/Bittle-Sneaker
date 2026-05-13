import argparse
import sys
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv

try:
    from features.sheets_client import get_sheet
except ModuleNotFoundError as exc:
    if exc.name != "features":
        raise
    from sheets_client import get_sheet


THAI_TZ = timezone(timedelta(hours=7))


def parse_sale_item(item: str) -> tuple[str, int, float]:
    parts = item.split(":")
    if len(parts) != 3:
        raise ValueError(
            "รูปแบบต้องเป็น เมนู:จำนวน:ราคา เช่น กาแฟ:2:45"
        )

    menu = parts[0].strip()
    if not menu:
        raise ValueError("ชื่อเมนูไม่สามารถเว้นว่างได้")

    try:
        quantity = int(parts[1])
    except ValueError as exc:
        raise ValueError("จำนวนต้องเป็นจำนวนเต็ม") from exc

    try:
        price = float(parts[2])
    except ValueError as exc:
        raise ValueError("ราคาต้องเป็นตัวเลข") from exc

    return menu, quantity, price


def main() -> int:
    load_dotenv()

    parser = argparse.ArgumentParser(
        description="เพิ่มยอดขายไปยัง Google Sheet โดยรับรูปแบบ เมนู:จำนวน:ราคา"
    )
    parser.add_argument(
        "sale",
        help="ยอดขายในรูปแบบ เมนู:จำนวน:ราคา เช่น กาแฟ:2:45",
    )
    args = parser.parse_args()

    try:
        menu, quantity, price = parse_sale_item(args.sale)
    except ValueError as exc:
        print(f"ข้อผิดพลาด: {exc}", file=sys.stderr)
        return 1

    total = quantity * price
    today = datetime.now(THAI_TZ).date().isoformat()
    row = [today, menu, quantity, price, total]

    try:
        sheet = get_sheet()
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

    sheet.append_row(row)

    print("เพิ่มยอดขายเรียบร้อย:", row)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
