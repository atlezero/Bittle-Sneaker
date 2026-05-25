# app_customer.py — Sandy Bot สำหรับลูกค้า 🛍️
import os
import sys
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv
from google import genai
from PIL import Image

# ── Path setup ────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

# ── Page config ───────────────────────────────────────────────
import base64
from io import BytesIO

logo_txt_path = PROJECT_ROOT / "pictures" / "logo_base64.txt"
if logo_txt_path.exists():
    try:
        logo_data = base64.b64decode(logo_txt_path.read_text(encoding="utf-8"))
        _logo = Image.open(BytesIO(logo_data))
    except Exception:
        _logo = Image.new("RGB", (128, 128), color="#1a1a2e")
else:
    _logo = Image.new("RGB", (128, 128), color="#1a1a2e")

st.set_page_config(
    page_title="Bittle Sneaker — Sandy Bot",
    page_icon=_logo,
    layout="centered",
)

from features.rag_engine import RAGEngine
from features.agent_harness import write_trace
from features.sheets_client import get_sheet
import uuid
from features.memory import FirestoreMemory
from features.drive_client import get_product_images_for_text, find_product_images

load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
MODEL = "gemini-3.1-flash-lite-preview"

# ── Session & memory setup ────────────────────────────────────
if "session_id" not in st.session_state:
    q_session_id = st.query_params.get("session_id")
    if q_session_id:
        st.session_state.session_id = q_session_id
    else:
        new_sid = uuid.uuid4().hex[:10]
        st.session_state.session_id = new_sid
        st.query_params["session_id"] = new_sid

memory = FirestoreMemory(st.session_state.session_id)

# ── CSS: Dark streetwear aesthetic ────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700;900&display=swap');

html, body, [class*="css"] {
    font-family: 'Outfit', sans-serif;
}

/* Main background */
.stApp {
    background: linear-gradient(135deg, #0a0a0a 0%, #111827 50%, #0a0a0a 100%);
    color: #f5f5f5;
}

/* Sidebar */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #111111 0%, #1a1a2e 100%);
    border-right: 1px solid #d4af37;
}

/* Title gradient */
.hero-title {
    background: linear-gradient(135deg, #d4af37 0%, #f5d469 50%, #c9a227 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    font-size: 2.2rem;
    font-weight: 900;
    letter-spacing: -0.5px;
    margin-bottom: 0;
}

.hero-sub {
    color: #888;
    font-size: 0.9rem;
    letter-spacing: 2px;
    text-transform: uppercase;
    margin-top: 0;
}

.product-card {
    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
    border: 1px solid #d4af3730;
    border-radius: 12px;
    padding: 16px 20px;
    margin-bottom: 10px;
    transition: border-color 0.2s;
}

.product-card:hover {
    border-color: #d4af37;
}

.brand-badge {
    background: linear-gradient(90deg, #d4af37, #c9a227);
    color: #0a0a0a;
    font-weight: 700;
    font-size: 0.7rem;
    letter-spacing: 2px;
    text-transform: uppercase;
    padding: 2px 10px;
    border-radius: 99px;
    display: inline-block;
    margin-bottom: 6px;
}

.product-name { font-size: 1rem; font-weight: 700; color: #f5f5f5; margin: 4px 0; }
.product-detail { font-size: 0.8rem; color: #aaa; }
.product-price { font-size: 1.1rem; font-weight: 700; color: #d4af37; margin-top: 8px; }

/* Chat messages */
[data-testid="stChatMessage"] {
    background: #1a1a2e !important;
    border: 1px solid #d4af3720 !important;
    border-radius: 12px !important;
}

/* Input */
[data-testid="stChatInputContainer"] {
    border-top: 1px solid #d4af3740 !important;
}

/* Quick buttons */
.stButton > button {
    background: #1a1a2e !important;
    color: #d4af37 !important;
    border: 1px solid #d4af3750 !important;
    border-radius: 8px !important;
    font-family: 'Outfit', sans-serif !important;
    font-size: 0.8rem !important;
    transition: all 0.2s !important;
}
.stButton > button:hover {
    background: #d4af3715 !important;
    border-color: #d4af37 !important;
}

/* Divider gold */
hr { border-color: #d4af3730 !important; }

/* Status badge */
.status-available {
    color: #22c55e;
    font-size: 0.75rem;
    font-weight: 600;
}
</style>
""", unsafe_allow_html=True)

# ── Load RAG ──────────────────────────────────────────────────
@st.cache_resource
def load_rag():
    return RAGEngine("knowledge/sneaker_shop_kb.txt")

rag = load_rag()

# ── Load available products from Sheet ───────────────────────
def get_available_products() -> list[dict]:
    try:
        sheet = get_sheet("Products")
        records = sheet.get_all_records()
        return [p for p in records if str(p.get("สถานะ", "")).strip() != "ขายแล้ว"]
    except Exception:
        return []

# ── Sidebar ───────────────────────────────────────────────────
QUICK_COMMANDS = {
    "🕐 เวลาทำการ": "ร้านเปิดกี่โมง และมีทีมงานตอบช่วงไหนบ้าง?",
    "👟 รองเท้า Nike": "มีรองเท้า Nike อะไรบ้าง ราคาและไซส์เท่าไหร่?",
    "👞 รองเท้า Adidas": "มีรองเท้า Adidas อะไรบ้าง สภาพและราคาเป็นยังไง?",
    "🛡️ รับประกันของแท้": "รับประกันของแท้ไหม เปลี่ยนไซส์ได้ไหม?",
    "💳 ชำระเงิน": "รับชำระเงินผ่านช่องทางไหนบ้าง?",
    "📦 ค่าส่ง/จัดส่ง": "ค่าส่งเท่าไหร่ ส่งภายในกี่วัน?",
}

with st.sidebar:
    st.markdown("""
    <div style='text-align:center; padding: 12px 0 20px;'>
        <div style='font-size:2rem;'>👟</div>
        <div style='color:#d4af37; font-weight:900; font-size:1.1rem; letter-spacing:2px;'>SANDY BOT</div>
        <div style='color:#555; font-size:0.7rem; letter-spacing:3px; text-transform:uppercase;'>BITTLE SNEAKER</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("**คำถามที่พบบ่อย**")
    st.caption("กดปุ่มเพื่อถามทันที")
    for label, question in QUICK_COMMANDS.items():
        if st.button(label, key=f"quick_{label}", use_container_width=True):
            st.session_state["_quick"] = question

    st.divider()

    # สินค้าว่างในสต็อก
    st.markdown("**🔥 สินค้าในสต็อก**")
    products = get_available_products()
    if products:
        st.markdown(f"<span style='color:#22c55e; font-weight:600;'>● ว่างอยู่ {len(products)} คู่</span>", unsafe_allow_html=True)
        brands = sorted(set(str(p.get("แบรนด์", "")).strip() for p in products if p.get("แบรนด์")))
        for b in brands:
            count = sum(1 for p in products if str(p.get("แบรนด์", "")).strip() == b)
            st.markdown(f"<small style='color:#888;'>• {b}: {count} คู่</small>", unsafe_allow_html=True)
    else:
        st.caption("ไม่สามารถโหลดสต็อกได้ในขณะนี้")

    st.divider()
    if st.button("🗑️ ล้างประวัติแชท", use_container_width=True):
        memory.clear_history()
        st.session_state.messages = []
        new_sid = uuid.uuid4().hex[:10]
        st.session_state.session_id = new_sid
        st.query_params["session_id"] = new_sid
        st.rerun()

# ── Main content ──────────────────────────────────────────────
st.markdown("""
<div style='padding: 8px 0 24px;'>
    <p class='hero-title'>Sandy Bot 👟</p>
    <p class='hero-sub'>Bittle Sneaker • AI Assistant • ตอบไวตลอด 24 ชั่วโมง</p>
</div>
""", unsafe_allow_html=True)

# สินค้า Highlight
products = get_available_products()
if products:
    with st.expander(f"🔥 สินค้าว่างทั้งหมด ({len(products)} คู่) — กดเพื่อดูรายการ"):
        cols = st.columns(2)
        for i, p in enumerate(products):
            brand = str(p.get("แบรนด์", "")).strip()
            model = str(p.get("รุ่น", "")).strip()
            size_eu = str(p.get("ไซส์ EU", "")).strip()
            size_us = str(p.get("ไซส์ US", "")).strip()
            size_str = f"EU {size_eu}" if size_eu and size_eu not in ["ไม่ระบุ", "ทั่วไป"] else (f"US {size_us}" if size_us and size_us not in ["ไม่ระบุ", "ทั่วไป"] else "")
            condition = str(p.get("สภาพ", "")).strip()
            price = str(p.get("ราคาขาย", "")).strip()
            has_box = str(p.get("มีกล่อง", "")).strip()

            with cols[i % 2]:
                box_icon = "📦" if has_box == "มีกล่อง" else ""
                st.markdown(f"""
                <div class='product-card'>
                    <span class='brand-badge'>{brand}</span>
                    <div class='product-name'>{model}</div>
                    <div class='product-detail'>{size_str} • สภาพ {condition} {box_icon}</div>
                    <div class='product-price'>฿{price}</div>
                </div>
                """, unsafe_allow_html=True)

st.divider()

# ── Chat ──────────────────────────────────────────────────────
if "messages" not in st.session_state:
    history = memory.get_history()
    if history:
        st.session_state.messages = []
        for msg in history:
            st.session_state.messages.append({
                "role": msg["role"],
                "content": msg["content"],
                "images": msg.get("images", [])
            })
    else:
        st.session_state.messages = []
        welcome_msg = "สวัสดีค่ะ! 👋 หนูคือ Sandy บอทผู้ช่วยของ Bittle Sneaker นะคะ\nถามเรื่องรองเท้า ราคา ไซส์ สภาพ การส่งของ หรือนโยบายร้านได้เลยค่า~ 👟✨"
        st.session_state.messages.append({
            "role": "assistant",
            "content": welcome_msg
        })
        memory.save_message("assistant", welcome_msg)

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])
        if "images" in msg and msg["images"]:
            from collections import defaultdict
            images_by_code = defaultdict(list)
            for img in msg["images"]:
                if isinstance(img, dict) and "image_bytes" in img:
                    images_by_code[img["code"]].append(img)
            
            for code, imgs in images_by_code.items():
                if len(imgs) == 1:
                    st.image(imgs[0]["image_bytes"], caption=f"📸 รูปสินค้า {code}", use_container_width=True)
                else:
                    st.markdown(f"**📸 รูปสินค้า {code} ({len(imgs)} รูป):**")
                    cols = st.columns(min(len(imgs), 3))
                    for idx, img in enumerate(imgs):
                        with cols[idx % 3]:
                            st.image(img["image_bytes"], caption=f"มุมที่ {idx + 1}", use_container_width=True)

quick = st.session_state.pop("_quick", None)
prompt = st.chat_input("ถามเรื่องรองเท้า ราคา หรือนโยบายร้านได้เลยค่า~ 👟") or quick

if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.write(prompt)

    memory.save_message("user", prompt)
    write_trace("user_input", {"source": "customer_web", "message": prompt})

    # RAG — ค้นหาข้อมูลจาก knowledge base + Products sheet
    context_chunks = rag.search(prompt, top_k=4)
    write_trace("rag_search", {"query": prompt, "chunks_found": len(context_chunks)})
    context = "\n---\n".join(context_chunks)

    # ค้นหารูปภาพสินค้าใน Google Drive ล่วงหน้าก่อนที่จะตอบคำถาม
    import re
    
    # ดึงรหัสสินค้าทั้งหมดที่ถูกอ้างถึงในข้อความแชทล่าสุดของลูกค้า และในเนื้อหา RAG Context
    codes = re.findall(r'[A-Za-z]{2}-\d{3}', prompt + "\n" + context)
    unique_codes = sorted(list(set(code.upper() for code in codes)))
    
    image_results = []
    image_status_lines = []
    
    with st.spinner("Sandy กำลังค้นหาข้อมูลและรูปภาพสินค้า..."):
        for code in unique_codes:
            results = find_product_images(code)
            if results:
                image_status_lines.append(f"- รหัสสินค้า {code}: มีรูปภาพจริงพร้อมแสดงจำนวน {len(results)} รูป")
                for idx, result in enumerate(results):
                    image_results.append({
                        "code": code,
                        "image_bytes": result["bytes"],
                        "name": result["name"],
                        "index": idx + 1,
                        "url": result.get("url", "")
                    })
            else:
                image_status_lines.append(f"- รหัสสินค้า {code}: ไม่มีรูปภาพจริงในระบบ Google Drive")
                
    image_status_text = "\n".join(image_status_lines) if image_status_lines else "ไม่มีการอ้างถึงรหัสสินค้าใดๆ ในการค้นหานี้"

    # จัดเตรียมบทสนทนาประวัติย้อนหลังทั้งหมดให้ Gemini
    contents = []
    for msg in st.session_state.messages[:-1]:
        contents.append({
            "role": "user" if msg["role"] == "user" else "model",
            "parts": [{"text": msg["content"]}]
        })
    
    # เทิร์นล่าสุด แนบ Context จาก RAG และสถานะรูปภาพจริงเข้าประกอบ
    latest_prompt = f"""ข้อมูลประกอบการตอบคำถาม (ใช้เฉพาะข้อมูลนี้เท่านั้น):
{context}

[สถานะรูปภาพจริงของสินค้าในระบบ]:
{image_status_text}

คำถามล่าสุดของผู้ใช้: {prompt}"""
    
    contents.append({
        "role": "user",
        "parts": [{"text": latest_prompt}]
    })

    system_instruction = """คุณคือ Sandy Bot ผู้ช่วย AI น่ารักของร้าน Bittle Sneaker ร้านรองเท้ามือสองแบรนด์เนมของแท้
พูดด้วยน้ำเสียงเป็นกันเอง อบอุ่น ใช้ภาษาวัยรุ่นเล็กน้อย มีหางเสียง (คะ/ค่ะ/ค่า) แต่ยังคงความเป็นมืออาชีพและสุภาพ
ตอบเฉพาะจากข้อมูลประกอบการตอบคำถามที่ได้รับเท่านั้น ถ้าไม่พบข้อมูล ให้ตอบสุภาพว่าไม่ทราบ และแนะนำให้ลูกค้าทักแอดมินที่ Line OA: @bittlesneaker
ห้ามแต่งราคา ห้ามแต่งไซส์ สภาพ หรือแต่งข้อมูลสินค้าปลอมขึ้นมาเองโดยเด็ดขาด
ห้ามส่งรูปให้ลูกค้าเอง จนกว่าลูกค้าจะขอดูสินค้าชิ้นนั้นๆด้วยตัวเอง ห้ามนำรูปสินค้าตัวอื่นส่งไปเด็ดขาด

[การจัดการกรณีสินค้ามีจำนวนมาก]:
หากรองเท้าที่มีในผลการค้นหา (RAG Context) มีจำนวนมากเกินไป (มากกว่า 3 คู่ขึ้นไป) ห้ามลิสต์รายชื่อรองเท้าทั้งหมดให้ลูกค้าในคราวเดียว เพราะจะทำให้สับสน ให้คุณเลือกมาแนะนำเพียง 2-3 คู่ที่น่าสนใจที่สุดหรือตรงความต้องการมากที่สุดก่อน จากนั้นให้ถามคำถามเพิ่มเติมอย่างใส่ใจและน่ารัก (เช่น ถามไซส์ รุ่น หรือโทนสีที่ตามหาเป็นพิเศษ) เพื่อช่วยสโคป (scope) และกรองผลลัพธ์สินค้าให้แคบลงและตรงใจลูกค้ามากยิ่งขึ้น

[ข้อมูลเพิ่มเติมเรื่องรูปภาพ]:
ระบบของเราเชื่อมต่อกับ Google Drive และคุณสามารถตรวจสอบ [สถานะรูปภาพจริงของสินค้าในระบบ] ได้จากข้อมูลประกอบการตอบคำถาม:
1. หากสินค้าคู่นั้นระบุว่า "มีรูปภาพจริงพร้อมแสดง" ให้บอกลูกค้าอย่างน่ารักว่า "หนูได้ดึงรูปภาพจริงของคู่ [รหัสสินค้า] มาแสดงให้ชมที่ด้านล่างเรียบร้อยแล้วนะคะ!" เสมอ
2. หากสินค้าคู่นั้นระบุว่า "ไม่มีรูปภาพจริงในระบบ Google Drive" หรือไม่มีรูปภาพเด็ดขาด ห้ามบอกว่าจะแสดงรูปภาพด้านล่างหรือบอกจะส่งให้เด็ดขาด! ให้แจ้งลูกค้าอย่างสุภาพและจริงใจว่า "ขออภัยด้วยนะคะ ตอนนี้คู่ [รหัสสินค้า] ยังไม่มีรูปภาพจริงในระบบค่ะ หากคุณลูกค้าต้องการดูรูปภาพเพิ่มเติม สามารถทักหาแอดมินที่ Line OA: @bittlesneaker เพื่อให้แอดมินช่วยถ่ายรูปส่งให้ได้เลยนะคะ!"
3. หากลูกค้าถามหาสินค้าทั่วไปหรือขอรูปแต่ในระบบไม่ได้อ้างถึงรหัสสินค้าใดๆ ให้ตอบอย่างสุภาพว่าไม่มีรูปภาพในระบบ และแนะนำให้สอบถามแอดมินทาง Line OA: @bittlesneaker เช่นเดียวกัน"""

    with st.chat_message("assistant"):
        with st.spinner("Sandy กำลังคิดคำตอบ..."):
            try:
                response = client.models.generate_content(
                    model=MODEL,
                    contents=contents,
                    config={
                        "system_instruction": system_instruction,
                        "temperature": 0.4
                    }
                )
                answer = response.text
            except Exception as e:
                answer = "ขออภัยค่ะ ระบบขัดข้องชั่วคราว กรุณาลองใหม่อีกครั้งนะคะ 🙏\nหรือทักแอดมินได้ที่ Line OA: @bittlesneaker"
                write_trace("api_error", {"source": "customer_web", "error": str(e)})

        st.write(answer)
        
        # กรองแสดงเฉพาะภาพสินค้าที่รหัสสินค้าถูกระบุอยู่ในคำตอบของ AI เท่านั้น และลูกค้าต้องขอดูรูปภาพด้วยตัวเอง
        filtered_image_results = []
        
        # ตรวจสอบว่าลูกค้ามีเจตนาขอดูรูปภาพจริงหรือไม่
        image_keywords = ["รูป", "ภาพ", "ดู", "เห็น", "โชว์", "ขอดู", "ขอรูป", "ส่งรูป", "รูปจริง", "มีรูป", "ขอดูสินค้า", "ขอดูรูปสินค้า", "มีรูปไหม", "ขอดูหน่อย"]
        ask_for_images = any(kw in prompt for kw in image_keywords)
        
        if ask_for_images and image_results:
            mentioned_codes = re.findall(r'[A-Za-z]{2}-\d{3}', answer)
            mentioned_codes_upper = set(c.upper() for c in mentioned_codes)
            filtered_image_results = [img for img in image_results if img["code"].upper() in mentioned_codes_upper]
            
        # แสดงภาพสินค้าจาก Google Drive ที่ผ่านการกรองแล้ว
        if filtered_image_results:
            from collections import defaultdict
            images_by_code = defaultdict(list)
            for img in filtered_image_results:
                images_by_code[img["code"]].append(img)
            
            for code, imgs in images_by_code.items():
                if len(imgs) == 1:
                    st.image(imgs[0]["image_bytes"], caption=f"📸 รูปสินค้า {code}", use_container_width=True)
                else:
                    st.markdown(f"**📸 รูปสินค้า {code} ({len(imgs)} รูป):**")
                    cols = st.columns(min(len(imgs), 3))
                    for idx, img in enumerate(imgs):
                        with cols[idx % 3]:
                            st.image(img["image_bytes"], caption=f"มุมที่ {idx + 1}", use_container_width=True)

    # บันทึกประวัติ (ไม่บันทึก bytes ลง Firestore เพราะใหญ่เกินไป)
    memory.save_message("assistant", answer)
    write_trace("rag_response", {"source": "customer_web", "answer": answer})
    st.session_state.messages.append({"role": "assistant", "content": answer, "images": filtered_image_results})

