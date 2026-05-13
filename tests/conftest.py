import pytest
from unittest.mock import MagicMock


@pytest.fixture
def mock_env():
    """Fixture to mock environment variables"""
    return {
        "GOOGLE_SERVICE_ACCOUNT_JSON": '{"type": "service_account"}',
        "GOOGLE_SHEETS_ID": "test_sheet_id",
        "TELEGRAM_BOT_TOKEN": "test_token",
        "TELEGRAM_CHAT_ID": "test_chat",
        "GEMINI_API_KEY": "test_key"
    }


@pytest.fixture
def sample_sheet_data():
    """Fixture providing sample Google Sheets data"""
    return [
        ["วันที่", "เมนู", "จำนวน", "ราคา", "ยอดรวม"],
        ["2024-01-14", "กาแฟ", "2", "45", "90"],
        ["2024-01-14", "ชานม", "1", "50", "50"],
        ["2024-01-14", "กาแฟ", "1", "45", "45"],
        ["2024-01-15", "น้ำส้ม", "3", "30", "90"]
    ]


@pytest.fixture
def mock_sheet(sample_sheet_data):
    """Fixture providing a mock Google Sheet object"""
    mock_sheet = MagicMock()
    mock_sheet.get_all_values.return_value = sample_sheet_data
    mock_sheet.append_row.return_value = None
    return mock_sheet