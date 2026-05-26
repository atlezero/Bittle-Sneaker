import os
from unittest.mock import MagicMock, patch

import pytest
import gspread
from google.oauth2.service_account import Credentials

from features.agent_tools import (
    log_sale,
    get_sales_today,
)

# ─────────────────────────────────────────────────────────────
# ใช้ sheet ชื่อ "test"
# ─────────────────────────────────────────────────────────────

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]


def get_test_sheet(name=None):
    from features.sheets_client import get_sheet
    return get_sheet("test")


# Check if credentials exist for integration tests
CREDENTIALS_EXIST = (
    os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON") is not None or 
    os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE") is not None
)

@pytest.fixture(autouse=True)
def setup_integration(monkeypatch):
    # เปลี่ยนไปใช้ฟังก์ชันต่อชีทจริงที่เรามีอยู่แล้วในไฟล์นี้ (get_test_sheet)
    monkeypatch.setattr(
        "features.agent_tools._get_sheet",
        get_test_sheet,
    )
    yield


# ─────────────────────────────────────────────────────────────
# tests
# ─────────────────────────────────────────────────────────────

@pytest.mark.integration
@pytest.mark.skipif(not CREDENTIALS_EXIST, reason="ไม่พบ Google Credentials (JSON หรือ FILE)")
def test_log_sale_success():

    result = log_sale(
        menu="Nike",
        quantity=2,
        price=150,
    )

    assert result["status"] == "success"
    assert result["menu"] == "Nike"
    assert result["quantity"] == 2
    assert result["price"] == 150
    assert result["total"] == 300


@pytest.mark.integration
@pytest.mark.skipif(not CREDENTIALS_EXIST, reason="ไม่พบ Google Credentials (JSON หรือ FILE)")
def test_log_sale_invalid_quantity():

    with pytest.raises(ValueError):
        log_sale(
            menu="Adidas",
            quantity=0,
            price=290,
        )


@pytest.mark.integration
@pytest.mark.skipif(not CREDENTIALS_EXIST, reason="ไม่พบ Google Credentials (JSON หรือ FILE)")
def test_log_sale_invalid_price():

    with pytest.raises(ValueError):
        log_sale(
            menu="Adidas",
            quantity=1,
            price=0,
        )


@pytest.mark.integration
@pytest.mark.skipif(not CREDENTIALS_EXIST, reason="ไม่พบ Google Credentials (JSON หรือ FILE)")
def test_get_sales_today():

    result = get_sales_today()

    assert result["status"] == "success"

    assert "total_revenue" in result
    assert "total_items" in result
    assert "menu_summary" in result


class TestLogSaleStockValidation:
    """Unit tests for stock validation in log_sale (relational mode)"""

    @patch("features.agent_tools._get_sheet_safe")
    def test_log_sale_sku_not_in_stock(self, mock_get_sheet):
        mock_products_sheet = MagicMock()
        mock_orders_sheet = MagicMock()
        mock_products_sheet.id = "products-sheet-id"
        mock_orders_sheet.id = "orders-sheet-id"
        mock_products_sheet.get_all_records.return_value = []
        
        def mock_get_sheet_side_effect(name):
            if name == "Products":
                return mock_products_sheet
            elif name == "Orders":
                return mock_orders_sheet
            return MagicMock()
            
        mock_get_sheet.side_effect = mock_get_sheet_side_effect

        with pytest.raises(ValueError, match="ไม่พบสินค้าที่มีรหัส 'NK-001' ในสต็อก"):
            log_sale(
                sku="NK-001",
                quantity=1,
                price=3500.0,
            )

    @patch("features.agent_tools._get_sheet_safe")
    def test_log_sale_sku_already_sold(self, mock_get_sheet):
        mock_products_sheet = MagicMock()
        mock_orders_sheet = MagicMock()
        mock_products_sheet.id = "products-sheet-id"
        mock_orders_sheet.id = "orders-sheet-id"
        mock_products_sheet.get_all_records.return_value = [
            {"รหัสสินค้า": "NK-001", "สถานะ": "ขายแล้ว", "ราคาทุน": 2000.0}
        ]
        
        def mock_get_sheet_side_effect(name):
            if name == "Products":
                return mock_products_sheet
            elif name == "Orders":
                return mock_orders_sheet
            return MagicMock()
            
        mock_get_sheet.side_effect = mock_get_sheet_side_effect

        with pytest.raises(ValueError, match="สินค้าที่มีรหัส 'NK-001' ถูกขายไปแล้ว"):
            log_sale(
                sku="NK-001",
                quantity=1,
                price=3500.0,
            )

    @patch("features.agent_tools._get_sheet_safe")
    def test_log_sale_by_description_not_found(self, mock_get_sheet):
        mock_products_sheet = MagicMock()
        mock_orders_sheet = MagicMock()
        mock_products_sheet.id = "products-sheet-id"
        mock_orders_sheet.id = "orders-sheet-id"
        mock_products_sheet.get_all_records.return_value = [
            {"รหัสสินค้า": "NK-001", "แบรนด์": "Adidas", "รุ่น": "Samba", "ไซส์ EU": "42", "สถานะ": "ว่าง"}
        ]
        
        def mock_get_sheet_side_effect(name):
            if name == "Products":
                return mock_products_sheet
            elif name == "Orders":
                return mock_orders_sheet
            return MagicMock()
            
        mock_get_sheet.side_effect = mock_get_sheet_side_effect

        with pytest.raises(ValueError, match="ไม่พบ 'Nike Dunk ไซส์ 42' ที่พร้อมขายในสต็อก"):
            log_sale(
                sku="ไม่ระบุ",
                brand="Nike",
                model="Dunk",
                size="42",
                quantity=1,
                price=3500.0,
            )

    @patch("features.agent_tools._get_sheet_safe")
    def test_log_sale_successful_validation(self, mock_get_sheet):
        mock_products_sheet = MagicMock()
        mock_orders_sheet = MagicMock()
        mock_products_sheet.id = "products-sheet-id"
        mock_orders_sheet.id = "orders-sheet-id"
        mock_products_sheet.get_all_records.return_value = [
            {"รหัสสินค้า": "NK-001", "แบรนด์": "Nike", "รุ่น": "Dunk", "ไซส์ EU": "42", "สถานะ": "ว่าง", "ราคาทุน": 2000.0}
        ]
        
        def mock_get_sheet_side_effect(name):
            if name == "Products":
                return mock_products_sheet
            elif name == "Orders":
                return mock_orders_sheet
            return MagicMock()
            
        mock_get_sheet.side_effect = mock_get_sheet_side_effect

        result = log_sale(
            sku="NK-001",
            quantity=1,
            price=3500.0,
        )

        assert result["status"] == "success"
        assert result["sku"] == "NK-001"
        mock_products_sheet.update_cell.assert_called_once()
        mock_orders_sheet.append_row.assert_called_once()