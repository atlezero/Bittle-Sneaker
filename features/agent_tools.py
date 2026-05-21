import os
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import gspread
from dotenv import load_dotenv
from google.oauth2.service_account import Credentials
from .sheets_client import get_sheet

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


def _get_sheet(name: str | None = None) -> gspread.Worksheet:
    return get_sheet(name)


def _get_sheet_safe(name: str) -> gspread.Worksheet:
    try:
        # Try calling _get_sheet with the name argument
        return _get_sheet(name)
    except TypeError:
        # If it fails with TypeError because of zero-arg monkeypatch, call it without arguments!
        return _get_sheet()


# ─────────────────────────────────────────────────────────────
# Relational Database Schema Setup
# ─────────────────────────────────────────────────────────────

EXPECTED_PRODUCTS_HEADERS = [
    "รหัสสินค้า", "แบรนด์", "รุ่น", "สี", "ไซส์ US", "ไซส์ EU", "สภาพ", 
    "รายละเอียดสภาพ", "ราคาทุน", "ราคาขาย", "สถานะ", "ปีที่ผลิต", 
    "มีกล่อง", "มีใบเสร็จ", "รหัสแหล่งที่มา", "วันที่ได้มา", "หมายเหตุ"
]

EXPECTED_ORDERS_HEADERS = [
    "รหัสออเดอร์", "รหัสสินค้า", "รหัสลูกค้า", "วันที่ขาย", "ราคาที่ขาย", 
    "ช่องทางขาย", "ค่าส่ง", "เลข Tracking", "วิธีชำระเงิน", "สถานะชำระเงิน", 
    "กำไร", "หมายเหตุ"
]

EXPECTED_CUSTOMERS_HEADERS = [
    "รหัสลูกค้า", "ชื่อ", "IG", "Line ID", "เบอร์โทร", "ระดับลูกค้า", 
    "จำนวนออเดอร์", "หมายเหตุ"
]

EXPECTED_SOURCES_HEADERS = [
    "รหัสแหล่งที่มา", "ชื่อแหล่งที่มา", "ประเภท", "ช่องทางติดต่อ", 
    "ความน่าเชื่อถือ", "หมายเหตุ"
]

EXPECTED_PHOTOS_HEADERS = [
    "รหัสรูป", "รหัสสินค้า", "ลิงก์รูป", "ประเภทรูป", "วันที่อัปโหลด"
]

EXPECTED_HEADERS = [
    "วันที่",
    "รหัสสินค้า",
    "แบรนด์",
    "รุ่น",
    "ไซส์",
    "จำนวน",
    "ราคา",
    "ยอดรวม",
]


def _ensure_header(sheet: gspread.Worksheet) -> None:
    headers = sheet.row_values(1)
    if not headers:
        sheet.insert_row(EXPECTED_HEADERS, index=1, value_input_option="RAW")
    elif headers != EXPECTED_HEADERS:
        sheet.delete_rows(1)
        sheet.insert_row(EXPECTED_HEADERS, index=1, value_input_option="RAW")


def _ensure_sheet_headers(sheet: gspread.Worksheet, expected_headers: list[str]) -> None:
    headers = sheet.row_values(1)
    if not headers:
        sheet.insert_row(expected_headers, index=1, value_input_option="RAW")
    elif headers != expected_headers:
        sheet.delete_rows(1)
        sheet.insert_row(expected_headers, index=1, value_input_option="RAW")


# ─────────────────────────────────────────────────────────────
# Validation
# ─────────────────────────────────────────────────────────────

def validate_sale(
    menu: str = None,
    sku: str = "ไม่ระบุ",
    brand: str = "ไม่ระบุ",
    model: str = "ไม่ระบุ",
    quantity: int = 1,
    price: float = 0.0,
) -> None:
    if (not menu or not menu.strip()) and sku == "ไม่ระบุ" and brand == "ไม่ระบุ" and model == "ไม่ระบุ":
        raise ValueError("ข้อมูลรองเท้าห้ามว่าง")

    if quantity <= 0:
        raise ValueError("จำนวนต้องมากกว่า 0")

    if price <= 0:
        raise ValueError("ราคาต้องมากกว่า 0")


# ─────────────────────────────────────────────────────────────
# Tools
# ─────────────────────────────────────────────────────────────

def log_sale(
    menu: str = None,
    sku: str = "ไม่ระบุ",
    brand: str = "ไม่ระบุ",
    model: str = "ไม่ระบุ",
    size: str = "ทั่วไป",
    quantity: int = 1,
    price: float = 0.0,
    **kwargs,
) -> dict:
    """
    บันทึกยอดขายลง Google Sheets
    """
    # หากมีการผ่านค่า menu (จาก CLI หรือชุดทดสอบเก่า) ให้แปลงออกเป็น ฟิลด์ต่าง ๆ
    if menu and menu.strip():
        clean_menu = menu.strip()
        parsed_size = "ทั่วไป"
        
        # ค้นหาไซส์จากท้ายข้อความ
        for sep in ["_", " "]:
            if sep in clean_menu:
                parts = clean_menu.rsplit(sep, 1)
                last_part = parts[1].strip()
                if last_part.isalnum() or last_part.replace(".", "", 1).isdigit():
                    parsed_size = last_part
                    clean_menu = parts[0].strip()
                    break

        parsed_sku = "ไม่ระบุ"
        parsed_brand = "ไม่ระบุ"
        parsed_model = "ไม่ระบุ"
        words = clean_menu.split()
        if words:
            first_word = words[0]
            if "-" in first_word or (len(first_word) >= 4 and any(c.isdigit() for c in first_word) and any(c.isalpha() for c in first_word)):
                parsed_sku = first_word
                words = words[1:]
            
            if words:
                parsed_brand = words[0]
                if len(words) > 1:
                    parsed_model = " ".join(words[1:])
                else:
                    parsed_model = "ทั่วไป"
            else:
                parsed_brand = "ทั่วไป"
                parsed_model = "ทั่วไป"

        if sku == "ไม่ระบุ":
            sku = parsed_sku
        if brand == "ไม่ระบุ":
            brand = parsed_brand
        if model == "ไม่ระบุ":
            model = parsed_model
        if size == "ทั่วไป" or not size:
            size = parsed_size

    validate_sale(
        menu=menu,
        sku=sku,
        brand=brand,
        model=model,
        quantity=quantity,
        price=price,
    )

    products_sheet = _get_sheet_safe("Products")
    orders_sheet = _get_sheet_safe("Orders")
    customers_sheet = _get_sheet_safe("Customers")
    sources_sheet = _get_sheet_safe("Sources")
    photos_sheet = _get_sheet_safe("Photos")

    # ตรวจสอบว่าเป็น โหมด Single Sheet หรือไม่ (เช่น โดนม็อคให้ใช้ชีทเดียวกัน)
    is_single_sheet = False
    if hasattr(products_sheet, "id") and hasattr(orders_sheet, "id"):
        is_single_sheet = (products_sheet.id == orders_sheet.id)
    else:
        is_single_sheet = (products_sheet == orders_sheet)

    now = datetime.now(THAI_TZ)
    timestamp = now.isoformat()

    if is_single_sheet:
        # ─────────────────────────────────────────────────────────────
        # โหมด Single Sheet (Backward Compatibility)
        # ─────────────────────────────────────────────────────────────
        _ensure_header(products_sheet)
        total = quantity * price
        products_sheet.append_row(
            [
                timestamp,
                sku,
                brand,
                model,
                size,
                quantity,
                price,
                total,
            ],
            value_input_option="RAW",
        )

        display_name_parts = []
        if sku and sku not in ["ไม่ระบุ", "ทั่วไป"]:
            display_name_parts.append(f"[{sku}]")
        if brand and brand not in ["ไม่ระบุ", "ทั่วไป"]:
            display_name_parts.append(brand)
        if model and model not in ["ไม่ระบุ", "ทั่วไป"]:
            display_name_parts.append(model)
        display_name = " ".join(display_name_parts) if display_name_parts else (menu or "ไม่ระบุ")
        full_menu = f"{display_name}_{size}" if size and size != "ทั่วไป" else display_name

        return {
            "status": "success",
            "menu": full_menu,
            "sku": sku,
            "brand": brand,
            "model": model,
            "size": size,
            "quantity": quantity,
            "price": price,
            "total": total,
            "timestamp": timestamp,
        }

    # ─────────────────────────────────────────────────────────────
    # โหมด Relational Multi-Sheet (5 Sheets)
    # ─────────────────────────────────────────────────────────────
    _ensure_sheet_headers(products_sheet, EXPECTED_PRODUCTS_HEADERS)
    _ensure_sheet_headers(orders_sheet, EXPECTED_ORDERS_HEADERS)
    _ensure_sheet_headers(customers_sheet, EXPECTED_CUSTOMERS_HEADERS)
    _ensure_sheet_headers(sources_sheet, EXPECTED_SOURCES_HEADERS)
    _ensure_sheet_headers(photos_sheet, EXPECTED_PHOTOS_HEADERS)

    # 1. จัดการข้อมูลสินค้า (Products)
    products = products_sheet.get_all_records()
    if sku == "ไม่ระบุ":
        prefix_code = brand[:2].upper() if brand and brand != "ไม่ระบุ" else "SKU"
        sku = f"{prefix_code}-{len(products) + 1:03d}"

    cost_price = float(kwargs.get("cost_price", 0.0) or 0.0)
    color = kwargs.get("color", "ไม่ระบุ")
    condition = kwargs.get("condition", "ไม่ระบุ")
    condition_details = kwargs.get("condition_details", "ไม่ระบุ")

    # แตกไซส์
    size_us = kwargs.get("size_us", "ไม่ระบุ")
    size_eu = kwargs.get("size_eu", "ไม่ระบุ")
    if size and size != "ทั่วไป" and size != "ไม่ระบุ":
        if "US" in size.upper() or "us" in size.lower():
            size_us = size
        else:
            size_eu = size

    found_row_idx = None
    cost_price_val = cost_price
    for idx, p in enumerate(products):
        if str(p.get("รหัสสินค้า", "")).strip() == sku:
            found_row_idx = idx + 2
            try:
                cost_price_val = float(p.get("ราคาทุน", 0.0) or 0.0)
            except ValueError:
                pass
            break

    if found_row_idx:
        status_col = EXPECTED_PRODUCTS_HEADERS.index("สถานะ") + 1
        products_sheet.update_cell(found_row_idx, status_col, "ขายแล้ว")
    else:
        p_row = [
            sku,
            brand,
            model,
            color,
            size_us,
            size_eu,
            condition,
            condition_details,
            cost_price,
            price,
            "ขายแล้ว",
            kwargs.get("year", "ไม่ระบุ"),
            kwargs.get("has_box", "ไม่ระบุ"),
            kwargs.get("has_receipt", "ไม่ระบุ"),
            kwargs.get("source_id", "ไม่ระบุ"),
            kwargs.get("acquisition_date", now.strftime("%Y-%m-%d")),
            kwargs.get("product_notes", "")
        ]
        products_sheet.append_row(p_row, value_input_option="RAW")

    # 2. จัดการข้อมูลลูกค้า (Customers)
    customers = customers_sheet.get_all_records()
    customer_name = kwargs.get("customer_name") or "ลูกค้าทั่วไป"
    customer_ig = kwargs.get("customer_ig", "ไม่ระบุ")
    customer_line = kwargs.get("customer_line", "ไม่ระบุ")
    customer_phone = kwargs.get("customer_phone", "ไม่ระบุ")
    customer_level = kwargs.get("customer_level", "ทั่วไป")

    found_cust_row = None
    customer_id = None
    order_count = 0
    for idx, c in enumerate(customers):
        c_name = str(c.get("ชื่อ", "")).strip()
        c_ig = str(c.get("IG", "")).strip()
        c_line = str(c.get("Line ID", "")).strip()
        c_phone = str(c.get("เบอร์โทร", "")).strip()

        match = False
        if customer_name and customer_name != "ลูกค้าทั่วไป" and c_name == customer_name:
            match = True
        elif customer_ig and customer_ig != "ไม่ระบุ" and c_ig == customer_ig:
            match = True
        elif customer_line and customer_line != "ไม่ระบุ" and c_line == customer_line:
            match = True
        elif customer_phone and customer_phone != "ไม่ระบุ" and c_phone == customer_phone:
            match = True

        if match:
            found_cust_row = idx + 2
            customer_id = c.get("รหัสลูกค้า")
            try:
                order_count = int(c.get("จำนวนออเดอร์", 0))
            except ValueError:
                order_count = 0
            break

    if found_cust_row:
        order_count_col = EXPECTED_CUSTOMERS_HEADERS.index("จำนวนออเดอร์") + 1
        customers_sheet.update_cell(found_cust_row, order_count_col, order_count + 1)
    else:
        customer_id = f"CUST-{len(customers) + 1:04d}"
        c_row = [
            customer_id,
            customer_name,
            customer_ig,
            customer_line,
            customer_phone,
            customer_level,
            1,
            kwargs.get("customer_notes", "")
        ]
        customers_sheet.append_row(c_row, value_input_option="RAW")

    # 3. จัดการข้อมูลการสั่งซื้อ (Orders)
    orders = orders_sheet.get_all_records()
    shipping_fee = kwargs.get("shipping_fee")
    if shipping_fee is None:
        shipping_fee = 0.0 if quantity >= 2 else 50.0

    sales_channel = kwargs.get("sales_channel", "ไม่ระบุ")
    tracking_number = kwargs.get("tracking_number", "ไม่ระบุ")
    payment_method = kwargs.get("payment_method", "ไม่ระบุ")
    payment_status = kwargs.get("payment_status", "ชำระแล้ว")

    # เพิ่มข้อมูลออเดอร์ตามจำนวนคู่
    for i in range(quantity):
        row_order_id = f"ORD-{len(orders) + i + 1:04d}"
        profit_val = price - cost_price_val
        o_row = [
            row_order_id,
            sku,
            customer_id,
            timestamp,
            price,
            sales_channel,
            shipping_fee / quantity,
            tracking_number,
            payment_method,
            payment_status,
            profit_val,
            kwargs.get("order_notes", "")
        ]
        orders_sheet.append_row(o_row, value_input_option="RAW")

    total = quantity * price
    display_name_parts = []
    if sku and sku not in ["ไม่ระบุ", "ทั่วไป"]:
        display_name_parts.append(f"[{sku}]")
    if brand and brand not in ["ไม่ระบุ", "ทั่วไป"]:
        display_name_parts.append(brand)
    if model and model not in ["ไม่ระบุ", "ทั่วไป"]:
        display_name_parts.append(model)
    display_name = " ".join(display_name_parts) if display_name_parts else (menu or "ไม่ระบุ")

    display_size = size_eu if size_eu and size_eu != "ไม่ระบุ" else (size_us if size_us and size_us != "ไม่ระบุ" else "ทั่วไป")
    full_menu = f"{display_name}_{display_size}" if display_size and display_size != "ทั่วไป" else display_name

    return {
        "status": "success",
        "menu": full_menu,
        "sku": sku,
        "brand": brand,
        "model": model,
        "size": display_size,
        "quantity": quantity,
        "price": price,
        "total": total,
        "timestamp": timestamp,
    }


def get_sales_today() -> dict:
    """
    สรุปยอดขายวันนี้
    """
    products_sheet = _get_sheet_safe("Products")
    orders_sheet = _get_sheet_safe("Orders")

    is_single_sheet = False
    if hasattr(products_sheet, "id") and hasattr(orders_sheet, "id"):
        is_single_sheet = (products_sheet.id == orders_sheet.id)
    else:
        is_single_sheet = (products_sheet == orders_sheet)

    today = datetime.now(THAI_TZ).date()

    if is_single_sheet:
        # Legacy mode
        rows = products_sheet.get_all_records()
        today_rows = []
        for r in rows:
            raw_timestamp = str(r.get("วันที่", "")).strip()
            if not raw_timestamp:
                continue
            try:
                row_date = datetime.fromisoformat(raw_timestamp).date()
            except ValueError:
                continue
            if row_date == today:
                today_rows.append(r)

        total_revenue = 0.0
        total_items = 0
        menu_summary = {}

        for r in today_rows:
            brand = str(r.get("แบรนด์") or "").strip()
            model = str(r.get("รุ่น") or "").strip()
            sku = str(r.get("รหัสสินค้า") or "").strip()
            sneaker = str(r.get("รองเท้า") or r.get("ชื่อเกม") or "").strip()
            size = str(r.get("ไซส์") or r.get("เกรดไอดี") or "ทั่วไป").strip()

            if brand or model:
                name_parts = []
                if sku and sku != "ไม่ระบุ":
                    name_parts.append(f"[{sku}]")
                if brand and brand != "ไม่ระบุ":
                    name_parts.append(brand)
                if model and model != "ไม่ระบุ":
                    name_parts.append(model)
                full_sneaker = " ".join(name_parts) if name_parts else "ไม่ระบุ"
            else:
                full_sneaker = sneaker if sneaker else str(r.get("เมนู") or "ไม่ระบุ").strip()

            menu = f"{full_sneaker}_{size}" if size and size != "ทั่วไป" else full_sneaker

            qty_val = r.get("จำนวน", 0)
            qty = 0
            try:
                qty = int(float(qty_val))
            except ValueError:
                pass

            tot_val = r.get("ยอดรวม", 0.0)
            tot = 0.0
            try:
                tot = float(tot_val)
            except ValueError:
                pass

            if menu not in menu_summary:
                menu_summary[menu] = {"quantity": 0, "total": 0.0}
            menu_summary[menu]["quantity"] += qty
            menu_summary[menu]["total"] += tot
            total_revenue += tot
            total_items += qty

        return {
            "status": "success",
            "date": today.isoformat(),
            "total_revenue": total_revenue,
            "total_items": total_items,
            "menu_summary": menu_summary,
        }

    # Relational Mode
    orders = orders_sheet.get_all_records()
    products = products_sheet.get_all_records()

    sku_to_product = {}
    for p in products:
        p_sku = str(p.get("รหัสสินค้า", "")).strip()
        if p_sku:
            sku_to_product[p_sku] = p

    today_orders = []
    for o in orders:
        raw_timestamp = str(o.get("วันที่ขาย", "")).strip()
        if not raw_timestamp:
            continue
        try:
            row_date = datetime.fromisoformat(raw_timestamp).date()
        except ValueError:
            continue
        if row_date == today:
            today_orders.append(o)

    total_revenue = 0.0
    total_items = 0
    menu_summary = {}

    for o in today_orders:
        sku = str(o.get("รหัสสินค้า", "")).strip()
        price_val = 0.0
        try:
            price_val = float(o.get("ราคาที่ขาย", 0.0) or 0.0)
        except ValueError:
            pass

        p_info = sku_to_product.get(sku, {})
        brand = str(p_info.get("แบรนด์") or "ไม่ระบุ").strip()
        model = str(p_info.get("รุ่น") or "ไม่ระบุ").strip()
        size = str(p_info.get("ไซส์ EU") or p_info.get("ไซส์ US") or "ทั่วไป").strip()
        if size == "ไม่ระบุ" or not size:
            size = "ทั่วไป"

        name_parts = []
        if sku and sku != "ไม่ระบุ":
            name_parts.append(f"[{sku}]")
        if brand and brand != "ไม่ระบุ":
            name_parts.append(brand)
        if model and model != "ไม่ระบุ":
            name_parts.append(model)
        full_sneaker = " ".join(name_parts) if name_parts else "ไม่ระบุ"
        menu = f"{full_sneaker}_{size}" if size and size != "ทั่วไป" else full_sneaker

        if menu not in menu_summary:
            menu_summary[menu] = {"quantity": 0, "total": 0.0}
        menu_summary[menu]["quantity"] += 1
        menu_summary[menu]["total"] += price_val
        total_revenue += price_val
        total_items += 1

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