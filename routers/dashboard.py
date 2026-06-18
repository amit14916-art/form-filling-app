from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from decimal import Decimal
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from database.db import get_db
from database.models import User, UserProfile, Document, ExamApplication, Wallet, WalletTransaction
from auth.auth import get_current_user
from services.eligibility_engine import EligibilityEngine

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

class DepositRequest(BaseModel):
    amount: Decimal = Field(..., gt=0, description="Amount in INR to deposit")
    description: Optional[str] = Field("Testing Wallet Deposit", description="Description of the transaction")

class TransactionResponse(BaseModel):
    id: int
    amount: Decimal
    type: str
    description: str
    created_at: str

class ApplicationSummary(BaseModel):
    id: int
    exam_name: str
    portal_url: str
    status: str
    applied_at: str

class DashboardStatsResponse(BaseModel):
    wallet_balance: Decimal
    currency: str
    total_applications: int
    status_breakdown: Dict[str, int]
    documents_uploaded_count: int
    eligible_exams_count: int
    recent_applications: List[ApplicationSummary]
    recent_transactions: List[TransactionResponse]
    eligible_count: int
    applied_count: int
    free_count: int

@router.get("/stats", response_model=DashboardStatsResponse)
async def get_dashboard_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # 1. Fetch user wallet
    result = await db.execute(select(Wallet).filter(Wallet.user_id == current_user.id))
    wallet = result.scalars().first()
    if not wallet:
        wallet = Wallet(user_id=current_user.id, balance=Decimal("0.00"), currency="INR")
        db.add(wallet)
        await db.commit()
        await db.refresh(wallet)

    # 2. Fetch all applications
    result_apps = await db.execute(select(ExamApplication).filter(ExamApplication.user_id == current_user.id))
    apps = result_apps.scalars().all()
    
    total_apps = len(apps)
    status_counts = {"eligible": 0, "applied": 0, "payment_pending": 0, "submitted": 0, "failed": 0}
    for a in apps:
        if a.status in status_counts:
            status_counts[a.status] += 1
        else:
            status_counts[a.status] = 1

    # Sort applications for recent list
    sorted_apps = sorted(apps, key=lambda x: x.applied_at, reverse=True)[:5]
    recent_apps_res = [
        ApplicationSummary(
            id=a.id,
            exam_name=a.exam_name,
            portal_url=a.portal_url,
            status=a.status,
            applied_at=a.applied_at.isoformat()
        )
        for a in sorted_apps
    ]

    # 3. Fetch count of uploaded documents
    result_docs = await db.execute(select(Document).filter(Document.user_id == current_user.id))
    docs_count = len(result_docs.scalars().all())

    # 4. Fetch eligibility report
    eligibility_report = await EligibilityEngine.check_user_eligibility(current_user.id, db)
    eligible_count = sum(1 for e in eligibility_report if e["eligible"])
    free_count = sum(1 for e in eligibility_report if e["eligible"] and (e.get("fee") == 0 or e.get("category_fee_waiver") is True))

    # 5. Fetch recent transactions
    result_tx = await db.execute(
        select(WalletTransaction)
        .filter(WalletTransaction.wallet_id == wallet.id)
        .order_by(WalletTransaction.created_at.desc())
        .limit(5)
    )
    txs = result_tx.scalars().all()
    recent_tx_res = [
        TransactionResponse(
            id=t.id,
            amount=t.amount,
            type=t.type,
            description=t.description or "",
            created_at=t.created_at.isoformat()
        )
        for t in txs
    ]

    return DashboardStatsResponse(
        wallet_balance=wallet.balance,
        currency=wallet.currency,
        total_applications=total_apps,
        status_breakdown=status_counts,
        documents_uploaded_count=docs_count,
        eligible_exams_count=eligible_count,
        recent_applications=recent_apps_res,
        recent_transactions=recent_tx_res,
        eligible_count=eligible_count,
        applied_count=total_apps,
        free_count=free_count
    )

@router.post("/wallet/deposit", response_model=dict)
async def wallet_deposit(
    payload: DepositRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Fetch user wallet
    result = await db.execute(select(Wallet).filter(Wallet.user_id == current_user.id))
    wallet = result.scalars().first()
    if not wallet:
        wallet = Wallet(user_id=current_user.id, balance=Decimal("0.00"), currency="INR")
        db.add(wallet)
        await db.flush()

    # Credit amount
    wallet.balance += payload.amount
    
    # Register transaction
    tx = WalletTransaction(
        wallet_id=wallet.id,
        amount=payload.amount,
        type="credit",
        description=payload.description
    )
    db.add(tx)
    await db.commit()
    await db.refresh(wallet)

    return {
        "status": "SUCCESS",
        "message": f"Successfully deposited {payload.amount} {wallet.currency}.",
        "new_balance": wallet.balance
    }
