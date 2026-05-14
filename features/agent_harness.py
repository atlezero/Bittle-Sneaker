# agent_harness.py

import json
import os
from datetime import datetime
from zoneinfo import ZoneInfo

from dotenv import load_dotenv
from google import genai

from features.agent_tools import TOOLS

load_dotenv()

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

TRACE_FILE = "agent_trace.log"


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

def format_sales_today(
    result: dict,
) -> str:

    total = result.get(
        "total_revenue",
        0.0,
    )

    count = result.get(
        "total_items",
        0,
    )

    summary = result.get(
        "menu_summary",
        {},
    )

    best = max(
        summary,
        key=lambda m: summary[m]["total"],
        default=None,
    )

    best_part = (
        f" | เมนูทำเงินสูงสุด: "
        f"{best} "
        f"({summary[best]['total']:.0f} บาท)"
        if best else ""
    )

    return (
        f"📊 ยอดขายวันนี้: "
        f"{total:.2f} บาท "
        f"({count} รายการ)"
        f"{best_part}"
    )


# ─────────────────────────────────────────────────────────────
# Main agent
# ─────────────────────────────────────────────────────────────

def run_agent(
    user_input: str,
) -> str:

    write_trace(
        "user_input",
        {"message": user_input},
    )

    try:

        response = client.models.generate_content(
            model=MODEL,
            contents=(
                f"{SYSTEM_INSTRUCTION}\n\n"
                f"คำสั่ง: {user_input}"
            ),
        )

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

        action_data = parse_action_response(
            raw
        )

    except json.JSONDecodeError as e:

        write_trace(
            "parse_error",
            {
                "raw": raw,
                "error": str(e),
            },
        )

        return (
            "❌ AI ตอบกลับ"
            "ในรูปแบบที่ไม่ถูกต้อง"
        )

    action = action_data.get("action")

    args = action_data.get(
        "args",
        {},
    )

    if action not in TOOLS:

        write_trace(
            "unknown_action",
            {"action": action},
        )

        return (
            f"⚠️ ไม่รู้จัก action: "
            f"{action}"
        )

    try:

        result = TOOLS[action](**args)

        write_trace(
            "tool_result",
            {
                "action": action,
                "result": result,
            },
        )

        if action == "log_sale":

            return (
                f"✅ บันทึกสำเร็จ: "
                f"{result['menu']} "
                f"x{result['quantity']} "
                f"= {result['total']} บาท"
            )

        if action == "get_sales_today":

            return format_sales_today(
                result
            )

        return f"✅ ผลลัพธ์: {result}"

    except (
        ValueError,
        TypeError,
        FileNotFoundError,
    ) as e:

        write_trace(
            "tool_error",
            {
                "action": action,
                "error": str(e),
            },
        )

        return (
            f"❌ ข้อมูลไม่ถูกต้อง: {e}"
        )


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