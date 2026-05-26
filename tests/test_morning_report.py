import pytest
from datetime import datetime, timezone
from unittest.mock import Mock, patch

import requests

from features.morning_report import (
    THAI_TZ,
    build_summary,
    find_column,
    parse_date,
    send_telegram_message,
)


class TestParseDate:
    def test_parse_yyyy_mm_dd(self):
        result = parse_date("2024-01-13")
        assert str(result) == "2024-01-13"

    def test_parse_dd_mm_yyyy(self):
        result = parse_date("13/01/2024")
        assert str(result) == "2024-01-13"

    def test_parse_dd_mm_yyyy_dash(self):
        result = parse_date("13-01-2024")
        assert str(result) == "2024-01-13"

    def test_invalid_date(self):
        with pytest.raises(ValueError):
            parse_date("มั่วๆ")


class TestFindColumn:
    def test_find_date_column(self):
        headers = ["วันที่", "เมนู", "ยอดรวม"]
        result = find_column(headers, ["date", "วันที่"])
        assert result == 0

    def test_find_menu_column(self):
        headers = ["date", "menu", "total"]
        result = find_column(headers, ["menu", "เมนู"])
        assert result == 1

    def test_column_not_found(self):
        headers = ["a", "b", "c"]
        result = find_column(headers, ["price"])
        assert result is None


class TestBuildSummary:
    @patch("features.morning_report.datetime")
    def test_build_summary_with_data(self, mock_datetime):
        # Mock datetime.now(THAI_TZ)
        mock_now = datetime(2024, 1, 14, 8, 0, 0, tzinfo=THAI_TZ)
        mock_datetime.now.return_value = mock_now
        mock_datetime.fromisoformat.side_effect = datetime.fromisoformat
        mock_datetime.strptime.side_effect = datetime.strptime

        rows = [
            ["วันที่", "เมนู", "จำนวน", "ราคา", "ยอดรวม"],
            ["2024-01-13T10:00:00+07:00", "Nike", "2", "150", "300"],
            ["2024-01-13T11:00:00+07:00", "Adidas", "1", "290", "290"],
            ["2024-01-13T12:00:00+07:00", "Nike", "1", "150", "150"],
        ]

        result = build_summary(rows)

        mock_datetime.now.assert_called_once_with(THAI_TZ)
        assert "สรุปยอดขายรองเท้าเมื่อวันวานน้า~ 👟✨" in result
        assert "ยอดรวมทั้งหมด: 740.00 บาท" in result
        assert "Nike: 3 คู่ (ยอดขาย 450.00 บาท, กำไร 450.00 บาท)" in result
        assert "Adidas: 1 คู่ (ยอดขาย 290.00 บาท, กำไร 290.00 บาท)" in result
        assert "💸 กำไรทั้งหมด: 740.00 บาท" in result

    @patch("features.morning_report.datetime")
    def test_build_summary_no_sales(self, mock_datetime):
        mock_datetime.now.return_value = datetime(
            2024, 1, 14, tzinfo=timezone.utc
        )
        mock_datetime.strptime.side_effect = datetime.strptime

        rows = [
            ["วันที่", "เมนู", "จำนวน", "ราคา", "ยอดรวม"],
            ["2024-01-10", "Nike", "2", "150", "300"],
        ]

        result = build_summary(rows)

        mock_datetime.now.assert_called_once_with(THAI_TZ)
        assert "ยังไม่มียอดขายเลยค่ะ" in result

    def test_build_summary_empty_rows(self):
        result = build_summary([])

        assert result == "ยังไม่มีข้อมูลใน Google Sheet ค่ะ 😅"

    def test_build_summary_missing_columns(self):
        rows = [
            ["ชื่อ", "ราคา"],
            ["RoV", "150"],
        ]

        result = build_summary(rows)

        assert "ไม่พบคอลัมน์ที่ต้องการ" in result


    @patch("features.morning_report.datetime")
    def test_build_summary_with_new_gaming_headers(self, mock_datetime):
        # Mock datetime.now(THAI_TZ)
        mock_now = datetime(2024, 1, 14, 8, 0, 0, tzinfo=THAI_TZ)
        mock_datetime.now.return_value = mock_now
        mock_datetime.fromisoformat.side_effect = datetime.fromisoformat
        mock_datetime.strptime.side_effect = datetime.strptime

        rows = [
            ["วันที่", "รองเท้า", "ไซส์", "จำนวน", "ราคา", "ยอดรวม"],
            ["2024-01-13T10:00:00+07:00", "Nike", "42", "2", "790", "1580"],
            ["2024-01-13T11:00:00+07:00", "Adidas", "ทั่วไป", "1", "290", "290"],
            ["2024-01-13T12:00:00+07:00", "Nike", "43", "1", "1890", "1890"],
        ]

        result = build_summary(rows)

        mock_datetime.now.assert_called_once_with(THAI_TZ)
        assert "สรุปยอดขายรองเท้าเมื่อวันวานน้า~ 👟✨" in result
        assert "ยอดรวมทั้งหมด: 3760.00 บาท" in result
        assert "Nike (42): 2 คู่ (ยอดขาย 1580.00 บาท, กำไร 1580.00 บาท)" in result
        assert "Nike (43): 1 คู่ (ยอดขาย 1890.00 บาท, กำไร 1890.00 บาท)" in result
        assert "Adidas: 1 คู่ (ยอดขาย 290.00 บาท, กำไร 290.00 บาท)" in result
        assert "💸 กำไรทั้งหมด: 3760.00 บาท" in result
    @patch("features.morning_report.get_sheet")
    @patch("features.morning_report.datetime")
    def test_build_summary_with_profit_column(self, mock_datetime, mock_get_sheet):
        # Mock datetime.now(THAI_TZ)
        mock_now = datetime(2024, 1, 14, 8, 0, 0, tzinfo=THAI_TZ)
        mock_datetime.now.return_value = mock_now
        mock_datetime.fromisoformat.side_effect = datetime.fromisoformat
        mock_datetime.strptime.side_effect = datetime.strptime

        # Mock Products sheet failure or return empty to avoid network hits
        mock_get_sheet.side_effect = Exception("Mock sheet failure")

        # Orders sheet style with "กำไร" column
        rows = [
            ["วันที่ขาย", "รหัสสินค้า", "ราคาที่ขาย", "กำไร"],
            ["2024-01-13T10:00:00+07:00", "NK-001", "3500", "1200"],
            ["2024-01-13T11:00:00+07:00", "AD-002", "2900", "900"],
        ]

        result = build_summary(rows)

        assert "ยอดรวมทั้งหมด: 6400.00 บาท" in result
        assert "💸 กำไรทั้งหมด: 2100.00 บาท" in result
        assert "[NK-001]: 1 คู่ (ยอดขาย 3500.00 บาท, กำไร 1200.00 บาท)" in result
        assert "[AD-002]: 1 คู่ (ยอดขาย 2900.00 บาท, กำไร 900.00 บาท)" in result

    @patch("features.morning_report.get_sheet")
    @patch("features.morning_report.datetime")
    def test_build_summary_with_product_cost_join(self, mock_datetime, mock_get_sheet):
        # Mock datetime.now(THAI_TZ)
        mock_now = datetime(2024, 1, 14, 8, 0, 0, tzinfo=THAI_TZ)
        mock_datetime.now.return_value = mock_now
        mock_datetime.fromisoformat.side_effect = datetime.fromisoformat
        mock_datetime.strptime.side_effect = datetime.strptime

        # Mock Products sheet to return cost prices
        mock_products_sheet = Mock()
        mock_products_sheet.get_all_records.return_value = [
            {"รหัสสินค้า": "NK-001", "ราคาทุน": "2300", "แบรนด์": "Nike", "รุ่น": "Dunk"},
            {"รหัสสินค้า": "AD-002", "ราคาทุน": "2000", "แบรนด์": "Adidas", "รุ่น": "Samba"},
        ]
        mock_get_sheet.return_value = mock_products_sheet

        # Orders rows without profit column
        rows = [
            ["วันที่", "รหัสสินค้า", "จำนวน", "ยอดรวม"],
            ["2024-01-13T10:00:00+07:00", "NK-001", "1", "3500"],
            ["2024-01-13T11:00:00+07:00", "AD-002", "1", "2900"],
        ]

        result = build_summary(rows)

        mock_get_sheet.assert_called_with("Products")
        assert "ยอดรวมทั้งหมด: 6400.00 บาท" in result
        # NK-001: price 3500, cost 2300 -> profit 1200
        # AD-002: price 2900, cost 2000 -> profit 900
        # Total profit = 2100
        assert "💸 กำไรทั้งหมด: 2100.00 บาท" in result
        assert "[NK-001] Nike Dunk: 1 คู่ (ยอดขาย 3500.00 บาท, กำไร 1200.00 บาท)" in result
        assert "[AD-002] Adidas Samba: 1 คู่ (ยอดขาย 2900.00 บาท, กำไร 900.00 บาท)" in result


class TestSendTelegramMessage:
    @patch("features.morning_report.requests.post")
    @patch("features.morning_report.os.getenv")
    def test_send_telegram_success(self, mock_getenv, mock_post):
        def getenv_side_effect(key):
            values = {
                "TELEGRAM_BOT_TOKEN": "fake-token",
                "TELEGRAM_CHAT_ID": "123456",
            }
            return values.get(key)

        mock_getenv.side_effect = getenv_side_effect

        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        send_telegram_message("hello")

        mock_post.assert_called_once()

    @patch("features.morning_report.os.getenv")
    def test_send_telegram_missing_env(self, mock_getenv):
        mock_getenv.return_value = None

        with pytest.raises(RuntimeError):
            send_telegram_message("hello")

    @patch("features.morning_report.requests.post")
    @patch("features.morning_report.os.getenv")
    def test_send_telegram_http_error(self, mock_getenv, mock_post):
        def getenv_side_effect(key):
            values = {
                "TELEGRAM_BOT_TOKEN": "fake-token",
                "TELEGRAM_CHAT_ID": "123456",
            }
            return values.get(key)

        mock_getenv.side_effect = getenv_side_effect

        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.text = '{"ok":false}'
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
            "HTTP Error"
        )

        mock_post.return_value = mock_response

        with pytest.raises(RuntimeError):
            send_telegram_message("hello")
