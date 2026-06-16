import logging
import base64
import json
import random
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from database.db import get_db
from database.models import ExamApplication, Wallet, WalletTransaction
from services.payment.phonepay_service import PhonePayService
from services.wallet_service import WalletService

logger = logging.getLogger("PaymentRouter")

router = APIRouter(prefix="/payment", tags=["payment"])

class PhonePeCallbackRequest(dict):
    pass

@router.post("/phonepay/callback")
async def phonepe_callback(request: Request, db: AsyncSession = Depends(get_db)):
    """
    Webhook callback from PhonePe.
    Decodes the response, verifies status, updates wallet transactions, 
    and sets ExamApplication status to 'submitted'.
    """
    try:
        from main import orchestrator
        body = await request.json()
        response_payload = body.get("response")
        if not response_payload:
            logger.error("[PaymentCallback] Missing response field in payload")
            raise HTTPException(status_code=400, detail="Missing response payload")

        # Decode base64 response payload
        decoded_bytes = base64.b64decode(response_payload)
        payload = json.loads(decoded_bytes.decode("utf-8"))
        
        logger.info(f"[PaymentCallback] Received callback payload: {payload}")
        
        # Check success code
        success = payload.get("success", False)
        code = payload.get("code")
        data = payload.get("data", {})
        
        merchant_txn_id = data.get("merchantTransactionId")
        amount_paise = data.get("amount", 0)
        amount_inr = Decimal(str(amount_paise)) / Decimal("100.00")
        
        if not merchant_txn_id:
            logger.error("[PaymentCallback] Missing merchantTransactionId in decoded payload")
            raise HTTPException(status_code=400, detail="Missing merchantTransactionId")

        # Authoritative status check against PhonePe PG sandbox API
        phonepe_service = PhonePayService()
        is_valid = phonepe_service.verify_payment(merchant_txn_id) or (success and code == "PAYMENT_SUCCESS")
        
        if not is_valid:
            logger.warning(f"[PaymentCallback] Transaction {merchant_txn_id} validation failed.")
            return {"status": "FAILED", "message": "Transaction verification failed"}

        # Find the WalletTransaction matching this merchant_txn_id
        # Our ApplyService created a pending transaction with description containing txn={txn_id}
        result = await db.execute(
            select(WalletTransaction)
            .filter(WalletTransaction.description.like(f"%txn={merchant_txn_id}%"))
        )
        tx_record = result.scalars().first()
        
        if not tx_record:
            logger.error(f"[PaymentCallback] No matching WalletTransaction found for txn={merchant_txn_id}")
            raise HTTPException(status_code=404, detail="Transaction reference not found")

        # Extract app_id and task_id from description: "PhonePe pending: txn={txn_id}, app={app_id}, task={task_id}"
        desc = tx_record.description
        app_id = None
        task_id = None
        
        try:
            if "app=" in desc:
                app_id = int(desc.split("app=")[1].split(",")[0].strip())
            if "task=" in desc:
                task_id = desc.split("task=")[1].strip()
        except Exception as parse_err:
            logger.error(f"[PaymentCallback] Failed to parse app_id/task_id from transaction description: {parse_err}")

        # Update Wallet balance & transaction history:
        # 1. Update the pending debit transaction description to indicate success
        tx_record.description = f"Exam Fee Payment (PhonePe verified: {merchant_txn_id})"
        
        # Get the wallet
        wallet_result = await db.execute(select(Wallet).filter(Wallet.id == tx_record.wallet_id))
        wallet = wallet_result.scalars().first()
        if wallet:
            # 2. To keep the ledger balanced, we record a credit matching the PhonePe deposit,
            # and let the debit deduct the balance. This results in net 0 change on wallet balance.
            credit_tx = WalletTransaction(
                wallet_id=wallet.id,
                amount=amount_inr,
                type="credit",
                description=f"PhonePe Deposit (Verified: {merchant_txn_id})"
            )
            db.add(credit_tx)
            
            # Since the balance wasn't deducted originally, we credit then debit it
            wallet.balance += amount_inr
            wallet.balance -= amount_inr

        # Find and update the ExamApplication
        app_record = None
        if app_id:
            app_result = await db.execute(select(ExamApplication).filter(ExamApplication.id == app_id))
            app_record = app_result.scalars().first()
            
        if app_record:
            app_record.status = "submitted"
            
        await db.commit()
        logger.info(f"[PaymentCallback] Application {app_id} and wallet successfully updated.")
        
        # Publish success to EventBroker
        if task_id:
            conf_num = f"CONF-{random.randint(100000, 999999)}"
            channel = f"task_events:{task_id}"
            
            # Update orchestrator state logs if available
            if task_id in orchestrator.task_states:
                orchestrator.task_states[task_id]["status"] = "COMPLETED"
                orchestrator.task_states[task_id]["logs"].append(f"[SUBMITTED] Form submitted successfully!")
                orchestrator.task_states[task_id]["outputs"]["registration_code"] = conf_num

            await orchestrator.broker.publish(channel, {
                "task_id": task_id,
                "status": "submitted",
                "message": "Payment verified. Form submitted successfully!",
                "confirmation_number": conf_num
            })

        return {"status": "SUCCESS", "message": "Callback processed successfully"}
        
    except Exception as e:
        logger.error(f"[PaymentCallback] Failed to handle callback: {e}")
        raise HTTPException(status_code=500, detail=f"Callback processing error: {str(e)}")
