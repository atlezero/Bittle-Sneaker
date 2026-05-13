import os
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()

def generate_captions(product_name, price):
    prompt = f"""
    เขียนแคปชั่นขายของภาษาไทย

    สินค้า: {product_name}
    ราคา: {price} บาท

    รูปแบบการตอบ (ห้ามเปลี่ยน):
    Cute: <ข้อความ>
    Minimal: <ข้อความ>
    Gen-Z: <ข้อความ>
    """

    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
    model = genai.GenerativeModel("gemini-3.1-flash-lite-preview")
    response = model.generate_content(prompt)
    return response.text.strip()

if __name__ == "__main__":
    print(generate_captions("เสื้อยืด oversize สีดำ", 299))
