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
            ["2024-01-13T10:00:00+07:00", "กาแฟ", "2", "45", "90"],
            ["2024-01-13T11:00:00+07:00", "ชานม", "1", "50", "50"],
            ["2024-01-13T12:00:00+07:00", "กาแฟ", "1", "45", "45"],
        ]

        result = build_summary(rows)

        mock_datetime.now.assert_called_once_with(THAI_TZ)
        assert "สรุปยอดขายเมื่อวานน้า~ 🧸" in result
        assert "ยอดรวมทั้งหมด: 185.00 บาท" in result
        assert "กาแฟ: 3 แก้ว" in result
        assert "ชานม: 1 แก้ว" in result
        assert "ขายดีที่สุด: กาแฟ (3 ชิ้น)" in result
        assert "ขายได้น้อยที่สุด: ชานม (1 ชิ้น)" in result

    @patch("features.morning_report.datetime")
    def test_build_summary_no_sales(self, mock_datetime):
        mock_datetime.now.return_value = datetime(
            2024, 1, 14, tzinfo=timezone.utc
        )
        mock_datetime.strptime.side_effect = datetime.strptime

        rows = [
            ["วันที่", "เมนู", "จำนวน", "ราคา", "ยอดรวม"],
            ["2024-01-10", "กาแฟ", "2", "45", "90"],
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
            ["กาแฟ", "45"],
        ]

        result = build_summary(rows)

        assert "ไม่พบคอลัมน์ที่ต้องการ" in result


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
