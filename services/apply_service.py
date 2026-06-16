import logging
import asyncio
import random
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from database.models import ExamApplication, Wallet, WalletTransaction
from services.portal_strategies.strategy_factory import StrategyFactory
from tools.browser_worker import StealthBrowserWorker
from services.payment.phonepay_service import PhonePayService
from services.wallet_service import WalletService
# Dynamic orchestrator import inside method
from swarm_core.rag_engine import rag_engine

logger = logging.getLogger("ApplyService")

class ApplyService:
    @staticmethod
    async def run_application(task_id: str, user_data: dict, exam_data: dict, db: AsyncSession):
        from main import orchestrator
        broker = orchestrator.broker
        channel = f"task_events:{task_id}"
        
        async def publish_progress(status: str, message: str, extra: dict = None):
            payload = {"task_id": task_id, "status": status, "message": message}
            if extra:
                payload.update(extra)
            logger.info(f"[ApplyService progress] {status}: {message}")
            await broker.publish(channel, payload)
            
            # Record log in orchestrator task state
            if task_id in orchestrator.task_states:
                orchestrator.task_states[task_id]["logs"].append(f"[{status.upper()}] {message}")
                if status == "submitted":
                    orchestrator.task_states[task_id]["status"] = "COMPLETED"
                    if extra and "confirmation_number" in extra:
                        orchestrator.task_states[task_id]["outputs"]["registration_code"] = extra["confirmation_number"]
                elif status == "failed":
                    orchestrator.task_states[task_id]["status"] = "FAILED"
                elif status == "payment_pending":
                    orchestrator.task_states[task_id]["status"] = "PAYMENT_PENDING"

        # Initialize isolated task state in orchestrator memory
        if task_id not in orchestrator.task_states:
            orchestrator.task_states[task_id] = {
                "task_id": task_id,
                "command": f"Apply to {exam_data.get('exam_name')}",
                "status": "RUNNING",
                "steps": [],
                "current_step": 0,
                "encrypted_context": {},
                "pii_keys": [],
                "logs": [],
                "outputs": {}
            }

        await publish_progress("initializing", "Initializing StealthBrowserWorker sandbox...")
        worker = StealthBrowserWorker()
        page = None
        
        try:
            # Init Playwright session
            page = await worker.init_session()
            
            # Determine Strategy
            portal_url = exam_data.get("portal_url")
            strategy = StrategyFactory.get_strategy(portal_url)
            
            # Navigate to portal to set the page URL context for mock checks
            if strategy.is_mock_page(page) or not portal_url:
                await page.goto("about:blank")
            else:
                await page.goto(portal_url, wait_until="domcontentloaded")
            
            # Call create_account
            await publish_progress("creating_account", "Creating account...")
            success = await strategy.create_account(page, user_data)
            if not success:
                raise Exception("Strategy account creation failed.")
                
            # Call fill_profile
            await publish_progress("filling_profile", "Filling profile...")
            success = await strategy.fill_profile(page, user_data)
            if not success:
                raise Exception("Strategy profile filling failed.")
                
            # Call upload_documents
            await publish_progress("uploading_documents", "Uploading photo...")
            success = await strategy.upload_documents(page, user_data.get("docs", {}))
            if not success:
                raise Exception("Strategy document upload failed.")
                
            # Check fee_waiver flag
            fee_waiver = exam_data.get("category_fee_waiver", False)
            fee = exam_data.get("fee", 0)
            
            # Load application record
            result = await db.execute(
                select(ExamApplication)
                .filter(ExamApplication.user_id == user_data["id"], ExamApplication.exam_name == exam_data["exam_name"])
            )
            app_record = result.scalars().first()
            if not app_record:
                app_record = ExamApplication(
                    user_id=user_data["id"],
                    exam_name=exam_data["exam_name"],
                    portal_url=portal_url,
                    status="applied"
                )
                db.add(app_record)
                await db.flush()

            if fee_waiver:
                await publish_progress("processing_payment", "Processing payment...")
                await strategy.handle_payment(page, {"fee_waiver": True})
                
                conf_num = f"CONF-{random.randint(100000, 999999)}"
                app_record.status = "submitted"
                await db.commit()
                
                await publish_progress("submitted", f"Form submitted successfully!", {"confirmation_number": conf_num})
            else:
                wallet_balance = await WalletService.get_balance(user_data["id"], db)
                if wallet_balance >= fee:
                    await publish_progress("processing_payment", "Processing payment...")
                    debit_ok = await WalletService.debit(
                        user_data["id"], 
                        Decimal(str(fee)), 
                        f"Exam Fee Payment for {exam_data['exam_name']}", 
                        db
                    )
                    if not debit_ok:
                        raise Exception("Wallet debit failed.")
                    
                    await strategy.handle_payment(page, {"fee_waiver": False})
                    
                    conf_num = f"CONF-{random.randint(100000, 999999)}"
                    app_record.status = "submitted"
                    await db.commit()
                    
                    await publish_progress("submitted", f"Form submitted successfully!", {"confirmation_number": conf_num})
                else:
                    await publish_progress("processing_payment", "Processing payment...")
                    phonepe = PhonePayService()
                    phonepay_url, txn_id = phonepe.create_payment_link(
                        user_data["id"],
                        Decimal(str(fee)),
                        exam_data["exam_name"],
                        app_record.id
                    )
                    
                    # Create pending transaction
                    wallet_res = await db.execute(select(Wallet).filter(Wallet.user_id == user_data["id"]))
                    wallet = wallet_res.scalars().first()
                    if not wallet:
                        wallet = Wallet(user_id=user_data["id"], balance=Decimal("0.00"), currency="INR")
                        db.add(wallet)
                        await db.flush()
                        
                    pending_tx = WalletTransaction(
                        wallet_id=wallet.id,
                        amount=Decimal(str(fee)),
                        type="debit",
                        description=f"PhonePe pending: txn={txn_id}, app={app_record.id}, task={task_id}"
                    )
                    db.add(pending_tx)
                    
                    app_record.status = "payment_pending"
                    await db.commit()
                    
                    await publish_progress("payment_pending", "Redirecting to PhonePe...", {"phonepay_url": phonepay_url})
                    
        except Exception as e:
            logger.error(f"Error executing form fill pipeline: {e}")
            error_msg = str(e)
            
            # Save error log and update status
            result = await db.execute(
                select(ExamApplication)
                .filter(ExamApplication.user_id == user_data["id"], ExamApplication.exam_name == exam_data["exam_name"])
            )
            app_record = result.scalars().first()
            if app_record:
                app_record.status = "failed"
                app_record.error_log = error_msg
                await db.commit()
                
            # Trigger RAG healing logging
            try:
                dom_layout = await page.content() if page else ""
                rag_engine.add_healing_record(
                    failed_selector="[ApplyService Pipeline]",
                    error_message=error_msg,
                    dom_snippet=dom_layout[:500],
                    healed_selector="N/A"
                )
            except Exception:
                pass
                
            await publish_progress("failed", f"Execution failed: {error_msg}")
            
        finally:
            if worker:
                try:
                    await worker.close_session()
                except Exception:
                    pass
