import pytest
from unittest.mock import patch, MagicMock

from features.caption_gen import generate_captions


class TestGenerateCaptions:
    """Test cases for generate_captions function"""

    @patch("features.caption_gen.genai.GenerativeModel")
    @patch.dict("os.environ", {"GEMINI_API_KEY": "test_key"})
    def test_generate_captions_success(self, mock_model_class):
        """Test successful caption generation"""
        # Setup mock
        mock_model = MagicMock()
        mock_response = MagicMock()
        mock_response.text = """
        Cute: น่ารักจังเลยค่ะ 💕
        Minimal: สินค้าดี
        Gen-Z: ยอดเยี่ยมมาก 🔥
        """
        mock_model.generate_content.return_value = mock_response
        mock_model_class.return_value = mock_model

        # Call function
        result = generate_captions("เสื้อยืด", 299)

        # Assertions
        assert isinstance(result, str)
        assert "Cute:" in result
        assert "Minimal:" in result
        assert "Gen-Z:" in result
        assert "💕" in result
        assert "🔥" in result

        # Check that generate_content was called with correct prompt
        mock_model.generate_content.assert_called_once()
        call_args = mock_model.generate_content.call_args[0][0]
        assert "เสื้อยืด" in call_args
        assert "299 บาท" in call_args
        assert "Cute:" in call_args
        assert "Minimal:" in call_args
        assert "Gen-Z:" in call_args

    @patch("features.caption_gen.genai.GenerativeModel")
    @patch.dict("os.environ", {"GEMINI_API_KEY": "test_key"})
    def test_generate_captions_empty_response(self, mock_model_class):
        """Test caption generation with empty response"""
        # Setup mock
        mock_model = MagicMock()
        mock_response = MagicMock()
        mock_response.text = ""
        mock_model.generate_content.return_value = mock_response
        mock_model_class.return_value = mock_model

        # Call function
        result = generate_captions("สินค้า", 100)

        # Assertions
        assert result == ""

    @patch("features.caption_gen.genai.GenerativeModel")
    @patch.dict("os.environ", {"GEMINI_API_KEY": "test_key"})
    def test_generate_captions_with_whitespace(self, mock_model_class):
        """Test caption generation with whitespace in response"""
        # Setup mock
        mock_model = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "   \n\n  Cute: test  \n\n  "
        mock_model.generate_content.return_value = mock_response
        mock_model_class.return_value = mock_model

        # Call function
        result = generate_captions("สินค้า", 100)

        # Assertions
        assert result == "Cute: test"

    @patch("features.caption_gen.genai.configure")
    @patch.dict("os.environ", {}, clear=True)
    def test_generate_captions_missing_api_key(self, mock_configure):
        """Test caption generation when API key is missing"""
        # This should still work since the function doesn't validate the key
        # but genai.configure will be called with None
        with patch("features.caption_gen.genai.GenerativeModel") as mock_model_class:
            mock_model = MagicMock()
            mock_response = MagicMock()
            mock_response.text = "Cute: test"
            mock_model.generate_content.return_value = mock_response
            mock_model_class.return_value = mock_model

            result = generate_captions("สินค้า", 100)

            assert result == "Cute: test"
            mock_configure.assert_called_once_with(api_key=None)

    @patch("features.caption_gen.genai.GenerativeModel")
    @patch.dict("os.environ", {"GEMINI_API_KEY": "test_key"})
    def test_generate_captions_api_error(self, mock_model_class):
        """Test caption generation when API call fails"""
        # Setup mock to raise exception
        mock_model = MagicMock()
        mock_model.generate_content.side_effect = Exception("API Error")
        mock_model_class.return_value = mock_model

        # Call function and expect exception
        with pytest.raises(Exception, match="API Error"):
            generate_captions("สินค้า", 100)
