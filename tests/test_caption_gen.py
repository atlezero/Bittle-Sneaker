from unittest.mock import Mock, patch

from features.caption_gen import generate_captions


class TestGenerateCaptions:

    @patch("features.caption_gen.client.models.generate_content")
    def test_generate_captions_success(self, mock_generate):

        mock_response = Mock()

        mock_response.text = """
Cute: นุ่มสบาย ใส่แล้วละมุนสุด 🤍

Minimal: เสื้อดำเรียบ เท่ จบ

Gen-Z: ดำเท่เกินต้าน ฟีลคนคูลอะ 😎
"""

        mock_generate.return_value = mock_response

        result = generate_captions(
            "เสื้อยืด oversize สีดำ",
            299,
        )

        assert "Cute:" in result
        assert "Minimal:" in result
        assert "Gen-Z:" in result

    @patch("features.caption_gen.client.models.generate_content")
    def test_generate_captions_empty_response(self, mock_generate):

        mock_response = Mock()
        mock_response.text = ""

        mock_generate.return_value = mock_response

        result = generate_captions(
            "เสื้อ",
            100,
        )

        assert result == ""

    @patch("features.caption_gen.client.models.generate_content")
    def test_generate_captions_with_whitespace(self, mock_generate):

        mock_response = Mock()
        mock_response.text = "   hello world   "

        mock_generate.return_value = mock_response

        result = generate_captions(
            "เสื้อ",
            100,
        )

        assert result == "hello world"

    @patch("features.caption_gen.client.models.generate_content")
    def test_generate_captions_api_error(self, mock_generate):

        mock_generate.side_effect = Exception("API ERROR")

        try:
            generate_captions(
                "เสื้อ",
                100,
            )
            assert False

        except Exception as e:
            assert "API ERROR" in str(e)