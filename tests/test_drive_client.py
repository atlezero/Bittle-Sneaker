# tests/test_drive_client.py
from unittest.mock import patch, Mock
from features.drive_client import get_product_images_for_text

class TestGetProductImagesForText:

    @patch("features.drive_client.find_product_image")
    def test_no_codes_in_text(self, mock_find):
        result = get_product_images_for_text("สวัสดีค่ะ มีรองเท้าแนะนำไหมคะ")
        assert result == []
        mock_find.assert_not_called()

    @patch("features.drive_client.find_product_image")
    def test_single_code_found(self, mock_find):
        mock_find.return_value = "https://drive.google.com/uc?export=view&id=12345"
        
        result = get_product_images_for_text("สนใจคู่ NI-001 ครับ ขอดูรูปหน่อย")
        
        assert result == [{"code": "NI-001", "url": "https://drive.google.com/uc?export=view&id=12345"}]
        mock_find.assert_called_once_with("NI-001")

    @patch("features.drive_client.find_product_image")
    def test_multiple_codes_and_case_insensitivity(self, mock_find):
        # mock returns different URLs for different codes
        def mock_side_effect(code):
            if code == "NI-001":
                return "url_ni"
            if code == "AD-002":
                return "url_ad"
            return None
            
        mock_find.side_effect = mock_side_effect
        
        # ข้อความป้อนแบบปนตัวพิมพ์เล็กพิมพ์ใหญ่ และซ้ำกัน
        result = get_product_images_for_text("ดูคู่ ni-001 และ ad-002 และ NI-001 ด้วยค่ะ")
        
        # ควรจับคู่ได้ AD-002 และ NI-001 (เรียงตามลำดับอักษรและไม่ซ้ำ)
        assert len(result) == 2
        assert result[0] == {"code": "AD-002", "url": "url_ad"}
        assert result[1] == {"code": "NI-001", "url": "url_ni"}
        
        # ตรวจสอบการเรียก mock_find
        assert mock_find.call_count == 2
        mock_find.assert_any_call("NI-001")
        mock_find.assert_any_call("AD-002")

    @patch("features.drive_client.find_product_image")
    def test_image_not_found(self, mock_find):
        mock_find.return_value = None
        
        result = get_product_images_for_text("ขอดูรูป AD-999 หน่อยค่ะ")
        
        assert result == []
        mock_find.assert_called_once_with("AD-999")
