import os
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import gspread
from dotenv import load_dotenv
from google.oauth2.service_account import Credentials

# ── Path setup ────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

# ─────────────────────────────────────────────────────────────
# Google Sheets setup
# ─────────────────────────────────────────────────────────────

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

THAI_TZ = ZoneInfo("Asia/Bangkok")


def _get_sheet() -> gspread.Worksheet:

    creds = Credentials.from_service_account_file(
        str(PROJECT_ROOT / "service-account.json"),
        scopes=SCOPES,
    )

    gc = gspread.authorize(creds)

    spreadsheet_id = os.getenv("GOOGLE_SHEETS_ID")

    if not spreadsheet_id:
        raise EnvironmentError(
            "GOOGLE_SHEETS_ID ไม่พบใน .env"
        )

    spreadsheet = gc.open_by_key(spreadsheet_id)

    return spreadsheet.sheet1


# ─────────────────────────────────────────────────────────────
# Header setup
# ─────────────────────────────────────────────────────────────

EXPECTED_HEADERS = [
    "วันที่",
    "เมนู",
    "จำนวน",
    "ราคา",
    "ยอดรวม",
]


def _ensure_header(
    sheet: gspread.Worksheet,
) -> None:

    headers = sheet.row_values(1)

    # ถ้ายังไม่มี header
    if not headers:

        sheet.insert_row(
            EXPECTED_HEADERS,
            index=1,
            value_input_option="RAW",
        )

        return

    # ถ้า header ไม่ตรง
    if headers != EXPECTED_HEADERS:

        # ลบ header เก่า
        sheet.delete_rows(1)

        # ใส่ใหม่
        sheet.insert_row(
            EXPECTED_HEADERS,
            index=1,
            value_input_option="RAW",
        )


# ─────────────────────────────────────────────────────────────
# Validation
# ─────────────────────────────────────────────────────────────

def validate_sale(
    menu: str,
    quantity: int,
    price: float,
) -> None:

    if not menu or not menu.strip():
        raise ValueError("ชื่อเมนูห้ามว่าง")

    if quantity <= 0:
        raise ValueError("จำนวนต้องมากกว่า 0")

    if price <= 0:
        raise ValueError("ราคาต้องมากกว่า 0")


# ─────────────────────────────────────────────────────────────
# Tools
# ─────────────────────────────────────────────────────────────

def log_sale(
    menu: str,
    quantity: int,
    price: float,
) -> dict:
    """
    บันทึกยอดขายลง Google Sheets
    """

    validate_sale(
        menu,
        quantity,
        price,
    )

    total = quantity * price

    now = datetime.now(THAI_TZ)
    # บันทึกเวลาแบบ ISO 8601 เต็มรูปแบบ (2026-05-15T00:12:23.544407+07:00)
    timestamp = now.isoformat()

    sheet = _get_sheet()

    _ensure_header(sheet)

    # ✅ append "ข้อมูลขาย"
    # ไม่ใช่ append header
    sheet.append_row(
        [
            timestamp,
            menu,
            quantity,
            price,
            total,
        ],
        value_input_option="RAW",
    )

    return {
        "status": "success",
        "menu": menu,
        "quantity": quantity,
        "price": price,
        "total": total,
        "timestamp": timestamp,
    }


def get_sales_today() -> dict:
    """
    สรุปยอดขายวันนี้
    """

    sheet = _get_sheet()

    rows = sheet.get_all_records()

    today = datetime.now(
        THAI_TZ
    ).date()

    today_rows = []

    for r in rows:

        raw_timestamp = str(
            r.get("วันที่", "")
        ).strip()

        if not raw_timestamp:
            continue

        try:
            row_date = datetime.fromisoformat(
                raw_timestamp
            ).date()

        except ValueError:
            continue

        if row_date == today:
            today_rows.append(r)

    total_revenue = sum(
        float(r.get("ยอดรวม", 0))
        for r in today_rows
    )

    total_items = sum(
        int(r.get("จำนวน", 0))
        for r in today_rows
    )

    menu_summary = {}

    for r in today_rows:

        menu = r.get(
            "เมนู",
            "ไม่ระบุ",
        )

        if menu not in menu_summary:

            menu_summary[menu] = {
                "quantity": 0,
                "total": 0.0,
            }

        menu_summary[menu]["quantity"] += int(
            r.get("จำนวน", 0)
        )

        menu_summary[menu]["total"] += float(
            r.get("ยอดรวม", 0)
        )

    return {
        "status": "success",
        "date": today.isoformat(),
        "total_revenue": total_revenue,
        "total_items": total_items,
        "menu_summary": menu_summary,
    }


# ─────────────────────────────────────────────────────────────
# Registry
# ─────────────────────────────────────────────────────────────

TOOLS = {
    "log_sale": log_sale,
    "get_sales_today": get_sales_today,
}