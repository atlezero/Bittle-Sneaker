import os

from dotenv import load_dotenv
from google import genai

load_dotenv()

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

    response = client.models.generate_content(
        model=MODEL,
        contents=prompt,
    )

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