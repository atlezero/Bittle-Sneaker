# Unit Tests

โปรเจกต์นี้ใช้ `pytest` สำหรับ unit tests

## ติดตั้ง dependencies

```bash
pip install -r requirements.txt
```

## รัน tests

รันทั้งหมด:

```bash
pytest
```

รันเฉพาะไฟล์:

```bash
pytest tests/test_sheets_client.py
pytest tests/test_sales_logger.py
pytest tests/test_morning_report.py
pytest tests/test_caption_gen.py
```

รันพร้อม coverage:

```bash
pytest --cov=. --cov-report=html
```

## CLI regression tests

`tests/test_cli_scripts.py` รันสคริปต์ด้วย `subprocess` จากโฟลเดอร์ `features/` เหมือนใช้งานจริง เช่น:

```bash
cd features
python sales_logger.py "กาแฟ:2:45"
python morning_report.py
```

test กลุ่มนี้ตั้งค่า environment ปลอมเพื่อไม่ยิง Google Sheets หรือ Telegram จริง แต่ยังจับปัญหา import path, current working directory และ bootstrap ของ CLI ได้

## Timezone

logic วันที่ของ `sales_logger.py` และ `morning_report.py` ใช้เวลาไทย `UTC+7` และมี assertion ใน test ว่าต้องเรียก `datetime.now(THAI_TZ)`

## Integration test กับ Google Sheets

มี test ที่ append row จริงลง worksheet ชื่อ `test` ใน Google Sheet ID เดียวกัน แล้วอ่านข้อมูลกลับมายืนยัน:

```bash
pytest tests/test_sheets_client.py -m integration
```

ต้องตั้งค่า credentials ใน `.env` หรือ environment ก่อนรัน:

```bash
GOOGLE_SHEETS_ID=<spreadsheet-id>
GOOGLE_SERVICE_ACCOUNT_FILE=service-account.json
```

ถ้าต้องการให้โค้ดหลักเขียนลง worksheet ชื่อ `test` โดยไม่ส่งชื่อ worksheet เข้า `get_sheet()` โดยตรง ให้ตั้งค่า:

```bash
GOOGLE_SHEETS_WORKSHEET=test
```

## โครงสร้าง

```text
tests/
├── __init__.py
├── conftest.py              # Shared fixtures
├── test_caption_gen.py      # Tests for Gemini caption generation
├── test_cli_scripts.py      # Regression tests for real CLI execution paths
├── test_morning_report.py   # Tests for sales summary and Telegram
├── test_sales_logger.py     # Tests for sales logging CLI
└── test_sheets_client.py    # Tests for Google Sheets client
```

## Coverage หลัก

- `caption_gen.py`: สร้าง caption ด้วย Gemini AI
- `morning_report.py`: สรุปยอดขายรายวันและส่ง Telegram
- `sales_logger.py`: parse รายการขายและบันทึกยอดขาย
- `sheets_client.py`: เชื่อมต่อ Google Sheets API

## CI/CD

ตัวอย่าง step สำหรับ GitHub Actions:

```yaml
- name: Run tests
  run: |
    pip install -r requirements.txt
    pytest
```
