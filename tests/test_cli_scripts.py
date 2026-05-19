import os
import subprocess
import sys
import tempfile
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
FEATURES_DIR = PROJECT_ROOT / "features"


def isolated_env() -> dict[str, str]:
    env = {
        "PATH": os.environ.get("PATH", ""),
        "PYTHONPATH": "",
        "PYTHONUTF8": "1",
        "PYTHONIOENCODING": "utf-8",
        "GOOGLE_SHEETS_ID": "test-sheet-id",
        "GOOGLE_SERVICE_ACCOUNT_FILE": str(Path(tempfile.gettempdir()) / "milk-on-the-beach-missing-service-account.json"),
        "TELEGRAM_BOT_TOKEN": "fake-token",
        "TELEGRAM_CHAT_ID": "fake-chat-id",
    }
    for var in ("SYSTEMROOT", "APPDATA", "USERPROFILE", "HOMEDRIVE", "HOMEPATH"):
        if var in os.environ:
            env[var] = os.environ[var]
    return env


def run_from_features(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, *args],
        cwd=FEATURES_DIR,
        env=isolated_env(),
        text=True,
        encoding="utf-8",
        capture_output=True,
        timeout=15,
        check=False,
    )


def assert_no_import_crash(result: subprocess.CompletedProcess[str]) -> None:
    output = result.stdout + result.stderr
    assert "ModuleNotFoundError" not in output
    assert "No module named" not in output


def test_sales_logger_script_runs_from_features_directory():
    result = run_from_features("sales_logger.py", "กาแฟ:2:45")

    assert result.returncode == 1
    assert_no_import_crash(result)
    assert "ไม่พบไฟล์ service account" in result.stderr


def test_morning_report_script_runs_from_features_directory():
    result = run_from_features("morning_report.py")

    assert result.returncode == 1
    assert_no_import_crash(result)
    assert "เกิดข้อผิดพลาด:" in result.stderr
