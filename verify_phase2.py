import unittest
import os
import io
import asyncio
from decimal import Decimal

# Override database connection before importing app to run tests in memory
import database.db
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

database.db.engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
database.db.AsyncSessionLocal = async_sessionmaker(database.db.engine, expire_on_commit=False, class_=AsyncSession)

from main import app
from database.db import init_db
from database.models import User, UserProfile, Document, ExamApplication, Wallet, WalletTransaction
from sqlalchemy.future import select

class TestPhase2Features(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Initialize SQLite database
        loop = asyncio.get_event_loop()
        try:
            loop.run_until_complete(init_db())
            print("[setUpClass] SQLite In-Memory Database tables initialized successfully.")
        except Exception as e:
            print(f"[setUpClass] SQLite Database initialization failed: {e}")

    def setUp(self):
        from fastapi.testclient import TestClient
        self.client = TestClient(app)
        
        # Test accounts details
        import uuid
        self.email1 = f"candidate_sc_{uuid.uuid4().hex[:8]}@example.com"
        self.email2 = f"candidate_gen_{uuid.uuid4().hex[:8]}@example.com"
        self.password = "securepass123"
        self.phone = "9876543210"

    def get_auth_headers(self, email):
        # Register and login helper
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

    def test_eligibility_engine_and_wallet_transactions(self):
        print("\n--- Running Phase 2 Eligibility Engine & Wallet E2E Flow ---")
        
        headers = self.get_auth_headers(self.email1)

        # 1. Setup profile for SC Candidate from Bihar
        print("[Step 1] Creating SC User Profile (Bihar, Graduate)...")
        profile_data = {
            "full_name": "SC Candidate Bihar",
            "dob": "1995-04-10",
            "gender": "Female",
            "category": "SC",
            "state": "Bihar",
            "qualification": "Graduate",
            "phone": "9876543210",
            "aadhaar": "111122223333",
            "email": self.email1
        }
        prof_resp = self.client.post("/profile", json=profile_data, headers=headers)
        self.assertEqual(prof_resp.status_code, 200)

        # 2. Check eligibility (UPSC, SSC CGL and BPSC should be eligible, with category fee waiver = True)
        print("[Step 2] Querying eligible exams for SC Candidate...")
        elig_resp = self.client.get("/exams/eligible", headers=headers)
        self.assertEqual(elig_resp.status_code, 200)
        exams = elig_resp.json()
        self.assertGreater(len(exams), 0)
        
        # Validate that category fee waiver is True for all (since candidate is SC and Female)
        for ex in exams:
            self.assertTrue(ex["category_fee_waiver"])
        print(" -> All eligible exams have category_fee_waiver = True.")

        # 3. Setup profile for GEN Candidate from Uttar Pradesh (Male, Age 40 - should be ineligible due to age)
        print("[Step 3] Creating Gen User Profile (Uttar Pradesh, Overage)...")
        headers_gen = self.get_auth_headers(self.email2)
        profile_data_gen = {
            "full_name": "Overage Gen Candidate",
            "dob": "1980-01-01",  # Age ~46
            "gender": "Male",
            "category": "GEN",
            "state": "Uttar Pradesh",
            "qualification": "Graduate",
            "phone": "8888888888",
            "aadhaar": "444455556666",
            "email": self.email2
        }
        prof_gen_resp = self.client.post("/profile", json=profile_data_gen, headers=headers_gen)
        self.assertEqual(prof_gen_resp.status_code, 200)

        # 4. Check eligibility for overage candidate (should be empty/ineligible for all)
        print("[Step 4] Checking overage candidate eligibility...")
        elig_gen_resp = self.client.get("/exams/eligible", headers=headers_gen)
        self.assertEqual(elig_gen_resp.status_code, 200)
        exams_gen = elig_gen_resp.json()
        self.assertEqual(len(exams_gen), 0, "Overage candidate (age 46, GEN) should have no eligible exams.")
        print(" -> Verified overage candidate has 0 eligible exams.")

        # 5. Test Wallet Deposit
        print("[Step 5] Depositing 200 INR to GEN candidate wallet...")
        # Since he is GEN, UPPSC exam will require fee payment (if he were younger, but let's update profile to be eligible first)
        # Let's make him younger (dob: 2000-01-01 -> age ~26)
        profile_data_gen["dob"] = "2000-01-01"
        prof_gen_resp = self.client.post("/profile", json=profile_data_gen, headers=headers_gen)
        self.assertEqual(prof_gen_resp.status_code, 200)

        # Deposit funds
        dep_resp = self.client.post(
            "/dashboard/wallet/deposit",
            json={"amount": 200.00, "description": "Seed Deposit"},
            headers=headers_gen
        )
        self.assertEqual(dep_resp.status_code, 200)
        self.assertEqual(float(dep_resp.json()["new_balance"]), 200.00)
        print(" -> Wallet deposit OK. Balance: 200.00")

        # 6. Apply with insufficient funds
        # Young GEN UPPSC exam fee is 500. Wallet balance is 200. Should fail.
        print("[Step 6] Attempting to apply for UPPSC exam (fee 500, wallet 200)...")
        apply_fail_resp = self.client.post(
            "/exams/apply/UPPSC Combined State Services (PCS)",
            json={"passphrase": "some_passphrase"},
            headers=headers_gen
        )
        self.assertEqual(apply_fail_resp.status_code, 400)
        self.assertIn("Insufficient wallet balance", apply_fail_resp.json()["detail"])
        print(" -> Application rejected due to insufficient balance (Correct)")

        # 7. Apply with sufficient funds (deposit 300 more to make balance 500)
        print("[Step 7] Depositing 300 INR more...")
        self.client.post(
            "/dashboard/wallet/deposit",
            json={"amount": 300.00, "description": "Top Up Deposit"},
            headers=headers_gen
        )
        
        print("[Step 8] Applying with sufficient funds...")
        apply_success_resp = self.client.post(
            "/exams/apply/UPPSC Combined State Services (PCS)",
            json={"passphrase": "some_passphrase"},
            headers=headers_gen
        )
        self.assertEqual(apply_success_resp.status_code, 200)
        apply_success_data = apply_success_resp.json()
        self.assertEqual(apply_success_data["status"], "SUCCESS")
        self.assertEqual(float(apply_success_data["deducted_fee"]), 500.00)
        print(" -> Application successful. Fee 500.00 deducted.")

        # 8. Check Dashboard Stats and Ledger
        print("[Step 9] Fetching dashboard stats...")
        stats_resp = self.client.get("/dashboard/stats", headers=headers_gen)
        self.assertEqual(stats_resp.status_code, 200)
        stats = stats_resp.json()
        
        self.assertEqual(float(stats["wallet_balance"]), 0.00)
        # Transactions should contain credit of 200, credit of 300, and debit of 500 (order desc: debit 500, credit 300, credit 200)
        txs = stats["recent_transactions"]
        self.assertEqual(len(txs), 3)
        self.assertEqual(txs[0]["type"], "debit")
        self.assertEqual(float(txs[0]["amount"]), 500.00)
        self.assertEqual(txs[1]["type"], "credit")
        self.assertEqual(float(txs[1]["amount"]), 300.00)
        self.assertEqual(txs[2]["type"], "credit")
        self.assertEqual(float(txs[2]["amount"]), 200.00)
        print(" -> Dashboard stats and ledger audited successfully.")

if __name__ == "__main__":
    unittest.main()
