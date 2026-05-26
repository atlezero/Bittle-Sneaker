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


def parse_sale_item(item: str) -> tuple[str, float, str]:
    parts = item.split(":")
    if len(parts) != 3:
        raise ValueError(
            "รูปแบบต้องเป็น รหัสสินค้า:ราคาที่ขาย:ช่องทางขาย (เช่น NK-001:3500:IG)"
        )

    sku = parts[0].strip()
    price_str = parts[1].strip()
    sales_channel = parts[2].strip()

    if not sku:
        raise ValueError("รหัสสินค้าไม่สามารถเว้นว่างได้")

    try:
        price = float(price_str)
    except ValueError as exc:
        raise ValueError("ราคาต้องเป็นตัวเลข") from exc

    if not sales_channel:
        raise ValueError("ช่องทางขายไม่สามารถเว้นว่างได้")

    return sku, price, sales_channel


def main() -> int:
    load_dotenv()

    parser = argparse.ArgumentParser(
        description="เพิ่มยอดขายไปยัง Google Sheet โดยรับรูปแบบ รหัสสินค้า:ราคาที่ขาย:ช่องทางขาย"
    )
    parser.add_argument(
        "sale",
        help="ยอดขายในรูปแบบ เช่น NK-001:3500:IG",
    )
    args = parser.parse_args()

    try:
        sku, price, sales_channel = parse_sale_item(args.sale)
    except ValueError as exc:
        print(f"ข้อผิดพลาด: {exc}", file=sys.stderr)
        return 1

    try:
        result = log_sale(
            sku=sku,
            price=price,
            sales_channel=sales_channel,
            quantity=1
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

    print("เพิ่มยอดขายเรียบร้อย:", [
        result["timestamp"],
        sku,
        result.get("brand", "ไม่ระบุ"),
        result.get("model", "ไม่ระบุ"),
        result.get("size", "ทั่วไป"),
        1,
        price,
        result["total"]
    ])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
