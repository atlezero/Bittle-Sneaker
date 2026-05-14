id="s3u7qp"
from unittest.mock import Mock, patch

from features.agent_harness import run_agent


# ─────────────────────────────────────────────────────────────
# test: log_sale success
# ─────────────────────────────────────────────────────────────

@patch("features.agent_harness.client.models.generate_content")
@patch("features.agent_harness.TOOLS")
def test_run_agent_log_sale(mock_tools, mock_generate):

    # mock llm response
    mock_response = Mock()
    mock_response.text = """
    {
        "action": "log_sale",
        "args": {
            "menu": "ชาไทย",
            "quantity": 2,
            "price": 50
        }
    }
    """

    mock_generate.return_value = mock_response

    # mock tool result
    mock_tools.__contains__.return_value = True

    mock_tools.__getitem__.return_value = Mock(
        return_value={
            "menu": "ชาไทย",
            "quantity": 2,
            "total": 100,
        }
    )

    result = run_agent("ขายชาไทย 2 แก้ว")

    assert "บันทึกสำเร็จ" in result
    assert "100" in result


# ─────────────────────────────────────────────────────────────
# test: unknown action
# ─────────────────────────────────────────────────────────────

@patch("features.agent_harness.client.models.generate_content")
def test_run_agent_unknown_action(mock_generate):

    mock_response = Mock()

    mock_response.text = """
    {
        "action": "hack_system",
        "args": {}
    }
    """

    mock_generate.return_value = mock_response

    result = run_agent("แฮกระบบ")

    assert "ไม่รู้จัก action" in result


# ─────────────────────────────────────────────────────────────
# test: invalid json
# ─────────────────────────────────────────────────────────────

@patch("features.agent_harness.client.models.generate_content")
def test_run_agent_invalid_json(mock_generate):

    mock_response = Mock()

    mock_response.text = "มั่วจัดๆ"

    mock_generate.return_value = mock_response

    result = run_agent("ขายชาไทย")

    assert "AI ตอบกลับในรูปแบบที่ไม่ถูกต้อง" in result


# ─────────────────────────────────────────────────────────────
# test: get_sales_today
# ─────────────────────────────────────────────────────────────

@patch("features.agent_harness.client.models.generate_content")
@patch("features.agent_harness.TOOLS")
def test_run_agent_get_sales(mock_tools, mock_generate):

    mock_response = Mock()

    mock_response.text = """
    {
        "action": "get_sales_today",
        "args": {}
    }
    """

    mock_generate.return_value = mock_response

    mock_tools.__contains__.return_value = True

    mock_tools.__getitem__.return_value = Mock(
        return_value={
            "total_revenue": 500,
            "total_items": 10,
            "menu_summary": {
                "ชาไทย": {
                    "quantity": 10,
                    "total": 500
                }
            }
        }
    )

    result = run_agent("สรุปยอดขายวันนี้")

    assert "500" in result
    assert "10" in result