import asyncio
from datetime import date, datetime
from typing import Optional, List
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from database.db import get_db, AsyncSessionLocal
from database.models import User, UserProfile, ExamApplication, Wallet, WalletTransaction, Document
from auth.auth import get_current_user, SECRET_KEY
from swarm_core.crypto_utils import derive_key, decrypt_value
from swarm_core.exam_data_seed import EXAM_DATABASE
from services.eligibility_engine import EligibilityEngine

router = APIRouter(prefix="/exams", tags=["exams"])

# Derive key for secure Aadhaar decryption
DB_ENC_KEY = derive_key(SECRET_KEY)

class ApplyRequest(BaseModel):
    passphrase: Optional[str] = Field(None, description="Passphrase to decrypt user's details for form filling")

class EligibleExamResponse(BaseModel):
    exam_name: str
    portal_url: str
    fee: int
    category_fee_waiver: bool

class ApplicationResponse(BaseModel):
    id: int
    exam_name: str
    portal_url: str
    status: str
    applied_at: str

async def monitor_and_update_application(task_id: str, app_id: int):
    """
    Background worker that polls orchestrator task status and syncs it with the DB.
    """
    from main import orchestrator
    while True:
        await asyncio.sleep(2)
        state = orchestrator.task_states.get(task_id)
        if state:
            status_str = state.get("status")
            db_status = "applied"
            if status_str == "COMPLETED":
                db_status = "submitted"
            elif status_str == "FAILED":
                db_status = "failed"
            elif status_str == "RUNNING":
                db_status = "applied"

            async with AsyncSessionLocal() as session:
                stmt = select(ExamApplication).filter(ExamApplication.id == app_id)
                res = await session.execute(stmt)
                record = res.scalars().first()
                if record:
                    record.status = db_status
                    await session.commit()

            if status_str in ("COMPLETED", "FAILED"):
                break
        else:
            break

@router.get("/eligible", response_model=List[EligibleExamResponse])
async def get_eligible_exams(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Fetch profile
    result = await db.execute(select(UserProfile).filter(UserProfile.user_id == current_user.id))
    profile = result.scalars().first()
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="UserProfile must be created before checking exam eligibility."
        )

    # Call the new EligibilityEngine
    report = await EligibilityEngine.check_user_eligibility(current_user.id, db)
    
    # Filter to only return eligible exams
    eligible_only = [
        EligibleExamResponse(
            exam_name=e["exam_name"],
            portal_url=e["portal_url"],
            fee=e["fee"],
            category_fee_waiver=e["category_fee_waiver"]
        )
        for e in report if e["eligible"]
    ]

    return eligible_only

async def run_application_bg(task_id: str, user_data: dict, exam_data: dict):
    from services.apply_service import ApplyService
    async with AsyncSessionLocal() as session:
        await ApplyService.run_application(task_id, user_data, exam_data, session)

@router.post("/apply/{exam_name}", response_model=dict)
async def apply_exam(
    exam_name: str,
    payload: ApplyRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    import uuid
    # Fetch profile
    result = await db.execute(select(UserProfile).filter(UserProfile.user_id == current_user.id))
    profile = result.scalars().first()
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="UserProfile must be created before applying for exams."
        )

    # Check eligibility and exam details via EligibilityEngine
    eligibility_report = await EligibilityEngine.check_user_eligibility(current_user.id, db)
    exam_info = None
    for e in eligibility_report:
        if e["exam_name"].strip().lower() == exam_name.strip().lower():
            exam_info = e
            break

    if not exam_info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Exam '{exam_name}' not found."
        )

    if not exam_info["eligible"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Candidate is not eligible for this exam. Reasons: {', '.join(exam_info['reasons'])}"
        )

    # Fetch user documents
    docs_result = await db.execute(select(Document).filter(Document.user_id == current_user.id))
    documents = docs_result.scalars().all()
    docs_dict = {doc.doc_type: doc.file_path for doc in documents}

    # Decrypt Aadhaar
    aadhaar_dec = ""
    if profile.aadhaar_encrypted:
        try:
            aadhaar_dec = decrypt_value(profile.aadhaar_encrypted, DB_ENC_KEY)
        except Exception:
            pass

    # Build complete user_data dict
    user_data = {
        "id": current_user.id,
        "full_name": profile.full_name,
        "dob": profile.dob,
        "gender": profile.gender,
        "category": profile.category,
        "state": profile.state,
        "qualification": profile.qualification,
        "phone": profile.phone or current_user.phone,
        "email": profile.email or current_user.email,
        "aadhaar": aadhaar_dec,
        "docs": docs_dict
    }

    exam_data = {
        "exam_name": exam_info["exam_name"],
        "portal_url": exam_info["portal_url"],
        "fee": exam_info["fee"],
        "category_fee_waiver": exam_info["category_fee_waiver"]
    }

    task_id = f"APPLY-{uuid.uuid4().hex[:12].upper()}"

    # Submit run_application as BackgroundTask
    background_tasks.add_task(run_application_bg, task_id, user_data, exam_data)

    return {
        "task_id": task_id,
        "websocket_url": f"/ws/{task_id}"
    }

@router.get("/applications", response_model=List[ApplicationResponse])
async def list_applications(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(ExamApplication).filter(ExamApplication.user_id == current_user.id))
    apps = result.scalars().all()
    
    return [
        ApplicationResponse(
            id=a.id,
            exam_name=a.exam_name,
            portal_url=a.portal_url,
            status=a.status,
            applied_at=a.applied_at.isoformat()
        )
        for a in apps
    ]
