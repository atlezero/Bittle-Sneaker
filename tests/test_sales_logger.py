from unittest.mock import patch, MagicMock

import pytest

from features.sales_logger import THAI_TZ, parse_sale_item, main


class TestParseSaleItem:
    """Test cases for parse_sale_item function"""

    def test_parse_sale_item_valid_input(self):
        """Test parsing valid sale item string"""
        result = parse_sale_item("Nike:2:150.0")
        assert result == ("Nike", 2, 150.0)

    def test_parse_sale_item_with_spaces(self):
        """Test parsing sale item with extra spaces"""
        result = parse_sale_item("  Nike  :  2  :  150.0  ")
        assert result == ("Nike", 2, 150.0)

    def test_parse_sale_item_invalid_format(self):
        """Test parsing invalid format (not 3 parts)"""
        with pytest.raises(ValueError, match="รูปแบบต้องเป็น เมนู:จำนวน:ราคา"):
            parse_sale_item("Nike:2")

        with pytest.raises(ValueError, match="รูปแบบต้องเป็น เมนู:จำนวน:ราคา"):
            parse_sale_item("Nike:2:150:extra")

    def test_parse_sale_item_empty_menu(self):
        """Test parsing with empty menu name"""
        with pytest.raises(ValueError, match="ชื่อเมนูไม่สามารถเว้นว่างได้"):
            parse_sale_item(":2:150")

        with pytest.raises(ValueError, match="ชื่อเมนูไม่สามารถเว้นว่างได้"):
            parse_sale_item("   :2:150")

    def test_parse_sale_item_invalid_quantity(self):
        """Test parsing with invalid quantity"""
        with pytest.raises(ValueError, match="จำนวนต้องเป็นจำนวนเต็ม"):
            parse_sale_item("Nike:สอง:150")

        with pytest.raises(ValueError, match="จำนวนต้องเป็นจำนวนเต็ม"):
            parse_sale_item("Nike:2.5:150")

    def test_parse_sale_item_invalid_price(self):
        """Test parsing with invalid price"""
        with pytest.raises(ValueError, match="ราคาต้องเป็นตัวเลข"):
            parse_sale_item("Nike:2:หนึ่งร้อยห้าสิบ")

        with pytest.raises(ValueError, match="ราคาต้องเป็นตัวเลข"):
            parse_sale_item("Nike:2:abc")


class TestMainFunction:
    """Test cases for main function"""

    @patch("features.sales_logger.load_dotenv")
    @patch("features.sales_logger.argparse.ArgumentParser.parse_args")
    @patch("features.sales_logger.parse_sale_item")
    @patch("features.sales_logger.log_sale")
    @patch("features.sales_logger.datetime")
    def test_main_success(
        self,
        mock_datetime,
        mock_log_sale,
        mock_parse_sale,
        mock_parse_args,
        mock_load_dotenv,
    ):
        """Test successful execution of main function"""
        # Setup mocks
        mock_parse_args.return_value = MagicMock(sale="Nike:2:150")
        mock_parse_sale.return_value = ("Nike", 2, 150.0)
        # Mock .now(THAI_TZ).isoformat()
        mock_iso_timestamp = "2024-01-01T12:00:00.000000+07:00"
        mock_datetime.now.return_value.isoformat.return_value = mock_iso_timestamp
        
        mock_log_sale.return_value = {
            "status": "success",
            "timestamp": mock_iso_timestamp,
            "total": 300.0
        }

        # Call function
        result = main()

        # Assertions
        assert result == 0
        mock_datetime.now.assert_called_once_with(THAI_TZ)
        mock_log_sale.assert_called_once_with(
            sku="ไม่ระบุ",
            brand="Nike",
            model="ทั่วไป",
            size="ทั่วไป",
            quantity=2,
            price=150.0
        )

    @patch("features.sales_logger.load_dotenv")
    @patch("features.sales_logger.argparse.ArgumentParser.parse_args")
    @patch("features.sales_logger.parse_sale_item")
    def test_main_parse_error(self, mock_parse_sale, mock_parse_args, mock_load_dotenv, capsys):
        """Test main function with parsing error"""
        # Setup mocks
        mock_parse_args.return_value = MagicMock(sale="invalid")
        mock_parse_sale.side_effect = ValueError("Parse error")

        # Call function
        result = main()

        # Assertions
        assert result == 1
        captured = capsys.readouterr()
        assert "ข้อผิดพลาด: Parse error" in captured.err

    @patch("features.sales_logger.load_dotenv")
    @patch("features.sales_logger.argparse.ArgumentParser.parse_args")
    @patch("features.sales_logger.parse_sale_item")
    @patch("features.sales_logger.log_sale")
    def test_main_sheet_error(self, mock_log_sale, mock_parse_sale, mock_parse_args, mock_load_dotenv, capsys):
        """Test main function with sheet connection error"""
        # Setup mocks
        mock_parse_args.return_value = MagicMock(sale="Nike:2:150")
        mock_parse_sale.return_value = ("Nike", 2, 150.0)
        mock_log_sale.side_effect = RuntimeError("Sheet error")

        # Call function
        result = main()

        # Assertions
        assert result == 1
        captured = capsys.readouterr()
        assert "ข้อผิดพลาด: Sheet error" in captured.err

