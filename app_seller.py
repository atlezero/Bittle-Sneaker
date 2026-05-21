# app_seller.py — Admin Panel สำหรับผู้ขาย 🔧
import os
import sys
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv
from PIL import Image

# ── Path setup ────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

# ── Page config ───────────────────────────────────────────────
_logo = Image.open(PROJECT_ROOT / "pictures" / "logo.png")
st.set_page_config(
    page_title="Bittle Sneaker — Admin Panel",
    page_icon=_logo,
    layout="wide",
)

from features.agent_harness import run_agent, write_trace
from features.agent_tools import get_sales_today, log_sale
from features.caption_gen import generate_captions
from features.sheets_client import get_sheet

load_dotenv()

# ── CSS: Clean premium admin theme ───────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700;900&display=swap');

html, body, [class*="css"] {
    font-family: 'Outfit', sans-serif;
}

.stApp {
    background: #f8fafc;
    color: #1e293b;
}

[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0f172a 0%, #1e293b 100%);
    color: #f8fafc;
}

[data-testid="stSidebar"] * {
    color: #f8fafc !important;
}

.admin-header {
    background: linear-gradient(135deg, #0f172a 0%, #1e3a5f 100%);
    border-radius: 16px;
    padding: 20px 28px;
    margin-bottom: 24px;
    display: flex;
    align-items: center;
    gap: 16px;
    box-shadow: 0 4px 20px rgba(15, 23, 42, 0.15);
}

.admin-header-text h1 {
    color: white;
    font-size: 1.5rem;
    font-weight: 900;
    margin: 0;
    letter-spacing: -0.5px;
}

.admin-header-text p {
    color: #94a3b8;
    font-size: 0.8rem;
    margin: 2px 0 0;
    letter-spacing: 2px;
    text-transform: uppercase;
}

.metric-card {
    background: white;
    border-radius: 12px;
    padding: 20px 24px;
    border: 1px solid #e2e8f0;
    box-shadow: 0 1px 8px rgba(0,0,0,0.05);
    text-align: center;
}

.metric-value {
    font-size: 2rem;
    font-weight: 900;
    color: #0f172a;
    line-height: 1;
}

.metric-label {
    font-size: 0.75rem;
    color: #64748b;
    letter-spacing: 2px;
    text-transform: uppercase;
    margin-top: 6px;
}

.metric-card.gold .metric-value { color: #b45309; }
.metric-card.green .metric-value { color: #15803d; }

.order-row {
    background: white;
    border-radius: 8px;
    padding: 12px 16px;
    margin-bottom: 8px;
    border: 1px solid #f1f5f9;
    border-left: 3px solid #f97316;
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.caption-card {
    background: white;
    border-radius: 12px;
    padding: 20px;
    border: 1px solid #e2e8f0;
    margin-bottom: 12px;
    box-shadow: 0 1px 6px rgba(0,0,0,0.05);
}

.caption-style-badge {
    font-size: 0.7rem;
    font-weight: 700;
    letter-spacing: 2px;
    text-transform: uppercase;
    padding: 2px 10px;
    border-radius: 99px;
    display: inline-block;
    margin-bottom: 10px;
}

.badge-cute { background: #fce7f3; color: #be185d; }
.badge-minimal { background: #f1f5f9; color: #334155; }
.badge-genz { background: #fef3c7; color: #92400e; }

.caption-text { font-size: 0.95rem; line-height: 1.6; color: #374151; }

.product-table-row {
    background: white;
    border-radius: 8px;
    padding: 10px 16px;
    margin-bottom: 6px;
    border: 1px solid #f1f5f9;
    font-size: 0.85rem;
}

.status-available { color: #15803d; font-weight: 600; }
.status-sold { color: #dc2626; font-weight: 600; }

.stTabs [data-baseweb="tab-list"] {
    background: white;
    border-radius: 12px;
    padding: 4px;
    border: 1px solid #e2e8f0;
    gap: 4px;
}

.stTabs [data-baseweb="tab"] {
    border-radius: 8px !important;
    font-family: 'Outfit', sans-serif !important;
    font-weight: 600 !important;
}

[aria-selected="true"] {
    background: #0f172a !important;
    color: white !important;
}

.stButton > button {
    font-family: 'Outfit', sans-serif !important;
    font-weight: 600 !important;
    border-radius: 8px !important;
}

.stTextInput input, .stTextArea textarea, .stSelectbox select, .stNumberInput input {
    border-radius: 8px !important;
    font-family: 'Outfit', sans-serif !important;
}

hr { border-color: #e2e8f0 !important; }

.success-banner {
    background: linear-gradient(135deg, #d1fae5, #a7f3d0);
    border: 1px solid #6ee7b7;
    border-radius: 10px;
    padding: 14px 18px;
    color: #065f46;
    font-weight: 600;
}

.error-banner {
    background: linear-gradient(135deg, #fee2e2, #fecaca);
    border: 1px solid #fca5a5;
    border-radius: 10px;
    padding: 14px 18px;
    color: #7f1d1d;
    font-weight: 600;
}

.ai-response-box {
    background: linear-gradient(135deg, #f0f9ff, #e0f2fe);
    border: 1px solid #bae6fd;
    border-left: 4px solid #0284c7;
    border-radius: 10px;
    padding: 16px 20px;
    color: #0c4a6e;
    font-size: 0.95rem;
    line-height: 1.6;
}
</style>
""", unsafe_allow_html=True)

# ── Sidebar ───────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style='text-align:center; padding:16px 0 24px;'>
        <div style='font-size:2.5rem;'>⚙️</div>
        <div style='font-weight:900; font-size:1rem; letter-spacing:2px;'>ADMIN PANEL</div>
        <div style='color:#94a3b8; font-size:0.7rem; letter-spacing:3px;'>BITTLE SNEAKER</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("**🗺️ เมนูหลัก**")
    st.markdown("<small style='color:#94a3b8;'>📊 Dashboard — ยอดขายวันนี้</small>", unsafe_allow_html=True)
    st.markdown("<small style='color:#94a3b8;'>📝 บันทึกขาย — AI + แบบฟอร์ม</small>", unsafe_allow_html=True)
    st.markdown("<small style='color:#94a3b8;'>💬 สร้างแคปชั่น — 3 สไตล์</small>", unsafe_allow_html=True)
    st.markdown("<small style='color:#94a3b8;'>📦 สต็อกสินค้า — Products Sheet</small>", unsafe_allow_html=True)
    st.divider()
    st.markdown("<small style='color:#64748b;'>🔗 Sandy Bot ลูกค้า: port 8501<br>🔧 Admin Panel: port 8502</small>", unsafe_allow_html=True)

# ── Header ────────────────────────────────────────────────────
st.markdown("""
<div class='admin-header'>
    <div style='font-size:2.5rem;'>🔧</div>
    <div class='admin-header-text'>
        <h1>Admin Panel — Bittle Sneaker</h1>
        <p>ระบบจัดการร้านสำหรับแอดมิน • Real-time Google Sheets</p>
    </div>
</div>
""", unsafe_allow_html=True)

# ── Tabs ──────────────────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs([
    "📊 Dashboard",
    "📝 บันทึกขาย",
    "💬 สร้างแคปชั่น",
    "📦 สต็อกสินค้า",
])

# ═══════════════════════════════════════════════════════════════
# TAB 1: DASHBOARD
# ═══════════════════════════════════════════════════════════════
with tab1:
    st.subheader("📊 สรุปยอดขายวันนี้")

    col_refresh, _ = st.columns([1, 4])
    with col_refresh:
        refresh = st.button("🔄 รีเฟรช", use_container_width=True)

    if refresh or "sales_data" not in st.session_state:
        with st.spinner("กำลังโหลดข้อมูลจาก Google Sheets..."):
            try:
                result = get_sales_today()
                st.session_state["sales_data"] = result
            except Exception as e:
                st.error(f"❌ โหลดข้อมูลไม่สำเร็จ: {e}")
                st.session_state["sales_data"] = None

    data = st.session_state.get("sales_data")

    if data and data.get("status") == "success":
        total_rev = data.get("total_revenue", 0.0)
        total_items = data.get("total_items", 0)
        menu_summary = data.get("menu_summary", {})

        # Metrics
        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown(f"""
            <div class='metric-card gold'>
                <div class='metric-value'>฿{total_rev:,.0f}</div>
                <div class='metric-label'>ยอดรวมวันนี้</div>
            </div>""", unsafe_allow_html=True)
        with c2:
            st.markdown(f"""
            <div class='metric-card green'>
                <div class='metric-value'>{total_items}</div>
                <div class='metric-label'>คู่ที่ขายได้</div>
            </div>""", unsafe_allow_html=True)
        with c3:
            avg = (total_rev / total_items) if total_items > 0 else 0
            st.markdown(f"""
            <div class='metric-card'>
                <div class='metric-value'>฿{avg:,.0f}</div>
                <div class='metric-label'>ราคาเฉลี่ย/คู่</div>
            </div>""", unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        if menu_summary:
            st.markdown("**รายละเอียดสินค้าที่ขายวันนี้**")
            sorted_items = sorted(menu_summary.items(), key=lambda x: x[1]["total"], reverse=True)
            for menu, info in sorted_items:
                qty = info.get("quantity", 0)
                rev = info.get("total", 0.0)
                st.markdown(f"""
                <div class='order-row'>
                    <span><b>{menu}</b></span>
                    <span style='color:#64748b;'>{qty} คู่</span>
                    <span style='color:#b45309; font-weight:700;'>฿{rev:,.2f}</span>
                </div>""", unsafe_allow_html=True)
        else:
            st.info("📭 ยังไม่มียอดขายสำหรับวันนี้")
    else:
        st.info("กด 🔄 รีเฟรช เพื่อโหลดยอดขาย")


# ═══════════════════════════════════════════════════════════════
# TAB 2: บันทึกขาย
# ═══════════════════════════════════════════════════════════════
with tab2:
    st.subheader("📝 บันทึกยอดขาย")

    mode_ai, mode_form = st.tabs(["🤖 พิมพ์ภาษาไทยธรรมชาติ (AI)", "📋 กรอกแบบฟอร์ม"])

    # ── โหมด AI ─────────────────────────────────────────────
    with mode_ai:
        st.markdown("""
        <div style='background:#eff6ff; border:1px solid #bfdbfe; border-radius:10px; padding:14px 18px; margin-bottom:16px; color:#1e40af; font-size:0.88rem;'>
        💡 <b>วิธีใช้:</b> พิมพ์คำสั่งภาษาไทยเป็นธรรมชาติ แล้ว AI จะแปลงและบันทึกลง Google Sheets อัตโนมัติ<br>
        ตัวอย่าง: <i>"ขาย Nike Air Force 1 ไซส์ 42 ราคา 1,290 บาท ให้คุณบุ๊ค IG @book_sneaker จ่ายโอนแล้ว"</i>
        </div>
        """, unsafe_allow_html=True)

        if "ai_history" not in st.session_state:
            st.session_state.ai_history = []

        for msg in st.session_state.ai_history:
            with st.chat_message(msg["role"]):
                if msg["role"] == "assistant":
                    st.markdown(f"<div class='ai-response-box'>{msg['content']}</div>", unsafe_allow_html=True)
                else:
                    st.write(msg["content"])

        ai_cmd = st.chat_input("พิมพ์คำสั่งขาย หรือถามยอดวันนี้ได้เลย...", key="ai_input")
        if ai_cmd:
            st.session_state.ai_history.append({"role": "user", "content": ai_cmd})
            with st.chat_message("user"):
                st.write(ai_cmd)

            with st.chat_message("assistant"):
                with st.spinner("AI กำลังประมวลผล..."):
                    try:
                        result_text = run_agent(ai_cmd)
                    except Exception as e:
                        result_text = f"❌ เกิดข้อผิดพลาด: {e}"
                st.markdown(f"<div class='ai-response-box'>{result_text}</div>", unsafe_allow_html=True)

            st.session_state.ai_history.append({"role": "assistant", "content": result_text})
            if st.button("🗑️ ล้างประวัติ AI", key="clear_ai"):
                st.session_state.ai_history = []
                st.rerun()

    # ── โหมดแบบฟอร์ม ─────────────────────────────────────
    with mode_form:
        st.markdown("กรอกข้อมูลให้ครบแล้วกด **บันทึก**")

        with st.form("sale_form", clear_on_submit=True):
            fc1, fc2 = st.columns(2)
            with fc1:
                f_sku = st.text_input("รหัสสินค้า (SKU)", placeholder="เช่น NK-001 (เว้นว่างได้)")
                f_brand = st.text_input("แบรนด์ *", placeholder="เช่น Nike, Adidas, Converse")
                f_model = st.text_input("รุ่น *", placeholder="เช่น Air Force 1, Dunk Low")
                f_size = st.text_input("ไซส์", placeholder="เช่น 42 (EU) หรือ 9 (US)")
            with fc2:
                f_qty = st.number_input("จำนวน (คู่) *", min_value=1, max_value=50, value=1)
                f_price = st.number_input("ราคาขาย (บาท) *", min_value=1.0, step=50.0, value=1000.0)
                f_channel = st.selectbox("ช่องทางขาย", ["ไม่ระบุ", "IG", "Line", "Facebook", "Shopee", "Lazada", "หน้าร้าน"])
                f_payment = st.selectbox("วิธีชำระเงิน", ["ไม่ระบุ", "โอนเงิน", "บัตรเครดิต", "เงินสด", "QR Code"])

            st.markdown("**ข้อมูลลูกค้า** (ไม่บังคับ)")
            fc3, fc4, fc5 = st.columns(3)
            with fc3:
                f_cust_name = st.text_input("ชื่อลูกค้า", placeholder="เช่น คุณบุ๊ค")
            with fc4:
                f_cust_ig = st.text_input("IG ลูกค้า", placeholder="เช่น @book_st")
            with fc5:
                f_cust_line = st.text_input("Line ID", placeholder="เช่น book123")

            submitted = st.form_submit_button("✅ บันทึกยอดขาย", use_container_width=True, type="primary")

        if submitted:
            if not f_brand.strip() or not f_model.strip():
                st.markdown("<div class='error-banner'>❌ กรุณากรอก แบรนด์ และ รุ่น ให้ครบ</div>", unsafe_allow_html=True)
            else:
                with st.spinner("กำลังบันทึกลง Google Sheets..."):
                    try:
                        result = log_sale(
                            sku=f_sku.strip() or "ไม่ระบุ",
                            brand=f_brand.strip(),
                            model=f_model.strip(),
                            size=f_size.strip() or "ทั่วไป",
                            quantity=int(f_qty),
                            price=float(f_price),
                            sales_channel=f_channel,
                            payment_method=f_payment,
                            customer_name=f_cust_name.strip() or "ลูกค้าทั่วไป",
                            customer_ig=f_cust_ig.strip() or "ไม่ระบุ",
                            customer_line=f_cust_line.strip() or "ไม่ระบุ",
                        )
                        total = result.get("total", 0)
                        menu = result.get("menu", f"{f_brand} {f_model}")
                        st.markdown(f"""
                        <div class='success-banner'>
                            ✅ บันทึกสำเร็จ! {menu} • {int(f_qty)} คู่ • ฿{total:,.2f}
                        </div>""", unsafe_allow_html=True)
                        write_trace("form_sale", {"brand": f_brand, "model": f_model, "qty": f_qty, "price": f_price})
                    except Exception as e:
                        st.markdown(f"<div class='error-banner'>❌ บันทึกไม่สำเร็จ: {e}</div>", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════
# TAB 3: สร้างแคปชั่น
# ═══════════════════════════════════════════════════════════════
with tab3:
    st.subheader("💬 สร้างแคปชั่นขายรองเท้า")
    st.caption("AI จะสร้างแคปชั่น 3 สไตล์ให้อัตโนมัติ: น่ารัก, มินิมอล และ Gen-Z")

    cc1, cc2 = st.columns([3, 1])
    with cc1:
        cap_product = st.text_input(
            "ชื่อสินค้า",
            placeholder="เช่น Nike Air Force 1 สีขาว มือสอง ไซส์ 42 สภาพ 95%",
            key="cap_product",
        )
    with cc2:
        cap_price = st.number_input("ราคา (บาท)", min_value=1, value=1290, key="cap_price")

    gen_btn = st.button("✨ สร้างแคปชั่น", type="primary", use_container_width=False)

    if gen_btn:
        if not cap_product.strip():
            st.warning("กรุณากรอกชื่อสินค้าก่อนนะคะ")
        else:
            with st.spinner("AI กำลังเขียนแคปชั่น..."):
                try:
                    raw = generate_captions(cap_product.strip(), int(cap_price))

                    # Parse output
                    sections = {"Cute": "", "Minimal": "", "Gen-Z": ""}
                    current_key = None
                    for line in raw.splitlines():
                        line_stripped = line.strip()
                        if line_stripped.startswith("Cute:"):
                            current_key = "Cute"
                            sections[current_key] = line_stripped[5:].strip()
                        elif line_stripped.startswith("Minimal:"):
                            current_key = "Minimal"
                            sections[current_key] = line_stripped[8:].strip()
                        elif line_stripped.startswith("Gen-Z:"):
                            current_key = "Gen-Z"
                            sections[current_key] = line_stripped[6:].strip()
                        elif current_key and line_stripped:
                            sections[current_key] += "\n" + line_stripped

                    badge_map = {"Cute": "badge-cute", "Minimal": "badge-minimal", "Gen-Z": "badge-genz"}
                    emoji_map = {"Cute": "🥰", "Minimal": "◼", "Gen-Z": "🔥"}

                    for style, text in sections.items():
                        if text:
                            badge_cls = badge_map.get(style, "badge-minimal")
                            emoji = emoji_map.get(style, "")
                            st.markdown(f"""
                            <div class='caption-card'>
                                <span class='caption-style-badge {badge_cls}'>{emoji} {style}</span>
                                <div class='caption-text'>{text.replace(chr(10), "<br>")}</div>
                            </div>""", unsafe_allow_html=True)

                except Exception as e:
                    st.error(f"❌ สร้างแคปชั่นไม่สำเร็จ: {e}")


# ═══════════════════════════════════════════════════════════════
# TAB 4: สต็อกสินค้า
# ═══════════════════════════════════════════════════════════════
with tab4:
    st.subheader("📦 สต็อกสินค้าทั้งหมด")

    s_col1, s_col2 = st.columns([1, 4])
    with s_col1:
        if st.button("🔄 โหลดใหม่", key="refresh_stock", use_container_width=True):
            if "stock_data" in st.session_state:
                del st.session_state["stock_data"]

    if "stock_data" not in st.session_state:
        with st.spinner("กำลังโหลดสต็อกจาก Google Sheets..."):
            try:
                sheet = get_sheet("Products")
                records = sheet.get_all_records()
                st.session_state["stock_data"] = records
            except Exception as e:
                st.error(f"❌ โหลดสต็อกไม่สำเร็จ: {e}")
                st.session_state["stock_data"] = []

    stock = st.session_state.get("stock_data", [])

    if stock:
        # Filter controls
        f1, f2, f3 = st.columns(3)
        all_brands = ["ทั้งหมด"] + sorted(set(str(p.get("แบรนด์", "")).strip() for p in stock if p.get("แบรนด์")))
        all_statuses = ["ทั้งหมด", "ว่างอยู่", "ขายแล้ว"]

        with f1:
            sel_brand = st.selectbox("กรองแบรนด์", all_brands)
        with f2:
            sel_status = st.selectbox("กรองสถานะ", all_statuses)
        with f3:
            search_text = st.text_input("ค้นหา SKU / รุ่น", placeholder="เช่น NK-001 หรือ Dunk")

        # Apply filters
        filtered = stock
        if sel_brand != "ทั้งหมด":
            filtered = [p for p in filtered if str(p.get("แบรนด์", "")).strip() == sel_brand]
        if sel_status == "ว่างอยู่":
            filtered = [p for p in filtered if str(p.get("สถานะ", "")).strip() != "ขายแล้ว"]
        elif sel_status == "ขายแล้ว":
            filtered = [p for p in filtered if str(p.get("สถานะ", "")).strip() == "ขายแล้ว"]
        if search_text.strip():
            q = search_text.strip().lower()
            filtered = [p for p in filtered if
                q in str(p.get("รหัสสินค้า", "")).lower() or
                q in str(p.get("รุ่น", "")).lower() or
                q in str(p.get("แบรนด์", "")).lower()]

        # Stats bar
        available_count = sum(1 for p in filtered if str(p.get("สถานะ", "")).strip() != "ขายแล้ว")
        sold_count = sum(1 for p in filtered if str(p.get("สถานะ", "")).strip() == "ขายแล้ว")

        sm1, sm2, sm3 = st.columns(3)
        sm1.metric("📦 รายการที่กรองแล้ว", len(filtered))
        sm2.metric("✅ ว่างอยู่", available_count)
        sm3.metric("🏷️ ขายแล้ว", sold_count)

        st.markdown("<br>", unsafe_allow_html=True)

        # Table header
        h1, h2, h3, h4, h5, h6, h7 = st.columns([1.2, 1, 1.5, 0.8, 0.8, 1, 1])
        h1.markdown("**SKU**")
        h2.markdown("**แบรนด์**")
        h3.markdown("**รุ่น**")
        h4.markdown("**ไซส์ EU**")
        h5.markdown("**สภาพ**")
        h6.markdown("**ราคาขาย**")
        h7.markdown("**สถานะ**")
        st.divider()

        for p in filtered:
            sku = str(p.get("รหัสสินค้า", "")).strip() or "—"
            brand = str(p.get("แบรนด์", "")).strip() or "—"
            model = str(p.get("รุ่น", "")).strip() or "—"
            size_eu = str(p.get("ไซส์ EU", "")).strip() or "—"
            condition = str(p.get("สภาพ", "")).strip() or "—"
            price = str(p.get("ราคาขาย", "")).strip() or "—"
            status = str(p.get("สถานะ", "")).strip() or "ไม่ระบุ"

            is_sold = status == "ขายแล้ว"
            status_cls = "status-sold" if is_sold else "status-available"
            status_icon = "🔴" if is_sold else "🟢"

            r1, r2, r3, r4, r5, r6, r7 = st.columns([1.2, 1, 1.5, 0.8, 0.8, 1, 1])
            r1.markdown(f"<code style='font-size:0.8rem;'>{sku}</code>", unsafe_allow_html=True)
            r2.write(brand)
            r3.write(model)
            r4.write(size_eu)
            r5.write(condition)
            r6.markdown(f"**฿{price}**" if price != "—" else "—")
            r7.markdown(f"<span class='{status_cls}'>{status_icon} {status}</span>", unsafe_allow_html=True)
    else:
        st.info("📭 ยังไม่มีข้อมูลสต็อก หรือยังไม่ได้โหลด กด 🔄 เพื่อโหลด")
