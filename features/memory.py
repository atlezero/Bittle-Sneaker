# features/memory.py
import datetime
import os
import json
from pathlib import Path
from google.cloud import firestore
from google.oauth2 import service_account

PROJECT_ROOT = Path(__file__).resolve().parent.parent

class FirestoreMemory:
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.db = self._init_db()
        self.doc_ref = self.db.collection("chat_sessions").document(self.session_id) if self.db else None

    def _init_db(self):
        try:
            # ใช้ service-account-bittle.json เป็นหลัก เนื่องจากเปิดใช้งาน Firestore ไว้
            bittle_key_path = PROJECT_ROOT / "service-account-bittle.json"
            standard_key_path = PROJECT_ROOT / "service-account.json"
            
            creds = None
            
            # โหมด JSON String สำหรับ GitHub Actions
            json_str = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
            if json_str:
                info = json.loads(json_str)
                creds = service_account.Credentials.from_service_account_info(info)
            # โหมด Local
            elif bittle_key_path.exists():
                creds = service_account.Credentials.from_service_account_file(str(bittle_key_path))
            elif standard_key_path.exists():
                creds = service_account.Credentials.from_service_account_file(str(standard_key_path))
                
            if creds:
                return firestore.Client(credentials=creds, project=creds.project_id)
            else:
                # ลองโหลด Default Credentials
                return firestore.Client()
        except Exception as e:
            # หากเชื่อมต่อล้มเหลว ให้รันแบบ stateless/local ต่อได้โดยไม่เออเร่อพัง
            print(f"Error initializing Firestore Client: {e}")
            return None

    def get_history(self) -> list[dict]:
        """ดึงประวัติการแชททั้งหมดของ session_id นี้"""
        if not self.doc_ref:
            return []
        try:
            doc = self.doc_ref.get()
            if doc.exists:
                data = doc.to_dict()
                return data.get("messages", [])
        except Exception as e:
            print(f"Error getting Firestore history for session {self.session_id}: {e}")
        return []

    def save_message(self, role: str, content: str, images: list[dict] = None):
        """บันทึกข้อความใหม่ลงในลิสต์ประวัติแชท"""
        if not self.doc_ref:
            return
        try:
            new_msg = {
                "role": role,
                "content": content,
                "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
            }
            if images:
                new_msg["images"] = images
            # ใช้ ArrayUnion เพื่อเพิ่มข้อความต่อท้ายลิสต์เดิม
            self.doc_ref.set({
                "messages": firestore.ArrayUnion([new_msg]),
                "last_updated": datetime.datetime.now(datetime.timezone.utc).isoformat()
            }, merge=True)
        except Exception as e:
            print(f"Error saving Firestore message for session {self.session_id}: {e}")

    def clear_history(self):
        """ลบประวัติการสนทนาของ session_id นี้"""
        if not self.doc_ref:
            return
        try:
            self.doc_ref.delete()
        except Exception as e:
            print(f"Error clearing Firestore history for session {self.session_id}: {e}")
