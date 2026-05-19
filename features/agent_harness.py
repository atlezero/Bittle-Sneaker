# agent_harness.py

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from dotenv import load_dotenv
from google import genai
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception

# ── Path setup ────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))
load_dotenv(PROJECT_ROOT / ".env")

from features.agent_tools import TOOLS

# ─────────────────────────────────────────────────────────────
# Gemini setup
# ─────────────────────────────────────────────────────────────

client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY")
)

MODEL = "gemini-3.1-flash-lite-preview"

THAI_TZ = ZoneInfo("Asia/Bangkok")


# ─────────────────────────────────────────────────────────────
# System instruction
# ─────────────────────────────────────────────────────────────

SYSTEM_INSTRUCTION = """
คุณคือ Milky ผู้ช่วย AI ของร้าน Milk on the Beach
หน้าที่ของคุณคือแปลงคำสั่งภาษาไทยเป็น JSON action

ตอบกลับเป็น JSON เท่านั้น

รูปแบบ:

{"action": "log_sale", "args": {"menu": "...", "quantity": N, "price": N}}

ถ้าต้องการสรุปยอดขายวันนี้:

{"action": "get_sales_today", "args": {}}

ถ้าคำสั่งไม่เกี่ยวข้อง:

{"action": "unknown", "args": {}}
"""


# ─────────────────────────────────────────────────────────────
# Trace log
# ─────────────────────────────────────────────────────────────

TRACE_FILE = str(PROJECT_ROOT / "agent_trace.log")


def write_trace(
    event: str,
    data: dict,
) -> None:

    with open(
        TRACE_FILE,
        "a",
        encoding="utf-8",
    ) as f:

        record = {
            "timestamp": datetime.now(
                THAI_TZ
            ).isoformat(),

            "event": event,

            **data,
        }

        f.write(
            json.dumps(
                record,
                ensure_ascii=False,
            ) + "\n"
        )


# ─────────────────────────────────────────────────────────────
# Parse JSON response
# ─────────────────────────────────────────────────────────────

def parse_action_response(raw: str) -> dict:
    """
    Parse JSON even if wrapped in markdown
    """

    text = raw.strip()

    if text.startswith("```"):

        lines = text.splitlines()

        if lines and lines[0].startswith("```"):
            lines = lines[1:]

        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]

        text = "\n".join(lines).strip()

    return json.loads(text)


# ─────────────────────────────────────────────────────────────
# Format sales summary
# ─────────────────────────────────────────────────────────────

def format_sales_today(result: dict) -> str:
    total = result.get("total_revenue", 0.0)
    count = result.get("total_items", 0)
    summary = result.get("menu_summary", {})

    if not summary:
        return "📊 ยังไม่มียอดขายสำหรับวันนี้ค่ะ"

    lines = ["📊 **สรุปยอดขายวันนี้**", "---"]

    # รายละเอียดแต่ละเมนู
    for menu, data in summary.items():
        lines.append(f"• {menu}: {data['quantity']} แก้ว (รวม {data['total']:.2f} บาท)")

    lines.append("---")
    lines.append(f"💰 **ยอดรวมทั้งหมด:** {total:.2f} บาท")
    lines.append(f"🥤 **จำนวนรวม:** {count} แก้ว")

    # หาเมนูขายดี (ตามจำนวน)
    best_qty_menu = max(summary, key=lambda m: summary[m]["quantity"], default=None)
    if best_qty_menu:
        lines.append(f"🏆 **ขายดีที่สุด:** {best_qty_menu} ({summary[best_qty_menu]['quantity']} แก้ว)")

    if len(summary) > 1:
        min_qty = min(data["quantity"] for data in summary.values())
        least_qty_menus = sorted([m for m, data in summary.items() if data["quantity"] == min_qty])
        least_menu_str = ", ".join(least_qty_menus)
        lines.append(f"📉 **ขายได้น้อยที่สุด:** {least_menu_str} ({min_qty} แก้ว)")

    return "\n".join(lines)



# ─────────────────────────────────────────────────────────────
# Main agent
# ─────────────────────────────────────────────────────────────

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception(lambda e: "503" in str(e) or "UNAVAILABLE" in str(e).upper()),
    reraise=True
)
def _call_gemini(prompt):
    return client.models.generate_content(
        model=MODEL,
        contents=prompt,
        config={
            "system_instruction": SYSTEM_INSTRUCTION,
            "response_mime_type": "application/json",
        },
    )


def run_agent(
    user_input: str,
) -> str:

    write_trace(
        "user_input",
        {"message": user_input},
    )

    try:
        response = _call_gemini(user_input)

    except Exception as e:

        write_trace(
            "llm_error",
            {"error": str(e)},
        )

        return f"❌ Gemini API Error: {e}"

    raw = response.text.strip()

    write_trace(
        "llm_response",
        {"raw": raw},
    )

    try:
        action_data = parse_action_response(raw)
    except json.JSONDecodeError as e:
        write_trace("parse_error", {"raw": raw, "error": str(e)})
        return "❌ AI ตอบกลับในรูปแบบที่ไม่ถูกต้อง"

    # แปลงให้เป็น list เสมอเพื่อความง่ายในการวนลูป
    if isinstance(action_data, dict):
        actions = [action_data]
    elif isinstance(action_data, list):
        actions = action_data
    else:
        return "❌ AI ตอบกลับด้วยข้อมูลที่ไม่รองรับ"

    results_text = []

    for item in actions:
        action = item.get("action")
        args = item.get("args", {})

        if action not in TOOLS:
            write_trace("unknown_action", {"action": action})
            results_text.append(f"⚠️ ไม่รู้จัก action: {action}")
            continue

        try:
            result = TOOLS[action](**args)
            write_trace("tool_result", {"action": action, "args": args, "result": result})

            if action == "log_sale":
                results_text.append(
                    f"✅ บันทึกสำเร็จ: {result['menu']} "
                    f"{result['quantity']} แก้ว (รวม {result['total']} บาท)"
                )
            elif action == "get_sales_today":
                results_text.append(format_sales_today(result))
            else:
                results_text.append(f"✅ ทำการ {action} สำเร็จ")

        except Exception as e:
            write_trace("tool_error", {"action": action, "args": args, "error": str(e)})
            results_text.append(f"❌ เกิดข้อผิดพลาดใน {action}: {e}")

    return "\n".join(results_text)


# ─────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────

if __name__ == "__main__":

    print(
        "Milky Agent พร้อมรับคำสั่ง "
        "(พิมพ์ 'exit' เพื่อออก)\n"
    )

    while True:

        user_input = input(
            "คุณ: "
        ).strip()

        if user_input.lower() == "exit":
            break

        result = run_agent(user_input)

        print(f"Milky: {result}\n")