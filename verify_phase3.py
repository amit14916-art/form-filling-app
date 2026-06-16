import unittest
import os
import io
import asyncio
from decimal import Decimal
import database.db
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

# Override database connection before importing app to run tests in memory
database.db.engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
database.db.AsyncSessionLocal = async_sessionmaker(database.db.engine, expire_on_commit=False, class_=AsyncSession)

from main import app
from database.db import init_db
from database.models import User, UserProfile, Document, ExamApplication, Wallet, WalletTransaction
from sqlalchemy.future import select
from fastapi.testclient import TestClient

class TestPhase3Features(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        loop = asyncio.get_event_loop()
        try:
            loop.run_until_complete(init_db())
            print("[setUpClass] SQLite In-Memory Database initialized.")
        except Exception as e:
            print(f"[setUpClass] Init failed: {e}")

    def setUp(self):
        self.client = TestClient(app)
        self.email_sc = "sc_candidate@example.com"
        self.email_gen = "gen_candidate@example.com"
        self.password = "securepass123"
        self.phone = "9876543210"

    def get_auth_headers(self, email):
        self.client.post(
            "/auth/register",
            json={"email": email, "password": self.password, "phone": self.phone}
        )
        login_resp = self.client.post(
            "/auth/login",
            json={"email": email, "password": self.password}
        )
        token = login_resp.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}

    def test_apply_flow_sc_fee_waiver(self):
        print("\n--- Test 1: SC Candidate (Fee Waiver Exemption) ---")
        headers = self.get_auth_headers(self.email_sc)
        
        # 1. Create SC Profile
        profile_data = {
            "full_name": "SC Candidate",
            "dob": "1998-05-15",
            "gender": "Female",
            "category": "SC",
            "state": "Bihar",
            "qualification": "Graduate",
            "phone": "9876543210",
            "aadhaar": "987654321098",
            "email": self.email_sc
        }
        self.client.post("/profile", json=profile_data, headers=headers)
        
        # 2. Upload mock documents
        for doc_type in ["photo", "signature", "aadhaar"]:
            self.client.post(
                "/profile/documents",
                data={"doc_type": doc_type},
                files={"file": (f"{doc_type}.jpg", b"mock content", "image/jpeg")},
                headers=headers
            )
            
        # 3. Apply for UPSC Civil Services Examination (Exempted)
        apply_resp = self.client.post(
            "/exams/apply/UPSC Civil Services Examination",
            json={"passphrase": "mypass123"},
            headers=headers
        )
        self.assertEqual(apply_resp.status_code, 200)
        data = apply_resp.json()
        self.assertIn("task_id", data)
        self.assertIn("websocket_url", data)
        
        # 4. Wait for background task to complete
        import time
        time.sleep(1)
        
        # Query DB to check status
        async def check_db_submitted():
            async with database.db.AsyncSessionLocal() as session:
                res = await session.execute(select(ExamApplication).filter(ExamApplication.exam_name == "UPSC Civil Services Examination"))
                app_rec = res.scalars().first()
                return app_rec
                
        loop = asyncio.get_event_loop()
        app_rec = loop.run_until_complete(check_db_submitted())
        self.assertIsNotNone(app_rec)
        self.assertEqual(app_rec.status, "submitted")
        print(" -> SC Candidate Form auto-applied directly with status='submitted'.")

    def test_apply_flow_gen_sufficient_wallet(self):
        print("\n--- Test 2: GEN Candidate (Sufficient Wallet Balance) ---")
        headers = self.get_auth_headers(self.email_gen)
        
        # 1. Create GEN Profile
        profile_data = {
            "full_name": "GEN Candidate",
            "dob": "1998-05-15",
            "gender": "Male",
            "category": "GEN",
            "state": "Bihar",
            "qualification": "Graduate",
            "phone": "8888888888",
            "aadhaar": "111122223333",
            "email": self.email_gen
        }
        self.client.post("/profile", json=profile_data, headers=headers)
        
        # 2. Upload documents
        for doc_type in ["photo", "signature", "aadhaar"]:
            self.client.post(
                "/profile/documents",
                data={"doc_type": doc_type},
                files={"file": (f"{doc_type}.jpg", b"mock content", "image/jpeg")},
                headers=headers
            )
            
        # 3. Add funds to wallet (100 INR for UPSC)
        dep_resp = self.client.post(
            "/dashboard/wallet/deposit",
            json={"amount": 100.0, "description": "Add funds for UPSC"},
            headers=headers
        )
        self.assertEqual(dep_resp.status_code, 200)
        
        # 4. Apply for UPSC Civil Services Examination
        apply_resp = self.client.post(
            "/exams/apply/UPSC Civil Services Examination",
            json={"passphrase": "mypass123"},
            headers=headers
        )
        self.assertEqual(apply_resp.status_code, 200)
        
        import time
        time.sleep(1)
        
        async def check_db_wallet_and_app():
            async with database.db.AsyncSessionLocal() as session:
                res_app = await session.execute(
                    select(ExamApplication)
                    .filter(ExamApplication.exam_name == "UPSC Civil Services Examination", ExamApplication.status == "submitted")
                )
                app_rec = res_app.scalars().all()
                return app_rec
                
        loop = asyncio.get_event_loop()
        apps = loop.run_until_complete(check_db_wallet_and_app())
        self.assertGreater(len(apps), 0)
        print(" -> Wallet debit successful, application status set to 'submitted'.")

    def test_apply_flow_gen_insufficient_wallet_phonepe(self):
        print("\n--- Test 3: GEN Candidate (Insufficient Wallet Balance -> PhonePe) ---")
        email_insufficient = "insufficient_candidate@example.com"
        headers = self.get_auth_headers(email_insufficient)
        
        # 1. Create GEN Profile
        profile_data = {
            "full_name": "GEN Candidate 2",
            "dob": "1998-05-15",
            "gender": "Male",
            "category": "GEN",
            "state": "Bihar",
            "qualification": "Graduate",
            "phone": "7777777777",
            "aadhaar": "444455556666",
            "email": email_insufficient
        }
        self.client.post("/profile", json=profile_data, headers=headers)
        
        # 2. Upload documents
        for doc_type in ["photo", "signature", "aadhaar"]:
            self.client.post(
                "/profile/documents",
                data={"doc_type": doc_type},
                files={"file": (f"{doc_type}.jpg", b"mock content", "image/jpeg")},
                headers=headers
            )
            
        # 3. Apply for UPSC Civil Services Examination
        apply_resp = self.client.post(
            "/exams/apply/UPSC Civil Services Examination",
            json={"passphrase": "mypass123"},
            headers=headers
        )
        self.assertEqual(apply_resp.status_code, 200)
        
        import time
        time.sleep(1)
        
        async def get_app_and_tx():
            async with database.db.AsyncSessionLocal() as session:
                res_app = await session.execute(
                    select(ExamApplication)
                    .filter(ExamApplication.exam_name == "UPSC Civil Services Examination", ExamApplication.status == "payment_pending")
                )
                app_rec = res_app.scalars().first()
                
                res_tx = await session.execute(
                    select(WalletTransaction)
                    .filter(WalletTransaction.description.like("%PhonePe pending%"))
                )
                tx_rec = res_tx.scalars().first()
                return app_rec, tx_rec
                
        loop = asyncio.get_event_loop()
        app_rec, tx_rec = loop.run_until_complete(get_app_and_tx())
        self.assertIsNotNone(app_rec)
        self.assertIsNotNone(tx_rec)
        self.assertEqual(app_rec.status, "payment_pending")
        print(" -> Insufficient funds routed correctly to payment_pending status.")
        
        # Extract transaction ID from pending transaction description
        desc = tx_rec.description
        txn_id = desc.split("txn=")[1].split(",")[0].strip()
        
        # 4. Trigger Webhook callback to simulate PhonePe success
        import base64
        import json
        callback_payload = {
            "success": True,
            "code": "PAYMENT_SUCCESS",
            "data": {
                "merchantTransactionId": txn_id,
                "amount": 10000  # 100 INR in paise
            }
        }
        encoded_payload = base64.b64encode(json.dumps(callback_payload).encode("utf-8")).decode("utf-8")
        
        callback_resp = self.client.post(
            "/api/v1/payment/phonepay/callback",
            json={"response": encoded_payload}
        )
        self.assertEqual(callback_resp.status_code, 200)
        self.assertEqual(callback_resp.json()["status"], "SUCCESS")
        
        # Verify app status is now 'submitted' in DB
        async def verify_final_status():
            async with database.db.AsyncSessionLocal() as session:
                res = await session.execute(select(ExamApplication).filter(ExamApplication.id == app_rec.id))
                return res.scalars().first()
                
        final_app = loop.run_until_complete(verify_final_status())
        self.assertEqual(final_app.status, "submitted")
        print(" -> PhonePe callback successfully verified, status updated to 'submitted'.")

if __name__ == "__main__":
    unittest.main()
