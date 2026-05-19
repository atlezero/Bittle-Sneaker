# app.py
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

# ── Page config (ต้องเป็นคำสั่งแรกสุด) ─────────────────────
_logo = Image.open(PROJECT_ROOT / "pictures" / "logo.png")
st.set_page_config(
    page_title="Milk On The Beach",
    page_icon=_logo,
    layout="centered",
)

from features.rag_engine import RAGEngine
from features.agent_harness import write_trace

load_dotenv()
client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
MODEL = "gemini-3.1-flash-lite-preview"


@st.cache_resource
def load_rag():
    return RAGEngine("knowledge/milkonthebeach_kb.txt")


rag = load_rag()

# ─────────────────────────────────────────────────────────────
# Sidebar — คำสั่งลัด
# ─────────────────────────────────────────────────────────────

QUICK_COMMANDS = {
    "🕐 เวลาเปิด-ปิด": "ร้านเปิดกี่โมงถึงกี่โมง?",
    "☕ เมนูกาแฟ": "มีเมนูกาแฟอะไรบ้าง?",
    "🧋 เมนูชาและนม": "มีเมนูชาและนมอะไรบ้าง?",
    "💳 วิธีชำระเงิน": "รับชำระเงินแบบไหนบ้าง?",
    "🎁 โปรโมชัน": "มีโปรโมชันอะไรบ้าง?",
    "📦 บริการจัดส่ง": "มีบริการส่งอาหารไหม?",
    "📞 ติดต่อร้าน": "ติดต่อร้านได้ที่ไหน?",
}

with st.sidebar:
    st.markdown("## 🧋 Milky Bot — คำสั่งลัด")
    st.caption("กดปุ่มเพื่อถามทันที ไม่ต้องพิมพ์เอง")

    for label, question in QUICK_COMMANDS.items():
        if st.button(label, key=f"quick_{label}", use_container_width=True):
            st.session_state["_quick"] = question

    st.divider()
    if st.button("🗑️ ล้างประวัติ", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

# ─────────────────────────────────────────────────────────────
# Main chat
# ─────────────────────────────────────────────────────────────

st.title("🥛 Milky Bot ผู้ช่วย AI ของ Milk On The Beach")
st.caption("ถามเรื่องเมนู เวลาเปิด หรือข้อมูลร้านได้เลย")

if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

# รับคำถามจากปุ่มลัด หรือจาก chat input
quick = st.session_state.pop("_quick", None)
prompt = st.chat_input("ถามอะไรเกี่ยวกับร้านได้เลย...") or quick

if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.write(prompt)

    # 📝 บันทึก trace: คำถามจาก user
    write_trace("user_input", {"source": "web", "message": prompt})

    # RAG: ค้นหา context ที่เกี่ยวข้อง
    context_chunks = rag.search(prompt, top_k=3)
    write_trace("rag_search", {"query": prompt, "chunks_found": len(context_chunks)})
    context = "\n---\n".join(context_chunks)

    # Generate คำตอบ
    full_prompt = f"""คุณคือ Milky Bot ผู้ช่วย AI ของร้าน Milk On The Beach ตอบเฉพาะจากข้อมูลด้านล่าง
ถ้าไม่พบข้อมูล ให้บอกว่าไม่ทราบ อย่าแต่งข้อมูลเอง

ข้อมูลร้าน:
{context}

คำถาม: {prompt}
"""
    try:
        response = client.models.generate_content(model=MODEL, contents=full_prompt)
        answer = response.text
    except Exception as e:
        answer = "ขออภัยค่ะ ระบบขัดข้องชั่วคราว กรุณาลองใหม่อีกครั้งนะคะ 🙏"
        write_trace("api_error", {"source": "web", "error": str(e)})

    # 📝 บันทึก trace: คำตอบจาก AI
    write_trace("rag_response", {"source": "web", "answer": answer})

    st.session_state.messages.append({"role": "assistant", "content": answer})
    with st.chat_message("assistant"):
        st.write(answer)