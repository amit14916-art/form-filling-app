import unittest
import os
import io
import asyncio
from fastapi.testclient import TestClient

# Override database connection before importing app
import database.db
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

database.db.engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
database.db.AsyncSessionLocal = async_sessionmaker(database.db.engine, expire_on_commit=False, class_=AsyncSession)

from main import app
from database.db import init_db
from database.models import User, UserProfile, Document, ExamApplication
from sqlalchemy.future import select

class TestPhase1Foundation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Initialize Database tables in sqlite
        loop = asyncio.get_event_loop()
        try:
            loop.run_until_complete(init_db())
            print("[setUpClass] SQLite In-Memory Database tables initialized successfully.")
        except Exception as e:
            print(f"[setUpClass] SQLite Database initialization failed: {e}")

    def setUp(self):
        self.client = TestClient(app)
        self.email = "test_phase1@example.com"
        self.password = "securepass123"
        self.phone = "9876543210"

    def test_auth_and_profile_flow(self):
        print("\n--- Running Phase 1 Foundation E2E Flow ---")
        
        # 1. Register User
        print("[Step 1] Registering user...")
        reg_resp = self.client.post(
            "/auth/register",
            json={
                "email": self.email,
                "password": self.password,
                "phone": self.phone
            }
        )
        self.assertEqual(reg_resp.status_code, 201)
        self.assertEqual(reg_resp.json()["status"], "SUCCESS")
        print(" -> Register OK")
        
        # 2. Login User
        print("[Step 2] Logging in...")
        login_resp = self.client.post(
            "/auth/login",
            json={
                "email": self.email,
                "password": self.password
            }
        )
        self.assertEqual(login_resp.status_code, 200)
        token_data = login_resp.json()
        self.assertIn("access_token", token_data)
        token = token_data["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        print(" -> Login OK")

        # 3. Create Profile
        print("[Step 3] Creating user profile...")
        profile_data = {
            "full_name": "Sarkari Swarm Test User",
            "dob": "1995-08-15",
            "gender": "Female",
            "category": "SC",
            "state": "Bihar",
            "qualification": "Graduate",
            "phone": "9876543210",
            "aadhaar": "123456789012",
            "email": self.email
        }
        prof_resp = self.client.post("/profile", json=profile_data, headers=headers)
        self.assertEqual(prof_resp.status_code, 200)
        self.assertEqual(prof_resp.json()["status"], "SUCCESS")
        print(" -> Profile Creation OK")

        # 4. Fetch Profile
        print("[Step 4] Retrieving user profile...")
        get_prof_resp = self.client.get("/profile", headers=headers)
        self.assertEqual(get_prof_resp.status_code, 200)
        prof_res = get_prof_resp.json()
        self.assertEqual(prof_res["full_name"], "Sarkari Swarm Test User")
        self.assertEqual(prof_res["category"], "SC")
        self.assertEqual(prof_res["aadhaar_decrypted"], "123456789012")
        self.assertIsNotNone(prof_res["aadhaar_encrypted"])
        print(" -> Profile Fetch and Decryption Verification OK")

        # 5. Check Eligibility
        print("[Step 5] Checking exam eligibility...")
        elig_resp = self.client.get("/exams/eligible", headers=headers)
        self.assertEqual(elig_resp.status_code, 200)
        exams = elig_resp.json()
        self.assertGreater(len(exams), 0)
        
        # Check that Bihar BPSC exams are returned as eligible
        bpsc_exams = [e for e in exams if "BPSC" in e["exam_name"]]
        self.assertGreater(len(bpsc_exams), 0, "BPSC exams should be eligible for Bihar residents")
        print(f" -> Found {len(exams)} eligible exams. Bihar BPSC eligibility verified.")
        
        # SC/Women candidate should have fee waiver set to True
        for e in exams:
            self.assertTrue(e["category_fee_waiver"], "SC / Female candidate should have fee waiver = True")
        print(" -> Category/Gender fee waiver check OK")

        # 6. Upload Document
        print("[Step 6] Uploading document...")
        files = {
            "file": ("test_photo.jpg", io.BytesIO(b"fake photo file content"), "image/jpeg")
        }
        upload_resp = self.client.post(
            "/profile/documents",
            headers=headers,
            data={"doc_type": "photo"},
            files=files
        )
        self.assertEqual(upload_resp.status_code, 200)
        upload_json = upload_resp.json()
        self.assertEqual(upload_json["status"], "SUCCESS")
        self.assertIn("uploads/1_photo_", upload_json["file_path"])
        print(" -> Document Upload OK")

        # 7. List Documents
        print("[Step 7] Listing uploaded documents...")
        docs_resp = self.client.get("/profile/documents", headers=headers)
        self.assertEqual(docs_resp.status_code, 200)
        docs_list = docs_resp.json()
        self.assertGreater(len(docs_list), 0)
        self.assertEqual(docs_list[0]["doc_type"], "photo")
        print(" -> Document Listing OK")

        # 8. Apply for an Exam (trigerring orchestrator)
        print("[Step 8] Applying for Bihar BPSC exam...")
        apply_resp = self.client.post(
            "/exams/apply/BPSC Civil Services Examination",
            json={"passphrase": "my_secure_passphrase"},
            headers=headers
        )
        self.assertEqual(apply_resp.status_code, 200)
        apply_data = apply_resp.json()
        self.assertEqual(apply_data["status"], "SUCCESS")
        self.assertIn("task_id", apply_data)
        self.assertIn("application_id", apply_data)
        print(" -> Apply Exam Endpoint OK (Orchestrator pipeline dispatched)")

        # 9. List Applications
        print("[Step 9] Checking applications list...")
        apps_resp = self.client.get("/exams/applications", headers=headers)
        self.assertEqual(apps_resp.status_code, 200)
        apps_list = apps_resp.json()
        self.assertGreater(len(apps_list), 0)
        self.assertEqual(apps_list[0]["exam_name"], "BPSC Civil Services Examination")
        self.assertIn(apps_list[0]["status"], ("applied", "submitted", "failed"))
        print(" -> Applications Listing OK")

if __name__ == "__main__":
    from fastapi.testclient import TestClient
    unittest.main()
