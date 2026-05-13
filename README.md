# milk-on-the-beach

เครื่องมือเล็ก ๆ สำหรับบันทึกยอดขายลง Google Sheets, สรุปรายงานยอดขาย, ส่งรายงานไป Telegram และสร้าง caption สินค้าด้วย Gemini

## โครงสร้างโปรเจกต์

```text
.
├── features/
│   ├── caption_gen.py          # สร้าง caption สินค้าด้วย Gemini
│   ├── morning_report.py       # สรุปยอดขายและส่ง Telegram
│   ├── sales_logger.py         # CLI สำหรับเพิ่มยอดขายลง Google Sheets
│   └── sheets_client.py        # Google Sheets client
├── requirements.txt            # Python dependencies
├── pytest.ini                  # pytest configuration
├── docs/
│   └── TESTING.md              # วิธีรันและดูแล unit tests
└── tests/
    ├── conftest.py
    ├── test_caption_gen.py
    ├── test_morning_report.py
    ├── test_sales_logger.py
    └── test_sheets_client.py
```

## ติดตั้ง

```bash
pip install -r requirements.txt
```

## รัน tests

```bash
pytest
```

อ่านรายละเอียดเพิ่มได้ที่ [docs/TESTING.md](docs/TESTING.md)

## เวลา

วันที่บันทึกยอดขายและวันที่ในรายงานใช้เวลาไทย `UTC+7`

## ไฟล์ local ที่ไม่ควร commit

- `.env`
- `service-account.json`
- `.venv/`
- `__pycache__/`
- `.pytest_cache/`
