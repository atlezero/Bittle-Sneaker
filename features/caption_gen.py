import os
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception

# ── Path setup ────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

# ─────────────────────────────────────────────────────────────
# Gemini setup
# ─────────────────────────────────────────────────────────────

client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY")
)

MODEL = "gemini-3.1-flash-lite-preview"


# ─────────────────────────────────────────────────────────────
# Generate captions
# ─────────────────────────────────────────────────────────────

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception(lambda e: "503" in str(e) or "UNAVAILABLE" in str(e).upper()),
    reraise=True
)
def _call_gemini_caption(prompt):
    return client.models.generate_content(
        model=MODEL,
        contents=prompt,
    )


def generate_captions(product_name: str, price: int) -> str:

    prompt = f"""
    เขียนแคปชั่นขายของภาษาไทย

    สินค้า: {product_name}
    ราคา: {price} บาท

    เงื่อนไข:
    - Cute ต้องน่ารัก
    - Minimal ต้องสั้น คลีน
    - Gen-Z ต้องวัยรุ่น สนุก

    รูปแบบการตอบ (ห้ามเปลี่ยน):

    Cute: <ข้อความ>

    Minimal: <ข้อความ>

    Gen-Z: <ข้อความ>
    """

    response = _call_gemini_caption(prompt)

    return response.text.strip()


# ─────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────

if __name__ == "__main__":

    result = generate_captions(
        product_name="เสื้อยืด oversize สีดำ",
        price=299,
    )

    print(result)