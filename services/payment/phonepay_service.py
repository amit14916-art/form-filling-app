import os
import base64
import hashlib
import json
import logging
import uuid
import requests
from decimal import Decimal
from typing import Tuple

logger = logging.getLogger("PhonePayService")

class PhonePayService:
    def __init__(self):
        # Read from env or use sandbox defaults
        self.merchant_id = os.getenv("PHONEPAY_MERCHANT_ID", "PGPLAYMERCHANT")
        self.salt_key = os.getenv("PHONEPAY_SALT_KEY", "099eb0cd-02cf-4e2a-8aca-3e6c6aff0399")
        self.salt_index = os.getenv("PHONEPAY_SALT_INDEX", "1")
        self.base_url = "https://api-preprod.phonepe.com/apis/pg-sandbox/pg/v1/pay"

    def create_payment_link(self, user_id: int, amount: Decimal, exam_name: str, application_id: int) -> Tuple[str, str]:
        """
        Creates a base64 request payload for PhonePe PG and generates the payment gateway redirect url.
        """
        transaction_id = f"TXN-{uuid.uuid4().hex[:12].upper()}"
        amount_in_paise = int(amount * 100)

        # Build standard redirect flow payload
        payload = {
            "merchantId": self.merchant_id,
            "merchantTransactionId": transaction_id,
            "merchantUserId": f"USER-{user_id}",
            "amount": amount_in_paise,
            "redirectUrl": f"http://localhost:8000/dashboard?txn_id={transaction_id}&app_id={application_id}",
            "callbackUrl": "http://localhost:8000/api/v1/payment/phonepay/callback",
            "mobileNumber": "9999999999",
            "paymentInstrument": {
                "type": "PAY_PAGE"
            }
        }

        # Base64 encode json payload
        json_payload = json.dumps(payload)
        base64_payload = base64.b64encode(json_payload.encode("utf-8")).decode("utf-8")

        # Create X-VERIFY header: SHA256(base64Payload + "/pg/v1/pay" + saltKey) + "###" + saltIndex
        main_string = base64_payload + "/pg/v1/pay" + self.salt_key
        sha256_hash = hashlib.sha256(main_string.encode("utf-8")).hexdigest()
        x_verify = f"{sha256_hash}###{self.salt_index}"

        headers = {
            "Content-Type": "application/json",
            "X-VERIFY": x_verify
        }
        
        req_body = {
            "request": base64_payload
        }

        try:
            logger.info(f"[PhonePayService] Sending request to sandbox for transaction {transaction_id}...")
            response = requests.post(self.base_url, json=req_body, headers=headers, timeout=10)
            res_data = response.json()
            if res_data.get("success") and "data" in res_data:
                redirect_url = res_data["data"]["instrumentResponse"]["redirectInfo"]["url"]
                logger.info(f"[PhonePayService] Successfully obtained sandbox redirect URL: {redirect_url}")
                return redirect_url, transaction_id
        except Exception as err:
            logger.error(f"[PhonePayService] API call failed, generating simulated sandbox checkout URL: {err}")
            
        # Simulated Sandbox checkout link fallback
        simulated_url = f"https://api-preprod.phonepe.com/apis/pg-sandbox/pg/v1/pay/redirect/{self.merchant_id}/{transaction_id}"
        return simulated_url, transaction_id

    def verify_payment(self, transaction_id: str) -> bool:
        """
        Queries PhonePe transaction status API to check if payment was captured.
        """
        path = f"/pg/v1/status/{self.merchant_id}/{transaction_id}"
        main_string = path + self.salt_key
        sha256_hash = hashlib.sha256(main_string.encode("utf-8")).hexdigest()
        x_verify = f"{sha256_hash}###{self.salt_index}"

        headers = {
            "Content-Type": "application/json",
            "X-VERIFY": x_verify,
            "X-MERCHANT-ID": self.merchant_id
        }

        url = f"https://api-preprod.phonepe.com/apis/pg-sandbox/pg/v1/status/{self.merchant_id}/{transaction_id}"
        try:
            logger.info(f"[PhonePayService] Verifying status for transaction {transaction_id}...")
            response = requests.get(url, headers=headers, timeout=10)
            res_data = response.json()
            if res_data.get("success") and res_data.get("code") == "PAYMENT_SUCCESS":
                logger.info(f"[PhonePayService] Transaction {transaction_id} verified as successful.")
                return True
        except Exception as e:
            logger.error(f"[PhonePayService] Transaction status query failed: {e}")
        return False
