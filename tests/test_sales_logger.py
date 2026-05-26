from unittest.mock import patch, MagicMock
import pytest

from features.sales_logger import THAI_TZ, parse_sale_item, main


class TestParseSaleItem:
    """Test cases for parse_sale_item function"""

    def test_parse_sale_item_valid_input(self):
        """Test parsing valid sale item string"""
        result = parse_sale_item("NK-001:3500.0:IG")
        assert result == ("NK-001", 3500.0, "IG")

    def test_parse_sale_item_with_spaces(self):
        """Test parsing sale item with extra spaces"""
        result = parse_sale_item("  NK-001  :  3500.0  :  IG  ")
        assert result == ("NK-001", 3500.0, "IG")

    def test_parse_sale_item_invalid_format(self):
        """Test parsing invalid format (not 3 parts)"""
        with pytest.raises(ValueError, match="รูปแบบต้องเป็น รหัสสินค้า:ราคาที่ขาย:ช่องทางขาย"):
            parse_sale_item("NK-001:3500")

        with pytest.raises(ValueError, match="รูปแบบต้องเป็น รหัสสินค้า:ราคาที่ขาย:ช่องทางขาย"):
            parse_sale_item("NK-001:3500:IG:extra")

    def test_parse_sale_item_empty_sku(self):
        """Test parsing with empty SKU"""
        with pytest.raises(ValueError, match="รหัสสินค้าไม่สามารถเว้นว่างได้"):
            parse_sale_item(":3500:IG")

        with pytest.raises(ValueError, match="รหัสสินค้าไม่สามารถเว้นว่างได้"):
            parse_sale_item("   :3500:IG")

    def test_parse_sale_item_empty_channel(self):
        """Test parsing with empty channel"""
        with pytest.raises(ValueError, match="ช่องทางขายไม่สามารถเว้นว่างได้"):
            parse_sale_item("NK-001:3500:")

        with pytest.raises(ValueError, match="ช่องทางขายไม่สามารถเว้นว่างได้"):
            parse_sale_item("NK-001:3500:   ")

    def test_parse_sale_item_invalid_price(self):
        """Test parsing with invalid price"""
        with pytest.raises(ValueError, match="ราคาต้องเป็นตัวเลข"):
            parse_sale_item("NK-001:abc:IG")


class TestMainFunction:
    """Test cases for main function"""

    @patch("features.sales_logger.load_dotenv")
    @patch("features.sales_logger.argparse.ArgumentParser.parse_args")
    @patch("features.sales_logger.parse_sale_item")
    @patch("features.sales_logger.log_sale")
    def test_main_success(
        self,
        mock_log_sale,
        mock_parse_sale,
        mock_parse_args,
        mock_load_dotenv,
    ):
        """Test successful execution of main function"""
        # Setup mocks
        mock_parse_args.return_value = MagicMock(sale="NK-001:3500:IG")
        mock_parse_sale.return_value = ("NK-001", 3500.0, "IG")
        
        mock_iso_timestamp = "2024-01-01T12:00:00.000000+07:00"
        mock_log_sale.return_value = {
            "status": "success",
            "timestamp": mock_iso_timestamp,
            "brand": "Nike",
            "model": "Dunk",
            "size": "42",
            "total": 3500.0
        }

        # Call function
        result = main()

        # Assertions
        assert result == 0
        mock_log_sale.assert_called_once_with(
            sku="NK-001",
            price=3500.0,
            sales_channel="IG",
            quantity=1
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
        mock_parse_args.return_value = MagicMock(sale="NK-001:3500:IG")
        mock_parse_sale.return_value = ("NK-001", 3500.0, "IG")
        mock_log_sale.side_effect = RuntimeError("Sheet error")

        # Call function
        result = main()

        # Assertions
        assert result == 1
        captured = capsys.readouterr()
        assert "ข้อผิดพลาด: Sheet error" in captured.err
