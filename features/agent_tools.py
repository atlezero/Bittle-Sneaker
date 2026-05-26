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
    cost_price = float(kwargs.get("cost_price", 0.0) or 0.0)
    cost_price_val = cost_price
    found_row_idx = None
    matched_sku = sku

    # แตกไซส์
    size_us = kwargs.get("size_us", "ไม่ระบุ")
    size_eu = kwargs.get("size_eu", "ไม่ระบุ")
    if size and size != "ทั่วไป" and size != "ไม่ระบุ":
        if "US" in size.upper() or "us" in size.lower():
            size_us = size
        else:
            size_eu = size

    # ทำการ Validate สต็อกสินค้าก่อนขาย
    if sku != "ไม่ระบุ":
        # กรณีระบุ SKU เจาะจง
        for idx, p in enumerate(products):
            if str(p.get("รหัสสินค้า", "")).strip() == sku:
                found_row_idx = idx + 2
                p_status = str(p.get("สถานะ", "")).strip()
                if p_status == "ขายแล้ว":
                    raise ValueError(f"สินค้าที่มีรหัส '{sku}' ถูกขายไปแล้ว ไม่สามารถขายซ้ำได้")
                try:
                    cost_price_val = float(p.get("ราคาทุน", 0.0) or 0.0)
                except (ValueError, TypeError):
                    pass
                break
        
        if not found_row_idx:
            raise ValueError(f"ไม่พบสินค้าที่มีรหัส '{sku}' ในสต็อก")
    else:
        # กรณีไม่ได้ระบุ SKU (เช่น "ไม่ระบุ") แต่ระบุ แบรนด์, รุ่น, ไซส์
        # ค้นหาสินค้าที่สถานะไม่ใช่ "ขายแล้ว" และตรงแบรนด์/รุ่น/ไซส์
        for idx, p in enumerate(products):
            p_status = str(p.get("สถานะ", "")).strip()
            if p_status == "ขายแล้ว":
                continue
            
            p_brand = str(p.get("แบรนด์", "")).strip().lower()
            p_model = str(p.get("รุ่น", "")).strip().lower()
            p_eu = str(p.get("ไซส์ EU", "")).strip().lower()
            p_us = str(p.get("ไซส์ US", "")).strip().lower()
            
            brand_match = (brand.strip().lower() == p_brand) if brand != "ไม่ระบุ" else True
            model_match = (model.strip().lower() == p_model) if model != "ไม่ระบุ" else True
            
            size_match = True
            if size and size != "ทั่วไป" and size != "ไม่ระบุ":
                sz_clean = size.strip().lower().replace("eu", "").replace("us", "").strip()
                p_eu_clean = p_eu.replace("eu", "").strip()
                p_us_clean = p_us.replace("us", "").strip()
                size_match = (sz_clean == p_eu_clean or sz_clean == p_us_clean)

            if brand_match and model_match and size_match:
                found_row_idx = idx + 2
                matched_sku = str(p.get("รหัสสินค้า", "")).strip()
                try:
                    cost_price_val = float(p.get("ราคาทุน", 0.0) or 0.0)
                except (ValueError, TypeError):
                    pass
                break
                
        if not found_row_idx:
            desc_parts = []
            if brand != "ไม่ระบุ": desc_parts.append(brand)
            if model != "ไม่ระบุ": desc_parts.append(model)
            if size != "ทั่วไป" and size != "ไม่ระบุ": desc_parts.append(f"ไซส์ {size}")
            desc = " ".join(desc_parts) or "สินค้า"
            raise ValueError(f"ไม่พบ '{desc}' ที่พร้อมขายในสต็อก")
        
        sku = matched_sku

    # อัปเดตสถานะสินค้าในสต็อกเป็น "ขายแล้ว"
    status_col = EXPECTED_PRODUCTS_HEADERS.index("สถานะ") + 1
    products_sheet.update_cell(found_row_idx, status_col, "ขายแล้ว")

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
        total_profit = 0.0
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

            profit_val = r.get("กำไร", 0.0)
            profit = 0.0
            try:
                profit = float(profit_val)
            except (ValueError, TypeError):
                pass

            if menu not in menu_summary:
                menu_summary[menu] = {"quantity": 0, "total": 0.0, "profit": 0.0}
            menu_summary[menu]["quantity"] += qty
            menu_summary[menu]["total"] += tot
            menu_summary[menu]["profit"] += profit
            total_revenue += tot
            total_profit += profit
            total_items += qty

        return {
            "status": "success",
            "date": today.isoformat(),
            "total_revenue": total_revenue,
            "total_items": total_items,
            "total_profit": total_profit,
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
    total_profit = 0.0
    total_items = 0
    menu_summary = {}

    for o in today_orders:
        sku = str(o.get("รหัสสินค้า", "")).strip()
        price_val = 0.0
        try:
            price_val = float(o.get("ราคาที่ขาย", 0.0) or 0.0)
        except ValueError:
            pass

        profit_val = 0.0
        try:
            profit_val = float(o.get("กำไร", 0.0) or 0.0)
        except (ValueError, TypeError):
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
            menu_summary[menu] = {"quantity": 0, "total": 0.0, "profit": 0.0}
        menu_summary[menu]["quantity"] += 1
        menu_summary[menu]["total"] += price_val
        menu_summary[menu]["profit"] += profit_val
        total_revenue += price_val
        total_profit += profit_val
        total_items += 1

    return {
        "status": "success",
        "date": today.isoformat(),
        "total_revenue": total_revenue,
        "total_items": total_items,
        "total_profit": total_profit,
        "menu_summary": menu_summary,
    }


def check_stock(
    brand: str = None,
    model: str = None,
    size: str = None,
) -> dict:
    """
    ตรวจสอบสต็อกรองเท้าที่มีสถานะว่าง / พร้อมส่ง (คัดกรองเฉพาะสินค้าที่สถานะไม่ใช่ "ขายแล้ว")
    """
    products_sheet = _get_sheet_safe("Products")
    products = products_sheet.get_all_records()
    
    in_stock = []
    for p in products:
        status = str(p.get("สถานะ", "")).strip()
        if status == "ขายแล้ว":
            continue
            
        # ค้นฟิลเตอร์แบรนด์ (Case-insensitive & Partial Match)
        if brand and brand.strip():
            p_brand = str(p.get("แบรนด์", "")).strip().lower()
            if brand.strip().lower() not in p_brand:
                continue
                
        # ค้นฟิลเตอร์รุ่น (Case-insensitive & Partial Match)
        if model and model.strip():
            p_model = str(p.get("รุ่น", "")).strip().lower()
            if model.strip().lower() not in p_model:
                continue
                
        # ค้นฟิลเตอร์ไซส์ (เช็กทั้ง ไซส์ EU และ ไซส์ US แบบ case-insensitive)
        if size and size.strip():
            target_size = size.strip().lower().replace("eu", "").replace("us", "").strip()
            p_eu = str(p.get("ไซส์ EU", "")).strip().lower().replace("eu", "").strip()
            p_us = str(p.get("ไซส์ US", "")).strip().lower().replace("us", "").strip()
            
            # Match แบบมี/ไม่มีหน่วย EU/US
            if target_size not in p_eu and target_size not in p_us:
                continue
                
        in_stock.append(p)
        
    return {
        "status": "success",
        "count": len(in_stock),
        "products": in_stock
    }


def generate_social_caption(
    product_name: str,
    price: float,
) -> dict:
    """
    สร้างแคปชั่นขายของด้วย AI (Cute, Minimal, Gen-Z) โดยดึงจาก caption_gen.py
    """
    from features.caption_gen import generate_captions
    
    try:
        captions = generate_captions(product_name, int(price))
        return {
            "status": "success",
            "product_name": product_name,
            "price": price,
            "captions": captions
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }


def get_customer_profile(
    name: str = None,
    ig: str = None,
    line: str = None,
    phone: str = None,
) -> dict:
    """
    ค้นหาข้อมูลลูกค้าและประวัติยอดสั่งซื้อสะสม
    """
    customers_sheet = _get_sheet_safe("Customers")
    customers = customers_sheet.get_all_records()
    
    found_customers = []
    
    # ปรับแต่งคำค้นหาเพื่อใช้เปรียบเทียบ
    q_name = name.strip().lower() if name else None
    q_ig = ig.strip().lower().replace("@", "") if ig else None
    q_line = line.strip().lower() if line else None
    q_phone = phone.strip().replace("-", "").replace(" ", "") if phone else None
    
    for c in customers:
        c_name = str(c.get("ชื่อ", "")).strip().lower()
        c_ig = str(c.get("IG", "")).strip().lower().replace("@", "")
        c_line = str(c.get("Line ID", "")).strip().lower()
        c_phone = str(c.get("เบอร์โทร", "")).strip().replace("-", "").replace(" ", "")
        
        match = False
        if q_name and q_name in c_name:
            match = True
        elif q_ig and q_ig in c_ig:
            match = True
        elif q_line and q_line in c_line:
            match = True
        elif q_phone and q_phone in c_phone:
            match = True
            
        if match:
            found_customers.append(c)
            
    return {
        "status": "success",
        "count": len(found_customers),
        "customers": found_customers
    }


def get_sales_summary(period: str = "today") -> dict:
    """
    สรุปยอดขาย: today / month / year
    - today: ยอดขายวันนี้ (เหมือน get_sales_today)
    - month: ยอดขายเดือนนี้
    - year: ยอดขายปีนี้
    """
    if period == "today":
        return get_sales_today()

    products_sheet = _get_sheet_safe("Products")
    orders_sheet = _get_sheet_safe("Orders")

    is_single_sheet = False
    if hasattr(products_sheet, "id") and hasattr(orders_sheet, "id"):
        is_single_sheet = (products_sheet.id == orders_sheet.id)
    else:
        is_single_sheet = (products_sheet == orders_sheet)

    now = datetime.now(THAI_TZ)

    if is_single_sheet:
        # Legacy single-sheet mode
        rows = products_sheet.get_all_records()
        filtered = []
        for r in rows:
            raw_ts = str(r.get("วันที่", "")).strip()
            if not raw_ts:
                continue
            try:
                row_date = datetime.fromisoformat(raw_ts).date()
            except ValueError:
                continue

            if period == "month" and (row_date.year != now.year or row_date.month != now.month):
                continue
            elif period == "year" and row_date.year != now.year:
                continue

            filtered.append(r)

        total_revenue = 0.0
        total_profit = 0.0
        total_items = 0
        menu_summary = {}

        for r in filtered:
            brand = str(r.get("แบรนด์") or "").strip()
            model_name = str(r.get("รุ่น") or "").strip()
            sku = str(r.get("รหัสสินค้า") or "").strip()
            size = str(r.get("ไซส์") or "ทั่วไป").strip()

            name_parts = []
            if sku and sku != "ไม่ระบุ":
                name_parts.append(f"[{sku}]")
            if brand and brand != "ไม่ระบุ":
                name_parts.append(brand)
            if model_name and model_name != "ไม่ระบุ":
                name_parts.append(model_name)
            full_sneaker = " ".join(name_parts) if name_parts else "ไม่ระบุ"
            menu = f"{full_sneaker}_{size}" if size and size != "ทั่วไป" else full_sneaker

            qty = 1
            try:
                qty = int(float(r.get("จำนวน", 1)))
            except (ValueError, TypeError):
                pass

            tot = 0.0
            try:
                tot = float(r.get("ยอดรวม", 0.0))
            except (ValueError, TypeError):
                pass

            profit_val = 0.0
            try:
                profit_val = float(r.get("กำไร", 0.0))
            except (ValueError, TypeError):
                pass

            if menu not in menu_summary:
                menu_summary[menu] = {"quantity": 0, "total": 0.0, "profit": 0.0}
            menu_summary[menu]["quantity"] += qty
            menu_summary[menu]["total"] += tot
            menu_summary[menu]["profit"] += profit_val
            total_revenue += tot
            total_profit += profit_val
            total_items += qty

        period_label = "เดือนนี้" if period == "month" else "ปีนี้"
        return {
            "status": "success",
            "period": period,
            "period_label": period_label,
            "date": now.date().isoformat(),
            "total_revenue": total_revenue,
            "total_items": total_items,
            "total_profit": total_profit,
            "menu_summary": menu_summary,
        }

    # Relational multi-sheet mode
    orders = orders_sheet.get_all_records()
    products = products_sheet.get_all_records()

    sku_to_product = {}
    for p in products:
        p_sku = str(p.get("รหัสสินค้า", "")).strip()
        if p_sku:
            sku_to_product[p_sku] = p

    filtered_orders = []
    for o in orders:
        raw_ts = str(o.get("วันที่ขาย", "")).strip()
        if not raw_ts:
            continue
        try:
            row_date = datetime.fromisoformat(raw_ts).date()
        except ValueError:
            continue

        if period == "month" and (row_date.year != now.year or row_date.month != now.month):
            continue
        elif period == "year" and row_date.year != now.year:
            continue

        filtered_orders.append(o)

    total_revenue = 0.0
    total_profit = 0.0
    total_items = 0
    menu_summary = {}

    for o in filtered_orders:
        sku = str(o.get("รหัสสินค้า", "")).strip()
        price_val = 0.0
        try:
            price_val = float(o.get("ราคาที่ขาย", 0.0) or 0.0)
        except (ValueError, TypeError):
            pass

        profit_val = 0.0
        try:
            profit_val = float(o.get("กำไร", 0.0) or 0.0)
        except (ValueError, TypeError):
            pass

        p_info = sku_to_product.get(sku, {})
        brand = str(p_info.get("แบรนด์") or "ไม่ระบุ").strip()
        model_name = str(p_info.get("รุ่น") or "ไม่ระบุ").strip()
        size = str(p_info.get("ไซส์ EU") or p_info.get("ไซส์ US") or "ทั่วไป").strip()
        if size == "ไม่ระบุ" or not size:
            size = "ทั่วไป"

        name_parts = []
        if sku and sku != "ไม่ระบุ":
            name_parts.append(f"[{sku}]")
        if brand and brand != "ไม่ระบุ":
            name_parts.append(brand)
        if model_name and model_name != "ไม่ระบุ":
            name_parts.append(model_name)
        full_sneaker = " ".join(name_parts) if name_parts else "ไม่ระบุ"
        menu = f"{full_sneaker}_{size}" if size and size != "ทั่วไป" else full_sneaker

        if menu not in menu_summary:
            menu_summary[menu] = {"quantity": 0, "total": 0.0, "profit": 0.0}
        menu_summary[menu]["quantity"] += 1
        menu_summary[menu]["total"] += price_val
        menu_summary[menu]["profit"] += profit_val
        total_revenue += price_val
        total_profit += profit_val
        total_items += 1

    period_label = "เดือนนี้" if period == "month" else "ปีนี้"
    return {
        "status": "success",
        "period": period,
        "period_label": period_label,
        "date": now.date().isoformat(),
        "total_revenue": total_revenue,
        "total_items": total_items,
        "total_profit": total_profit,
        "menu_summary": menu_summary,
    }


def get_sales_by_date(date_str: str) -> dict:
    """
    สรุปยอดขายสำหรับวันที่ระบุ (รูปแบบ YYYY-MM-DD)
    """
    try:
        target_date = datetime.fromisoformat(date_str.strip()).date()
    except ValueError:
        return {
            "status": "error",
            "message": f"รูปแบบวันที่ไม่ถูกต้อง: {date_str} (ต้องเป็น YYYY-MM-DD)"
        }

    products_sheet = _get_sheet_safe("Products")
    orders_sheet = _get_sheet_safe("Orders")

    is_single_sheet = False
    if hasattr(products_sheet, "id") and hasattr(orders_sheet, "id"):
        is_single_sheet = (products_sheet.id == orders_sheet.id)
    else:
        is_single_sheet = (products_sheet == orders_sheet)

    if is_single_sheet:
        # Legacy single-sheet mode
        rows = products_sheet.get_all_records()
        target_rows = []
        for r in rows:
            raw_ts = str(r.get("วันที่", "")).strip()
            if not raw_ts:
                continue
            try:
                row_date = datetime.fromisoformat(raw_ts).date()
            except ValueError:
                continue
            if row_date == target_date:
                target_rows.append(r)

        total_revenue = 0.0
        total_profit = 0.0
        total_items = 0
        menu_summary = {}

        for r in target_rows:
            brand = str(r.get("แบรนด์") or "").strip()
            model_name = str(r.get("รุ่น") or "").strip()
            sku = str(r.get("รหัสสินค้า") or "").strip()
            sneaker = str(r.get("รองเท้า") or r.get("ชื่อเกม") or "").strip()
            size = str(r.get("ไซส์") or r.get("เกรดไอดี") or "ทั่วไป").strip()

            if brand or model_name:
                name_parts = []
                if sku and sku != "ไม่ระบุ":
                    name_parts.append(f"[{sku}]")
                if brand and brand != "ไม่ระบุ":
                    name_parts.append(brand)
                if model_name and model_name != "ไม่ระบุ":
                    name_parts.append(model_name)
                full_sneaker = " ".join(name_parts) if name_parts else "ไม่ระบุ"
            else:
                full_sneaker = sneaker if sneaker else str(r.get("เมนู") or "ไม่ระบุ").strip()

            menu = f"{full_sneaker}_{size}" if size and size != "ทั่วไป" else full_sneaker

            qty = 1
            try:
                qty = int(float(r.get("จำนวน", 1)))
            except (ValueError, TypeError):
                pass

            tot = 0.0
            try:
                tot = float(r.get("ยอดรวม", 0.0))
            except (ValueError, TypeError):
                pass

            profit_val = 0.0
            try:
                profit_val = float(r.get("กำไร", 0.0))
            except (ValueError, TypeError):
                pass

            if menu not in menu_summary:
                menu_summary[menu] = {"quantity": 0, "total": 0.0, "profit": 0.0}
            menu_summary[menu]["quantity"] += qty
            menu_summary[menu]["total"] += tot
            menu_summary[menu]["profit"] += profit_val
            total_revenue += tot
            total_profit += profit_val
            total_items += qty

        return {
            "status": "success",
            "date": target_date.isoformat(),
            "total_revenue": total_revenue,
            "total_items": total_items,
            "total_profit": total_profit,
            "menu_summary": menu_summary,
        }

    # Relational multi-sheet mode
    orders = orders_sheet.get_all_records()
    products = products_sheet.get_all_records()

    sku_to_product = {}
    for p in products:
        p_sku = str(p.get("รหัสสินค้า", "")).strip()
        if p_sku:
            sku_to_product[p_sku] = p

    target_orders = []
    for o in orders:
        raw_ts = str(o.get("วันที่ขาย", "")).strip()
        if not raw_ts:
            continue
        try:
            row_date = datetime.fromisoformat(raw_ts).date()
        except ValueError:
            continue
        if row_date == target_date:
            target_orders.append(o)

    total_revenue = 0.0
    total_profit = 0.0
    total_items = 0
    menu_summary = {}

    for o in target_orders:
        sku = str(o.get("รหัสสินค้า", "")).strip()
        price_val = 0.0
        try:
            price_val = float(o.get("ราคาที่ขาย", 0.0) or 0.0)
        except (ValueError, TypeError):
            pass

        profit_val = 0.0
        try:
            profit_val = float(o.get("กำไร", 0.0) or 0.0)
        except (ValueError, TypeError):
            pass

        p_info = sku_to_product.get(sku, {})
        brand = str(p_info.get("แบรนด์") or "ไม่ระบุ").strip()
        model_name = str(p_info.get("รุ่น") or "ไม่ระบุ").strip()
        size = str(p_info.get("ไซส์ EU") or p_info.get("ไซส์ US") or "ทั่วไป").strip()
        if size == "ไม่ระบุ" or not size:
            size = "ทั่วไป"

        name_parts = []
        if sku and sku != "ไม่ระบุ":
            name_parts.append(f"[{sku}]")
        if brand and brand != "ไม่ระบุ":
            name_parts.append(brand)
        if model_name and model_name != "ไม่ระบุ":
            name_parts.append(model_name)
        full_sneaker = " ".join(name_parts) if name_parts else "ไม่ระบุ"
        menu = f"{full_sneaker}_{size}" if size and size != "ทั่วไป" else full_sneaker

        if menu not in menu_summary:
            menu_summary[menu] = {"quantity": 0, "total": 0.0, "profit": 0.0}
        menu_summary[menu]["quantity"] += 1
        menu_summary[menu]["total"] += price_val
        menu_summary[menu]["profit"] += profit_val
        total_revenue += price_val
        total_profit += profit_val
        total_items += 1

    return {
        "status": "success",
        "date": target_date.isoformat(),
        "total_revenue": total_revenue,
        "total_items": total_items,
        "total_profit": total_profit,
        "menu_summary": menu_summary,
    }


# ─────────────────────────────────────────────────────────────
# Registry
# ─────────────────────────────────────────────────────────────

TOOLS = {
    "log_sale": log_sale,
    "get_sales_today": get_sales_today,
    "get_sales_summary": get_sales_summary,
    "get_sales_by_date": get_sales_by_date,
    "check_stock": check_stock,
    "generate_social_caption": generate_social_caption,
    "get_customer_profile": get_customer_profile,
}