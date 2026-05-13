from unittest.mock import patch, MagicMock

import pytest

from features.sales_logger import THAI_TZ, parse_sale_item, main


class TestParseSaleItem:
    """Test cases for parse_sale_item function"""

    def test_parse_sale_item_valid_input(self):
        """Test parsing valid sale item string"""
        result = parse_sale_item("กาแฟ:2:45.5")
        assert result == ("กาแฟ", 2, 45.5)

    def test_parse_sale_item_with_spaces(self):
        """Test parsing sale item with extra spaces"""
        result = parse_sale_item("  กาแฟ  :  2  :  45.5  ")
        assert result == ("กาแฟ", 2, 45.5)

    def test_parse_sale_item_invalid_format(self):
        """Test parsing invalid format (not 3 parts)"""
        with pytest.raises(ValueError, match="รูปแบบต้องเป็น เมนู:จำนวน:ราคา"):
            parse_sale_item("กาแฟ:2")

        with pytest.raises(ValueError, match="รูปแบบต้องเป็น เมนู:จำนวน:ราคา"):
            parse_sale_item("กาแฟ:2:45:extra")

    def test_parse_sale_item_empty_menu(self):
        """Test parsing with empty menu name"""
        with pytest.raises(ValueError, match="ชื่อเมนูไม่สามารถเว้นว่างได้"):
            parse_sale_item(":2:45")

        with pytest.raises(ValueError, match="ชื่อเมนูไม่สามารถเว้นว่างได้"):
            parse_sale_item("   :2:45")

    def test_parse_sale_item_invalid_quantity(self):
        """Test parsing with invalid quantity"""
        with pytest.raises(ValueError, match="จำนวนต้องเป็นจำนวนเต็ม"):
            parse_sale_item("กาแฟ:สอง:45")

        with pytest.raises(ValueError, match="จำนวนต้องเป็นจำนวนเต็ม"):
            parse_sale_item("กาแฟ:2.5:45")

    def test_parse_sale_item_invalid_price(self):
        """Test parsing with invalid price"""
        with pytest.raises(ValueError, match="ราคาต้องเป็นตัวเลข"):
            parse_sale_item("กาแฟ:2:สี่สิบห้า")

        with pytest.raises(ValueError, match="ราคาต้องเป็นตัวเลข"):
            parse_sale_item("กาแฟ:2:abc")


class TestMainFunction:
    """Test cases for main function"""

    @patch("features.sales_logger.load_dotenv")
    @patch("features.sales_logger.argparse.ArgumentParser.parse_args")
    @patch("features.sales_logger.parse_sale_item")
    @patch("features.sales_logger.get_sheet")
    @patch("features.sales_logger.datetime")
    def test_main_success(
        self,
        mock_datetime,
        mock_get_sheet,
        mock_parse_sale,
        mock_parse_args,
        mock_load_dotenv,
    ):
        """Test successful execution of main function"""
        # Setup mocks
        mock_parse_args.return_value = MagicMock(sale="กาแฟ:2:45")
        mock_parse_sale.return_value = ("กาแฟ", 2, 45.0)
        mock_datetime.now.return_value.date.return_value.isoformat.return_value = "2024-01-01"
        mock_sheet = MagicMock()
        mock_get_sheet.return_value = mock_sheet

        # Call function
        result = main()

        # Assertions
        assert result == 0
        mock_datetime.now.assert_called_once_with(THAI_TZ)
        mock_sheet.append_row.assert_called_once_with(["2024-01-01", "กาแฟ", 2, 45.0, 90.0])

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
    @patch("features.sales_logger.get_sheet")
    def test_main_sheet_error(self, mock_get_sheet, mock_parse_sale, mock_parse_args, mock_load_dotenv, capsys):
        """Test main function with sheet connection error"""
        # Setup mocks
        mock_parse_args.return_value = MagicMock(sale="กาแฟ:2:45")
        mock_parse_sale.return_value = ("กาแฟ", 2, 45.0)
        mock_get_sheet.side_effect = RuntimeError("Sheet error")

        # Call function
        result = main()

        # Assertions
        assert result == 1
        captured = capsys.readouterr()
        assert "ข้อผิดพลาด: Sheet error" in captured.err
