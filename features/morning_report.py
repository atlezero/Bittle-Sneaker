import os
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests
from dotenv import load_dotenv

# ── Path setup ────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))
load_dotenv(PROJECT_ROOT / ".env")

from features.sheets_client import get_sheet


DATE_FORMATS = ["%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d"]
THAI_TZ = timezone(timedelta(hours=7))


def parse_date(value: str) -> datetime.date:
    value = value.strip()
    if not value:
        raise ValueError("ค่าวันที่ว่างเปล่า")

    # ลองแปลงแบบ ISO 8601 ก่อน (รองรับ 2026-05-15T00:12:23.544407+07:00)
    try:
        return datetime.fromisoformat(value).date()
    except ValueError:
        pass

    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue

    raise ValueError(
        f"ไม่สามารถแปลงวันที่ได้: '{value}'. รองรับรูปแบบ: ISO8601, YYYY-MM-DD, DD/MM/YYYY, DD-MM-YYYY"
    )


def find_column(headers: list[str], names: list[str]) -> int | None:
    normalized = [header.strip().lower() for header in headers]
    for index, value in enumerate(normalized):
        if any(name in value for name in names):
            return index
    return None


def build_summary(rows: list[list[str]]) -> str:
    if not rows:
        return "ยังไม่มีข้อมูลใน Google Sheet ค่ะ 😅"

    headers = rows[0]
    data_rows = rows[1:]

    date_col = find_column(headers, ["date", "วันที่", "day"])
    menu_col = find_column(headers, ["menu", "เมนู", "item"])
    quantity_col = find_column(headers, ["quantity", "จำนวน", "qty"])
    total_col = find_column(headers, ["total", "ยอดรวม", "amount"])

    if date_col is None or menu_col is None or (quantity_col is None and total_col is None):
        return (
            "ไม่พบคอลัมน์ที่ต้องการใน Google Sheet ค่ะ 🫣\n"
            "กรุณาตรวจสอบว่ามีคอลัมน์ วันที่, เมนู, จำนวน หรือ ยอดรวม อยู่ในสเปรดชีต"
        )

    yesterday = datetime.now(THAI_TZ).date() - timedelta(days=1)
    filtered = []
    for row in data_rows:
        if len(row) <= date_col:
            continue

        try:
            row_date = parse_date(row[date_col])
        except ValueError:
            continue

        if row_date != yesterday:
            continue

        menu = row[menu_col].strip() if len(row) > menu_col else ""
        if not menu:
            continue

        quantity = 0
        if quantity_col is not None and len(row) > quantity_col:
            try:
                quantity = int(float(row[quantity_col]))
            except ValueError:
                quantity = 0

        total = 0.0
        if total_col is not None and len(row) > total_col:
            try:
                total = float(row[total_col])
            except ValueError:
                total = 0.0
        elif quantity_col is not None and len(row) > quantity_col:
            price = 0.0
            price_col = find_column(headers, ["price", "ราคา"])
            if price_col is not None and len(row) > price_col:
                try:
                    price = float(row[price_col])
                except ValueError:
                    price = 0.0
            total = quantity * price

        filtered.append((menu, quantity, total))

    if not filtered:
        return f"เมื่อวาน ({yesterday}) ยังไม่มียอดขายเลยค่ะ 🥲"

    total_sales = sum(item[2] for item in filtered)
    menu_counter = Counter()
    quantity_counter = Counter()
    for menu, quantity, total in filtered:
        menu_counter[menu] += total
        quantity_counter[menu] += quantity

    best_menu = quantity_counter.most_common(1)[0]
    best_menu_name, best_menu_quantity = best_menu

    best_revenue_menu = menu_counter.most_common(1)[0]
    best_revenue_name, best_revenue_amount = best_revenue_menu

    lines = [
        "สรุปยอดขายเมื่อวานน้า~ 🧸",
        f"วันที่: {yesterday}",
        "---",
    ]

    # แสดงรายละเอียดแยกตามเมนู
    for menu in sorted(quantity_counter.keys()):
        qty = quantity_counter[menu]
        rev = menu_counter[menu]
        lines.append(f"• {menu}: {qty} แก้ว ({rev:.2f} บาท)")

    lines.append("---")
    lines.append(f"💰 ยอดรวมทั้งหมด: {total_sales:.2f} บาท")
    lines.append(f"🏆 ขายดีที่สุด: {best_menu_name} ({best_menu_quantity} ชิ้น)")

    if len(quantity_counter) > 1:
        min_qty = min(quantity_counter.values())
        least_menus = sorted([menu for menu, qty in quantity_counter.items() if qty == min_qty])
        least_menu_str = ", ".join(least_menus)
        lines.append(f"📉 ขายได้น้อยที่สุด: {least_menu_str} ({min_qty} ชิ้น)")

    if best_revenue_name != best_menu_name:
        lines.append(f"💎 ทำเงินมากสุด: {best_revenue_name} ({best_revenue_amount:.2f} บาท)")


    lines.append("ขอบคุณที่ดูแลร้านนะคะ 💕")
    return "\n".join(lines)


def send_telegram_message(message: str) -> None:
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")

    if not token or not chat_id:
        raise RuntimeError("ต้องตั้งค่า TELEGRAM_BOT_TOKEN และ TELEGRAM_CHAT_ID ใน .env")

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": message}
    response = requests.post(url, json=payload, timeout=15)
    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError as exc:
        error_detail = response.text
        raise RuntimeError(
            f"Telegram ส่งข้อความไม่สำเร็จ (HTTP {response.status_code}): {error_detail}"
        ) from exc


def main() -> int:
    load_dotenv()

    try:
        sheet = get_sheet()
        rows = sheet.get_all_values()
        summary = build_summary(rows)

        if "ไม่พบคอลัมน์" in summary or "ยังไม่มีข้อมูล" in summary:
            print(summary)
            return 1

        send_telegram_message(summary)
        print("ส่งสรุปไป Telegram เรียบร้อยแล้ว 🎉")
        return 0
    except Exception as exc:
        print(f"เกิดข้อผิดพลาด: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
