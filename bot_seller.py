# bot_seller.py — Sandy Seller Bot 🏪
# Telegram Bot สำหรับเจ้าของร้าน Bittle Sneaker
# ใช้จัดการร้าน: บันทึกขาย, เช็คสต๊อก, ดูรูปสินค้า, สรุปยอด, เจนแคปชั่น

import io
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import telebot
from dotenv import load_dotenv
from google import genai
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception

# ── Path setup ────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))
load_dotenv(PROJECT_ROOT / ".env")

from features.agent_tools import (
    log_sale,
    get_sales_today,
    get_sales_summary,
    get_sales_by_date,
    check_stock,
    generate_social_caption,
    get_customer_profile,
)
from features.drive_client import find_product_images

# ── Config ────────────────────────────────────────────────────
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ALLOWED_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
THAI_TZ = ZoneInfo("Asia/Bangkok")

if not BOT_TOKEN:
    raise RuntimeError("ต้องตั้งค่า TELEGRAM_BOT_TOKEN ใน .env")

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="Markdown")

# ── Gemini AI client (for NLU) ────────────────────────────────
gemini_client = genai.Client(api_key=GEMINI_API_KEY)
GEMINI_MODEL = "gemini-3.1-flash-lite"

NLU_SYSTEM_INSTRUCTION = """คุณคือระบบแปลงคำสั่งภาษาไทยของเจ้าของร้านรองเท้ามือสอง Bittle Sneaker ให้เป็น JSON action
ตอบเป็น JSON เท่านั้น ห้ามมีข้อความอื่น

กติกาสำคัญในการตัดสินใจเลือก Tool:
- คุณต้องวิเคราะห์เจตนาอย่างเคร่งครัด ห้ามเดามั่วเด็ดขาด!
- หากมีข้อมูลช่วงเวลาหรือหัวข้อที่บอทและ Tool ของบอทไม่รองรับ (เช่น "สัปดาห์ก่อน", "เมื่อ 3 วันที่แล้ว" หรือคำขออื่นๆ ที่อยู่นอกเหนือฟังก์ชันของบอท) คุณต้องตอบกลับเป็น {"action": "unknown", "args": {}} ทันที!
- หากผู้ใช้ระบุเจาะจงวันที่ เช่น "สรุปยอดเมื่อวาน", "สรุปยอดขายวันที่ 25", หรือระบุวันที่ชัดเจน ให้เลือกใช้ get_sales_by_date และแปลงวันที่ระบุนั้นเป็น ISO format (YYYY-MM-DD) โดยเปรียบเทียบจาก "เวลาปัจจุบันในระบบ" ที่แนบไปใน Prompt

Actions ที่รองรับ:

1. บันทึกยอดขาย (log_sale):
   อาร์กิวเมนต์ใน args:
   - sku: รหัสสินค้า (เช่น NK-001, หากไม่ระบุให้ใส่ "ไม่ระบุ")
   - brand: แบรนด์ (เช่น Nike, Adidas)
   - model: รุ่น (เช่น Dunk Low, Air Force 1)
   - size: ไซส์ (เช่น 42, 43)
   - quantity: จำนวน (int, default 1)
   - price: ราคาขาย (float)
   - customer_name: ชื่อลูกค้า (default "ลูกค้าทั่วไป")
   - customer_ig: IG ลูกค้า (default "ไม่ระบุ")
   - customer_line: Line ลูกค้า (default "ไม่ระบุ")
   - customer_phone: เบอร์โทรลูกค้า (default "ไม่ระบุ")
   - sales_channel: ช่องทางขาย (เช่น IG, Line, Facebook, หน้าร้าน)
   - payment_method: วิธีชำระเงิน (เช่น โอนเงิน, เงินสด)
   
   ตัวอย่าง:
   {"action": "log_sale", "args": {"sku": "NK-001", "brand": "Nike", "model": "Dunk Low", "size": "42", "quantity": 1, "price": 3500.0, "customer_name": "คุณจอย", "sales_channel": "IG"}}

2. สรุปยอดขายตามคาบเวลาปกติ (get_sales_summary):
   - period: "today" (วันนี้) / "month" (เดือนนี้) / "year" (ปีนี้)
   *หมายเหตุ: ใช้เฉพาะวันนี้ เดือนนี้ หรือปีนี้เท่านั้น หากเป็นระบุวันที่เจาะจงหรือ "เมื่อวานนี้" ให้ใช้ get_sales_by_date แทน!
   ตัวอย่าง:
   {"action": "get_sales_summary", "args": {"period": "today"}}

3. สรุปยอดขายตามระบุวันที่เจาะจง (get_sales_by_date):
   - date_str: วันที่ต้องการสรุปยอดขาย (รูปแบบ YYYY-MM-DD เท่านั้น)
   *หมายเหตุ: ใช้สำหรับยอดขายเมื่อวานนี้ หรือระบุวันเจาะจง เช่น "ยอดขายเมื่อวาน", "สรุปยอดวันที่ 2026-05-25"
   ตัวอย่างคำสั่ง "สรุปยอดขายเมื่อวานนี้หน่อย" (เมื่อเวลาปัจจุบันคือ 2026-05-26):
   {"action": "get_sales_by_date", "args": {"date_str": "2026-05-25"}}

4. เช็คสต๊อก (check_stock):
   - brand: แบรนด์ (optional)
   - model: รุ่น (optional)
   - size: ไซส์ (optional)
   ตัวอย่าง:
   {"action": "check_stock", "args": {"brand": "Nike"}}

5. เจนแคปชั่น (generate_social_caption):
   - product_name: ข้อมูลสินค้า
   - price: ราคา (float)
   ตัวอย่าง:
   {"action": "generate_social_caption", "args": {"product_name": "Nike Dunk Low Panda ไซส์ 42 สภาพ 90%", "price": 2490.0}}

6. ดูรูปสินค้า (view_product_image):
   - sku: รหัสสินค้า (เช่น NK-001)
   ตัวอย่าง:
   {"action": "view_product_image", "args": {"sku": "NK-001"}}

7. ค้นหาลูกค้า (get_customer_profile):
   - name / ig / line / phone
   ตัวอย่าง:
   {"action": "get_customer_profile", "args": {"name": "จอย"}}

8. คำสั่งที่ไม่เกี่ยวข้อง หรือไม่รองรับ:
   {"action": "unknown", "args": {}}
"""


# ── Security ──────────────────────────────────────────────────
def is_authorized(message) -> bool:
    """ตรวจสอบว่าผู้ส่งมี chat_id ตรงกับที่อนุญาต"""
    if not ALLOWED_CHAT_ID:
        return True
    return str(message.chat.id) == str(ALLOWED_CHAT_ID)


def unauthorized_reply(message):
    bot.reply_to(message, "⛔ ไม่มีสิทธิ์ใช้งานบอทนี้ค่ะ")


# ── Helpers ───────────────────────────────────────────────────
def escape_md(text: str) -> str:
    """Escape special markdown characters for Telegram"""
    if not text:
        return ""
    text = str(text)
    # Escape legacy Markdown special characters: \, _, *, [, `
    # Note: We must escape backslash first
    for char in ['\\', '_', '*', '[', '`']:
        if char == '\\':
            text = text.replace('\\', '\\\\')
        else:
            text = text.replace(char, f"\\{char}")
    return text


def format_stock_item(p: dict, idx: int) -> str:
    """จัดรูปแบบสินค้า 1 ชิ้นสำหรับแสดงในสต๊อก"""
    sku = str(p.get("รหัสสินค้า", "")).strip()
    brand = str(p.get("แบรนด์", "")).strip()
    model = str(p.get("รุ่น", "")).strip()
    size_eu = str(p.get("ไซส์ EU", "")).strip()
    size_us = str(p.get("ไซส์ US", "")).strip()
    condition = str(p.get("สภาพ", "")).strip()
    price = str(p.get("ราคาขาย", "")).strip()
    status = str(p.get("สถานะ", "")).strip()
    has_box = str(p.get("มีกล่อง", "")).strip()

    size_str = ""
    if size_eu and size_eu not in ["ไม่ระบุ", "ทั่วไป"]:
        size_str = f"EU {size_eu}"
    elif size_us and size_us not in ["ไม่ระบุ", "ทั่วไป"]:
        size_str = f"US {size_us}"

    box_icon = "📦" if has_box == "มีกล่อง" else ""

    escaped_brand = escape_md(brand)
    escaped_model = escape_md(model)
    lines = [f"{idx}. *{escaped_brand} {escaped_model}*"]
    if sku:
        lines[0] += f"  `[{sku}]`"
    details = []
    if size_str:
        details.append(f"👟 {escape_md(size_str)}")
    if condition:
        details.append(f"✨ สภาพ {escape_md(condition)}")
    if price:
        details.append(f"💰 ฿{escape_md(price)}")
    if box_icon:
        details.append(box_icon)
    if status:
        details.append(f"📋 {escape_md(status)}")
    if details:
        lines.append("   " + " | ".join(details))
    return "\n".join(lines)


def format_sales_summary(result: dict) -> str:
    """จัดรูปแบบสรุปยอดขาย"""
    period_label = result.get("period_label")
    if not period_label:
        if result.get("period") == "today":
            period_label = "วันนี้"
        elif result.get("period") == "month":
            period_label = "เดือนนี้"
        elif result.get("period") == "year":
            period_label = "ปีนี้"
        else:
            period_label = f"วันที่ {result.get('date', '')}"

    summary = result.get("menu_summary", {})
    total_revenue = result.get("total_revenue", 0.0)
    total_items = result.get("total_items", 0)
    total_profit = result.get("total_profit", 0.0)

    lines = [
        f"📊 *สรุปยอดขาย{period_label}*",
        f"📅 วันที่: {result.get('date', '')}",
        "─────────────────",
    ]

    if not summary:
        lines.append("ยังไม่มียอดขายค่ะ 🥲")
    else:
        for menu, data in sorted(summary.items()):
            qty = data.get("quantity", 0)
            total = data.get("total", 0.0)
            profit = data.get("profit", 0.0)
            escaped_menu = escape_md(menu)
            line = f"• {escaped_menu}: {qty} คู่ (฿{total:,.0f})"
            if profit:
                line += f" กำไร ฿{profit:,.0f}"
            lines.append(line)

    lines.append("─────────────────")
    lines.append(f"💰 *ยอดรวม:* ฿{total_revenue:,.0f}")
    lines.append(f"👟 *จำนวน:* {total_items} คู่")
    if total_profit:
        lines.append(f"💸 *กำไร:* ฿{total_profit:,.0f}")

    return "\n".join(lines)


# ── Gemini NLU ────────────────────────────────────────────────
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception(lambda e: "503" in str(e) or "UNAVAILABLE" in str(e).upper()),
    reraise=True,
)
def parse_user_command(text: str) -> dict:
    """ใช้ Gemini แปลงข้อความภาษาไทย → JSON action"""
    now = datetime.now(THAI_TZ)
    # แนบวันและเวลาปัจจุบันไปด้วย เพื่อให้ Gemini คำนวณวันที่สัมพัทธ์ได้ เช่น เมื่อวานนี้, 2 วันก่อน
    day_name = ['จันทร์', 'อังคาร', 'พุธ', 'พฤหัสบดี', 'ศุกร์', 'เสาร์', 'อาทิตย์'][now.weekday()]
    prompt = f"เวลาปัจจุบันในระบบ: {now.strftime('%Y-%m-%d %H:%M:%S')} (วัน{day_name})\nข้อความจากผู้ใช้: {text}"

    response = gemini_client.models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt,
        config={
            "system_instruction": NLU_SYSTEM_INSTRUCTION,
            "response_mime_type": "application/json",
        },
    )
    raw = response.text.strip()
    return json.loads(raw)


# ── Command Handlers ──────────────────────────────────────────

@bot.message_handler(commands=["start", "help"])
def cmd_start(message):
    if not is_authorized(message):
        return unauthorized_reply(message)

    text = (
        "🏪 *Sandy Seller Bot — Bittle Sneaker*\n"
        "สวัสดีค่ะเจ้าของร้าน! หนูคือ Sandy บอทช่วยจัดการร้านค่า 👟✨\n\n"
        "*📋 คำสั่งที่ใช้ได้:*\n"
        "─────────────────\n"
        "📦 `/stock` — เช็คสต๊อกทั้งหมด\n"
        "📦 `/stock nike` — ฟิลเตอร์แบรนด์\n"
        "📦 `/stock dunk low` — ฟิลเตอร์รุ่น\n"
        "─────────────────\n"
        "📊 `/sales` — ยอดขายวันนี้\n"
        "📊 `/sales month` — ยอดขายเดือนนี้\n"
        "📊 `/sales year` — ยอดขายปีนี้\n"
        "─────────────────\n"
        "📸 `/photo NK-001` — ดูรูปสินค้า\n"
        "✨ `/caption Nike Dunk Low 2490` — เจนแคปชั่น\n"
        "─────────────────\n\n"
        "💬 *หรือพิมพ์ภาษาไทยได้เลย เช่น:*\n"
        '• "ขาย Nike Dunk Low ไซส์42 ราคา3500"\n'
        '• "เช็คสต๊อก adidas"\n'
        '• "สรุปยอดขายเดือนนี้"\n'
        '• "เจนแคปชั่น Nike AF1 สภาพ95% ราคา2990"\n'
    )
    bot.reply_to(message, text)


@bot.message_handler(commands=["stock"])
def cmd_stock(message):
    if not is_authorized(message):
        return unauthorized_reply(message)

    # parse arguments: /stock [brand_or_model] [size]
    args_text = message.text.replace("/stock", "").strip()

    brand_filter = None
    model_filter = None
    size_filter = None

    if args_text:
        # ตรวจสอบว่ามีตัวเลขไซส์อยู่หรือไม่
        size_match = re.search(r"(\d+(?:\.\d+)?)\s*$", args_text)
        if size_match:
            size_filter = size_match.group(1)
            args_text = args_text[: size_match.start()].strip()

        if args_text:
            # ถ้าเป็นคำเดียว = brand, ถ้ามีมากกว่าหนึ่งคำ = model (ลอง brand + model)
            words = args_text.split()
            known_brands = ["nike", "adidas", "new balance", "converse", "vans", "puma", "reebok", "asics", "jordan"]
            first_word_lower = words[0].lower()

            if first_word_lower in known_brands:
                brand_filter = words[0]
                if len(words) > 1:
                    model_filter = " ".join(words[1:])
            else:
                # อาจเป็น model ตรงๆ หรือแบรนด์ไทย
                model_filter = args_text

    bot.send_chat_action(message.chat.id, "typing")

    try:
        result = check_stock(brand=brand_filter, model=model_filter, size=size_filter)
        products = result.get("products", [])
        count = result.get("count", 0)

        if count == 0:
            filter_desc = []
            if brand_filter:
                filter_desc.append(f"แบรนด์ {brand_filter}")
            if model_filter:
                filter_desc.append(f"รุ่น {model_filter}")
            if size_filter:
                filter_desc.append(f"ไซส์ {size_filter}")
            desc = " ".join(filter_desc) if filter_desc else "ทั้งหมด"
            bot.reply_to(message, f"📦 ไม่พบสินค้าที่ว่าง ({desc}) 🥲")
            return

        # จัดรูปแบบรายการสินค้า
        header = f"📦 *สต๊อกสินค้าว่าง ({count} คู่)*\n"
        filter_parts = []
        if brand_filter:
            filter_parts.append(f"แบรนด์: {brand_filter}")
        if model_filter:
            filter_parts.append(f"รุ่น: {model_filter}")
        if size_filter:
            filter_parts.append(f"ไซส์: {size_filter}")
        if filter_parts:
            header += f"🔍 _{', '.join(filter_parts)}_\n"
        header += "─────────────────\n"

        items_text = []
        for idx, p in enumerate(products, 1):
            items_text.append(format_stock_item(p, idx))

        full_text = header + "\n".join(items_text)

        # Telegram message limit = 4096 chars
        if len(full_text) > 4000:
            # ส่งแบบแยกข้อความ
            bot.reply_to(message, header + f"_(แสดง {min(count, 20)} จาก {count} รายการ)_")
            chunk = []
            chunk_len = 0
            for item in items_text[:20]:
                if chunk_len + len(item) > 3800:
                    bot.send_message(message.chat.id, "\n".join(chunk))
                    chunk = []
                    chunk_len = 0
                chunk.append(item)
                chunk_len += len(item)
            if chunk:
                bot.send_message(message.chat.id, "\n".join(chunk))
        else:
            bot.reply_to(message, full_text)

    except Exception as e:
        bot.reply_to(message, f"❌ เกิดข้อผิดพลาด: {e}")


@bot.message_handler(commands=["sales"])
def cmd_sales(message):
    if not is_authorized(message):
        return unauthorized_reply(message)

    args_text = message.text.replace("/sales", "").strip().lower()

    period = "today"
    if args_text in ["month", "เดือน", "เดือนนี้"]:
        period = "month"
    elif args_text in ["year", "ปี", "ปีนี้"]:
        period = "year"

    bot.send_chat_action(message.chat.id, "typing")

    try:
        result = get_sales_summary(period=period)
        text = format_sales_summary(result)
        bot.reply_to(message, text)
    except Exception as e:
        bot.reply_to(message, f"❌ เกิดข้อผิดพลาด: {e}")


@bot.message_handler(commands=["photo"])
def cmd_photo(message):
    if not is_authorized(message):
        return unauthorized_reply(message)

    args_text = message.text.replace("/photo", "").strip().upper()

    if not args_text:
        bot.reply_to(message, "📸 กรุณาระบุรหัสสินค้า เช่น `/photo NK-001`")
        return

    # ค้นหารหัสสินค้าจากข้อความ
    code_match = re.search(r"[A-Za-z]{2}-\d{3}", args_text)
    product_code = code_match.group(0) if code_match else args_text

    bot.send_chat_action(message.chat.id, "upload_photo")

    try:
        results = find_product_images(product_code)

        if not results:
            bot.reply_to(
                message,
                f"📸 ไม่พบรูปสินค้ารหัส `{product_code}` ใน Google Drive 🥲\n"
                "ลองเช็คว่าอัปโหลดรูปแล้วและตั้งชื่อไฟล์ให้มีรหัสสินค้าอยู่ด้วยนะคะ",
            )
            return

        bot.reply_to(message, f"📸 พบรูปสินค้า `{product_code}` จำนวน {len(results)} รูป")

        # ส่งรูปภาพทีละรูป
        for idx, img in enumerate(results, 1):
            img_bytes = img.get("bytes")
            img_name = img.get("name", f"photo_{idx}")
            if img_bytes:
                photo = io.BytesIO(img_bytes)
                photo.name = img_name
                bot.send_photo(
                    message.chat.id,
                    photo,
                    caption=f"📸 {product_code} — มุมที่ {idx}/{len(results)}",
                )

    except Exception as e:
        bot.reply_to(message, f"❌ เกิดข้อผิดพลาดในการดึงรูป: {e}")


@bot.message_handler(commands=["caption"])
def cmd_caption(message):
    if not is_authorized(message):
        return unauthorized_reply(message)

    args_text = message.text.replace("/caption", "").strip()

    if not args_text:
        bot.reply_to(
            message,
            "✨ กรุณาระบุข้อมูลสินค้าและราคา เช่น:\n"
            "`/caption Nike Dunk Low ไซส์42 สภาพ90% 2490`",
        )
        return

    # ดึงราคาจากตัวเลขสุดท้ายในข้อความ
    price_match = re.search(r"(\d+(?:\.\d+)?)\s*$", args_text)
    if price_match:
        price = float(price_match.group(1))
        product_name = args_text[: price_match.start()].strip()
    else:
        # ไม่มีราคา — ลองใช้ราคา 0
        price = 0.0
        product_name = args_text

    if not product_name:
        bot.reply_to(message, "✨ กรุณาระบุชื่อสินค้าด้วยค่ะ")
        return

    bot.send_chat_action(message.chat.id, "typing")

    try:
        result = generate_social_caption(product_name=product_name, price=price)

        if result.get("status") == "success":
            captions = result.get("captions", "")
            text = (
                f"✨ *แคปชั่นสำหรับ:* {escape_md(product_name)}\n"
                f"💰 *ราคา:* ฿{price:,.0f}\n"
                "─────────────────\n"
                f"{captions}\n"
                "─────────────────\n"
                "📋 _กดค้างเพื่อ copy ข้อความได้เลยค่ะ~_"
            )
            bot.reply_to(message, text)
        else:
            bot.reply_to(message, f"❌ เจนแคปชั่นไม่สำเร็จ: {result.get('message', 'ไม่ทราบสาเหตุ')}")

    except Exception as e:
        bot.reply_to(message, f"❌ เกิดข้อผิดพลาด: {e}")


# ── Natural Language Handler (Gemini NLU) ─────────────────────
@bot.message_handler(func=lambda m: True, content_types=["text"])
def handle_natural_language(message):
    if not is_authorized(message):
        return unauthorized_reply(message)

    user_text = message.text.strip()
    if not user_text:
        return

    bot.send_chat_action(message.chat.id, "typing")

    try:
        action_data = parse_user_command(user_text)
    except json.JSONDecodeError:
        bot.reply_to(
            message,
            "🤔 ไม่เข้าใจคำสั่งค่ะ ลองพิมพ์ `/help` เพื่อดูคำสั่งที่ใช้ได้นะคะ",
        )
        return
    except Exception as e:
        bot.reply_to(message, f"❌ Gemini API Error: {e}")
        return

    # Handle list of actions or single action
    if isinstance(action_data, list):
        actions = action_data
    elif isinstance(action_data, dict):
        actions = [action_data]
    else:
        bot.reply_to(message, "🤔 ไม่เข้าใจคำสั่งค่ะ")
        return

    for item in actions:
        action = item.get("action", "unknown")
        args = item.get("args", {})

        try:
            if action == "log_sale":
                result = log_sale(**args)
                text = (
                    "✅ *บันทึกยอดขายสำเร็จ!*\n"
                    "─────────────────\n"
                    f"👟 สินค้า: {escape_md(result.get('menu', 'ไม่ระบุ'))}\n"
                    f"📋 รหัส: `{result.get('sku', 'ไม่ระบุ')}`\n"
                    f"🔢 จำนวน: {result.get('quantity', 1)} คู่\n"
                    f"💰 ราคา: ฿{result.get('price', 0):,.0f}\n"
                    f"💵 ยอดรวม: ฿{result.get('total', 0):,.0f}\n"
                    f"🕐 เวลา: {result.get('timestamp', '')}"
                )
                bot.reply_to(message, text)

            elif action == "get_sales_today":
                result = get_sales_today()
                text = format_sales_summary(result)
                bot.reply_to(message, text)

            elif action == "get_sales_summary":
                period = args.get("period", "today")
                result = get_sales_summary(period=period)
                text = format_sales_summary(result)
                bot.reply_to(message, text)

            elif action == "get_sales_by_date":
                date_str = args.get("date_str", "")
                result = get_sales_by_date(date_str=date_str)
                if result.get("status") == "success":
                    text = format_sales_summary(result)
                    bot.reply_to(message, text)
                else:
                    bot.reply_to(message, f"❌ {result.get('message', 'ไม่สามารถสรุปยอดขายสำหรับวันที่ระบุได้')}")

            elif action == "check_stock":
                result = check_stock(**args)
                products = result.get("products", [])
                count = result.get("count", 0)

                if count == 0:
                    bot.reply_to(message, "📦 ไม่พบสินค้าที่ตรงกับเงื่อนไข 🥲")
                else:
                    header = f"📦 *สต๊อกสินค้าว่าง ({count} คู่)*\n─────────────────\n"
                    items = [format_stock_item(p, i) for i, p in enumerate(products[:20], 1)]
                    full_text = header + "\n".join(items)
                    if len(full_text) > 4000:
                        bot.reply_to(message, header)
                        chunk = []
                        for item in items:
                            if sum(len(c) for c in chunk) + len(item) > 3800:
                                bot.send_message(message.chat.id, "\n".join(chunk))
                                chunk = []
                            chunk.append(item)
                        if chunk:
                            bot.send_message(message.chat.id, "\n".join(chunk))
                    else:
                        bot.reply_to(message, full_text)

            elif action == "generate_social_caption":
                product_name = args.get("product_name", "")
                price = float(args.get("price", 0))
                result = generate_social_caption(product_name=product_name, price=price)
                if result.get("status") == "success":
                    captions = result.get("captions", "")
                    text = (
                        f"✨ *แคปชั่นสำหรับ:* {escape_md(product_name)}\n"
                        f"💰 ราคา: ฿{price:,.0f}\n"
                        "─────────────────\n"
                        f"{captions}"
                    )
                    bot.reply_to(message, text)
                else:
                    bot.reply_to(message, f"❌ {result.get('message', 'เจนแคปชั่นไม่สำเร็จ')}")

            elif action == "view_product_image":
                sku = args.get("sku", "")
                if not sku:
                    bot.reply_to(message, "📸 กรุณาระบุรหัสสินค้าด้วยค่ะ")
                    continue

                bot.send_chat_action(message.chat.id, "upload_photo")
                results = find_product_images(sku)
                if not results:
                    bot.reply_to(message, f"📸 ไม่พบรูปสินค้ารหัส `{sku}` 🥲")
                else:
                    bot.reply_to(message, f"📸 พบรูปสินค้า `{sku}` จำนวน {len(results)} รูป")
                    for idx, img in enumerate(results, 1):
                        img_bytes = img.get("bytes")
                        if img_bytes:
                            photo = io.BytesIO(img_bytes)
                            photo.name = img.get("name", f"photo_{idx}")
                            bot.send_photo(
                                message.chat.id,
                                photo,
                                caption=f"📸 {sku} — มุมที่ {idx}/{len(results)}",
                            )

            elif action == "get_customer_profile":
                result = get_customer_profile(**args)
                customers = result.get("customers", [])
                if not customers:
                    bot.reply_to(message, "👤 ไม่พบข้อมูลลูกค้าที่ตรงกัน 🥲")
                else:
                    lines = [f"👤 *พบลูกค้า {len(customers)} คน*\n─────────────────"]
                    for c in customers:
                        c_id = c.get("รหัสลูกค้า", "")
                        c_name = c.get("ชื่อ", "")
                        c_ig = c.get("IG", "")
                        c_line = c.get("Line ID", "")
                        c_phone = c.get("เบอร์โทร", "")
                        c_orders = c.get("จำนวนออเดอร์", 0)
                        c_level = c.get("ระดับลูกค้า", "")
                        lines.append(f"• *{escape_md(c_name)}* `[{c_id}]`")
                        details = []
                        if c_ig and c_ig != "ไม่ระบุ":
                            details.append(f"IG: {escape_md(c_ig)}")
                        if c_line and c_line != "ไม่ระบุ":
                            details.append(f"Line: {escape_md(c_line)}")
                        if c_phone and c_phone != "ไม่ระบุ":
                            details.append(f"📞 {escape_md(c_phone)}")
                        if details:
                            lines.append("  " + " | ".join(details))
                        lines.append(f"  🛒 สั่งซื้อ: {c_orders} ครั้ง | ระดับ: {escape_md(c_level)}")
                    bot.reply_to(message, "\n".join(lines))

            elif action == "unknown":
                bot.reply_to(
                    message,
                    "🤔 ไม่เข้าใจคำสั่งค่ะ ลองพิมพ์ `/help` เพื่อดูคำสั่งที่ใช้ได้นะคะ~",
                )
            else:
                bot.reply_to(message, f"🤔 ไม่รู้จัก action: {action}")

        except Exception as e:
            bot.reply_to(message, f"❌ เกิดข้อผิดพลาดใน {action}: {e}")


# ── Main ──────────────────────────────────────────────────────
if __name__ == "__main__":
    # Fix Windows console encoding for Thai/emoji characters
    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

    print("🏪 Sandy Seller Bot กำลังเริ่มทำงาน...")
    print(f"📱 Telegram Bot Token: {BOT_TOKEN[:10]}...")
    print(f"🔒 Allowed Chat ID: {ALLOWED_CHAT_ID}")
    print("─────────────────────────────────")
    print("Bot is running! Press Ctrl+C to stop.")

    bot.infinity_polling(timeout=60, long_polling_timeout=60)

