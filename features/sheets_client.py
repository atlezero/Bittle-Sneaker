# sheets_client.py
import json
import os
from pathlib import Path

import gspread
from google.oauth2.service_account import Credentials

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
PROJECT_ROOT = Path(__file__).resolve().parent.parent


def resolve_service_account_file(file_path: str) -> str:
    path = Path(file_path).expanduser()
    if path.is_absolute():
        return str(path)
    return str(PROJECT_ROOT / path)


def get_sheet(worksheet_name: str | None = None):
    """รองรับทั้งโหมดไฟล์ (local) และโหมด JSON string (GitHub Actions)"""
    json_str = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
    file_path = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE")

    if json_str:  # โหมด Actions
        info = json.loads(json_str)
        creds = Credentials.from_service_account_info(info, scopes=SCOPES)
    elif file_path:  # โหมด local
        creds = Credentials.from_service_account_file(
            resolve_service_account_file(file_path), scopes=SCOPES
        )
    else:
        raise RuntimeError(
            "ไม่พบ GOOGLE_SERVICE_ACCOUNT_JSON หรือ GOOGLE_SERVICE_ACCOUNT_FILE"
        )

    client = gspread.authorize(creds)
    sheet_id = os.getenv("GOOGLE_SHEETS_ID")
    spreadsheet = client.open_by_key(sheet_id)
    worksheet_name = worksheet_name or os.getenv("GOOGLE_SHEETS_WORKSHEET")
    if worksheet_name:
        return spreadsheet.worksheet(worksheet_name)
    return spreadsheet.sheet1
