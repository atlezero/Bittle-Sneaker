id="k1v4sd"
import os

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


def get_test_sheet():

    creds = Credentials.from_service_account_file(
        "service-account.json",
        scopes=SCOPES,
    )

    gc = gspread.authorize(creds)

    spreadsheet_id = os.getenv("GOOGLE_SHEETS_ID")

    spreadsheet = gc.open_by_key(
        spreadsheet_id
    )

    return spreadsheet.worksheet("test")


# ─────────────────────────────────────────────────────────────
# monkey patch _get_sheet
# ─────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def patch_sheet(monkeypatch):

    monkeypatch.setattr(
        "features.agent_tools._get_sheet",
        get_test_sheet,
    )

    yield


# ─────────────────────────────────────────────────────────────
# tests
# ─────────────────────────────────────────────────────────────

def test_log_sale_success():

    result = log_sale(
        menu="ชาไทย",
        quantity=2,
        price=50,
    )

    assert result["status"] == "success"
    assert result["menu"] == "ชาไทย"
    assert result["quantity"] == 2
    assert result["price"] == 50
    assert result["total"] == 100


def test_log_sale_invalid_quantity():

    with pytest.raises(ValueError):
        log_sale(
            menu="โกโก้",
            quantity=0,
            price=45,
        )


def test_log_sale_invalid_price():

    with pytest.raises(ValueError):
        log_sale(
            menu="โกโก้",
            quantity=1,
            price=0,
        )


def test_get_sales_today():

    result = get_sales_today()

    assert result["status"] == "success"

    assert "total_revenue" in result
    assert "total_items" in result
    assert "menu_summary" in result