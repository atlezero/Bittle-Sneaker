import json
import os
import sys
import pytest
from datetime import datetime, timezone
from unittest.mock import patch

from dotenv import load_dotenv

from features.sheets_client import PROJECT_ROOT, get_sheet, resolve_service_account_file


class TestGetSheet:
    """Test cases for get_sheet function"""

    @patch.dict(os.environ, {"GOOGLE_SERVICE_ACCOUNT_JSON": '{"type": "service_account"}'})
    @patch("features.sheets_client.Credentials.from_service_account_info")
    @patch("features.sheets_client.gspread.authorize")
    @patch("features.sheets_client.gspread.service_account")
    def test_get_sheet_with_json_env_var(self, mock_gspread_auth, mock_authorize, mock_creds):
        """Test get_sheet using GOOGLE_SERVICE_ACCOUNT_JSON environment variable"""
        # Setup mocks
        mock_client = mock_authorize.return_value
        mock_sheet = mock_client.open_by_key.return_value.sheet1

        # Call function
        result = get_sheet()

        # Assertions
        mock_creds.assert_called_once_with({"type": "service_account"}, scopes=["https://www.googleapis.com/auth/spreadsheets"])
        mock_authorize.assert_called_once()
        mock_client.open_by_key.assert_called_once_with(os.getenv("GOOGLE_SHEETS_ID"))
        assert result == mock_sheet

    @patch("features.sheets_client.Credentials.from_service_account_file")
    @patch("features.sheets_client.gspread.authorize")
    @patch("features.sheets_client.gspread.service_account")
    def test_get_sheet_with_file_env_var(self, mock_gspread_auth, mock_authorize, mock_creds):
        """Test get_sheet using GOOGLE_SERVICE_ACCOUNT_FILE environment variable"""
        # Use platform-appropriate absolute path
        if sys.platform == "win32":
            abs_path = "C:\\path\\to\\service-account.json"
        else:
            abs_path = "/path/to/service-account.json"

        with patch.dict(os.environ, {"GOOGLE_SERVICE_ACCOUNT_FILE": abs_path}):
            # Setup mocks
            mock_client = mock_authorize.return_value
            mock_sheet = mock_client.open_by_key.return_value.sheet1

            # Call function
            result = get_sheet()

            # Assertions
            mock_creds.assert_called_once_with(abs_path, scopes=["https://www.googleapis.com/auth/spreadsheets"])
            mock_authorize.assert_called_once()
            mock_client.open_by_key.assert_called_once_with(os.getenv("GOOGLE_SHEETS_ID"))
            assert result == mock_sheet

    def test_resolve_service_account_file_relative_to_project_root(self):
        """Test relative service account paths resolve from the repo root"""
        result = resolve_service_account_file("./service-account.json")

        assert result == str(PROJECT_ROOT / "service-account.json")

    @patch.dict(
        os.environ,
        {
            "GOOGLE_SERVICE_ACCOUNT_FILE": "./service-account.json",
            "GOOGLE_SHEETS_ID": "test_sheet_id",
        },
        clear=True,
    )
    @patch("features.sheets_client.Credentials.from_service_account_file")
    @patch("features.sheets_client.gspread.authorize")
    def test_get_sheet_resolves_relative_file_env_var(self, mock_authorize, mock_creds):
        """Test get_sheet resolves relative credential paths from the repo root"""
        get_sheet()

        mock_creds.assert_called_once_with(
            str(PROJECT_ROOT / "service-account.json"),
            scopes=["https://www.googleapis.com/auth/spreadsheets"],
        )

    @patch.dict(os.environ, {"GOOGLE_SERVICE_ACCOUNT_JSON": '{"type": "service_account"}'})
    @patch("features.sheets_client.Credentials.from_service_account_info")
    @patch("features.sheets_client.gspread.authorize")
    def test_get_sheet_with_explicit_worksheet_name(self, mock_authorize, mock_creds):
        """Test get_sheet opens a named worksheet when requested"""
        mock_client = mock_authorize.return_value
        mock_spreadsheet = mock_client.open_by_key.return_value
        mock_sheet = mock_spreadsheet.worksheet.return_value

        result = get_sheet("test")

        mock_spreadsheet.worksheet.assert_called_once_with("test")
        assert result == mock_sheet

    @patch.dict(
        os.environ,
        {
            "GOOGLE_SERVICE_ACCOUNT_JSON": '{"type": "service_account"}',
            "GOOGLE_SHEETS_WORKSHEET": "test",
        },
    )
    @patch("features.sheets_client.Credentials.from_service_account_info")
    @patch("features.sheets_client.gspread.authorize")
    def test_get_sheet_uses_worksheet_env_var(self, mock_authorize, mock_creds):
        """Test get_sheet opens worksheet from GOOGLE_SHEETS_WORKSHEET"""
        mock_client = mock_authorize.return_value
        mock_spreadsheet = mock_client.open_by_key.return_value
        mock_sheet = mock_spreadsheet.worksheet.return_value

        result = get_sheet()

        mock_spreadsheet.worksheet.assert_called_once_with("test")
        assert result == mock_sheet

    @patch.dict(os.environ, {}, clear=True)
    def test_get_sheet_missing_credentials(self):
        """Test get_sheet raises RuntimeError when no credentials provided"""
        with pytest.raises(RuntimeError, match="ไม่พบ GOOGLE_SERVICE_ACCOUNT_JSON หรือ GOOGLE_SERVICE_ACCOUNT_FILE"):
            get_sheet()

    @patch.dict(os.environ, {"GOOGLE_SERVICE_ACCOUNT_JSON": "invalid json"})
    def test_get_sheet_invalid_json(self):
        """Test get_sheet raises JSONDecodeError for invalid JSON"""
        with pytest.raises(json.JSONDecodeError):
            get_sheet()


@pytest.mark.integration
def test_append_and_read_from_test_worksheet():
    """Append a real row to the Google Sheet worksheet named test and read it back."""
    load_dotenv()
    has_credentials = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON") or os.getenv(
        "GOOGLE_SERVICE_ACCOUNT_FILE"
    )
    if not has_credentials or not os.getenv("GOOGLE_SHEETS_ID"):
        pytest.skip("ต้องตั้งค่า Google Sheets credentials และ GOOGLE_SHEETS_ID ก่อน")

    sheet = get_sheet("test")
    marker = f"pytest-{datetime.now(timezone.utc).isoformat()}"
    row = [marker, "integration-test", "1", "1.0", "1.0"]

    sheet.append_row(row)

    values = sheet.get_all_values()
    assert row in values
