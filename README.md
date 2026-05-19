---
title: Milk On The Beach
emoji: 🧋
colorFrom: yellow
colorTo: red
sdk: streamlit
sdk_version: "1.57.0"
python_version: "3.11"
app_file: app.py
pinned: false
---

# 🧋 Milk On The Beach — AI Chatbot สำหรับร้านเครื่องดื่ม

ระบบ AI Chatbot ผู้ช่วยร้านเครื่องดื่ม **Milk On The Beach** พัฒนาด้วย Streamlit + Gemini API + RAG  
ช่วยให้ลูกค้าถามข้อมูลร้าน เมนู ราคา โปรโมชัน และบริการต่าง ๆ ได้ทันทีผ่านหน้าเว็บ

> 📖 อ่าน thinking process ของโปรเจกต์ได้ที่ [PIVOT.md](PIVOT.md)

## 🌐 Live Demo

🔗 **[https://huggingface.co/spaces/atlez/milk-on-the-beach](https://huggingface.co/spaces/atlez/milk-on-the-beach)**

## ✨ ฟีเจอร์หลัก

| ฟีเจอร์ | รายละเอียด |
|---|---|
| 🧋 **Milky Bot** | Chatbot ตอบคำถามลูกค้าจากข้อมูลร้านด้วย RAG + Gemini |
| 📊 **บันทึกยอดขาย** | บันทึกยอดขายลง Google Sheets ผ่าน CLI |
| 📈 **สรุปรายงาน** | สรุปยอดขายเมื่อวานส่ง Telegram อัตโนมัติทุกเช้า |
| 🕐 **คำสั่งลัด** | ปุ่ม shortcut ถามคำถามยอดฮิตได้ทันที |
| 📝 **Trace Log** | บันทึกทุกการสนทนาลง `agent_trace.log` |

## 🏗️ โครงสร้างโปรเจกต์

```text
.
├── app.py                      # Streamlit chatbot UI
├── features/
│   ├── agent_harness.py        # Agent orchestrator + Gemini
│   ├── agent_tools.py          # Tools: log_sale, get_sales_today
│   ├── rag_engine.py           # RAG engine (TF-IDF based)
│   ├── morning_report.py       # สรุปยอดขาย → Telegram
│   ├── sales_logger.py         # CLI บันทึกยอดขาย
│   ├── sheets_client.py        # Google Sheets client
│   └── caption_gen.py          # สร้าง caption ด้วย Gemini
├── knowledge/
│   └── milkonthebeach_kb.txt   # Knowledge base ของร้าน
├── tests/                      # Unit tests
├── .github/workflows/
│   ├── deploy.yml              # Auto deploy → HF Spaces
│   └── morning_report.yml      # Cron job ส่งรายงานเช้า
├── PIVOT.md                    # Thinking process
└── requirements.txt
```

## 🚀 วิธีรันในเครื่อง (Local Setup)

### 1. Clone และสร้าง Virtual Environment

```bash
git clone https://github.com/atlezero/milk-on-the-beach.git
cd milk-on-the-beach
python -m venv .venv
```

### 2. Activate Environment

```bash
# Windows (PowerShell)
.\.venv\Scripts\Activate.ps1

# Windows (CMD)
.venv\Scripts\activate.bat

# macOS / Linux
source .venv/bin/activate
```

### 3. ติดตั้ง Dependencies

```bash
pip install -r requirements.txt
```

### 4. ตั้งค่า Environment Variables

สร้างไฟล์ `.env` ที่ root ของโปรเจกต์:

```env
GOOGLE_API_KEY=<your-gemini-api-key>
GOOGLE_SHEETS_ID=<your-google-sheets-id>
GOOGLE_SERVICE_ACCOUNT_FILE=./service-account.json
TELEGRAM_BOT_TOKEN=<your-telegram-bot-token>
TELEGRAM_CHAT_ID=<your-telegram-chat-id>
```

### 5. รัน Streamlit

```bash
streamlit run app.py
```

เปิด http://localhost:8501 ในเบราว์เซอร์ได้เลย

## 🧪 รัน Tests

```bash
pytest
```

อ่านรายละเอียดเพิ่มได้ที่ [docs/TESTING.md](docs/TESTING.md)

## ⏰ เวลา

วันที่บันทึกยอดขายและวันที่ในรายงานใช้เวลาไทย `UTC+7`

## 🔒 ไฟล์ที่ไม่ควร commit

- `.env` — API keys
- `service-account.json` — Google credentials
- `.venv/` — Virtual environment
- `agent_trace.log` — Trace logs




## Demo Day Self-Check

- [x] Deploy URL ใช้งานได้ (เปิดทดสอบล่าสุด: 19/5/2569 T 15:30 น.)
- [x] ไม่มี `.env` หรือ `*.json` ใน git history
- [x] PIVOT.md ครบ 3 ข้อ
- [x] README อธิบายระบบของ domain ตัวเอง
- [x] knowledge base, prompt, UI ปรับเป็น domain ใหม่หมดแล้ว