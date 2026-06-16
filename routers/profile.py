import os
import uuid
from datetime import date
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile, Form
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from database.db import get_db
from database.models import User, UserProfile, Document
from auth.auth import get_current_user, SECRET_KEY
from swarm_core.crypto_utils import derive_key, encrypt_value, decrypt_value

router = APIRouter(prefix="/profile", tags=["profile"])

# Derive key for secure Aadhaar encryption in database
DB_ENC_KEY = derive_key(SECRET_KEY)

# Pydantic models
class ProfileCreateOrUpdate(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=100)
    dob: str = Field(..., description="Date of birth in YYYY-MM-DD format")
    gender: str = Field(..., min_length=2, max_length=20)
    category: str = Field(..., description="Category, e.g., GEN, OBC, SC, ST")
    state: str = Field(..., min_length=2, max_length=50)
    qualification: str = Field(..., min_length=2, max_length=100)
    phone: Optional[str] = None
    aadhaar: Optional[str] = None
    email: Optional[EmailStr] = None

class ProfileResponse(BaseModel):
    full_name: str
    dob: str
    gender: str
    category: str
    state: str
    qualification: str
    phone: Optional[str]
    email: Optional[str]
    aadhaar_encrypted: Optional[str]
    aadhaar_decrypted: Optional[str]

class DocumentResponse(BaseModel):
    id: int
    doc_type: str
    file_path: str
    file_size: int
    uploaded_at: str

@router.post("", response_model=dict)
async def save_profile(
    payload: ProfileCreateOrUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    try:
        parsed_dob = date.fromisoformat(payload.dob)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid dob format. Must be YYYY-MM-DD."
        )

    # Check if category is valid
    if payload.category.upper() not in ("GEN", "OBC", "SC", "ST"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid category. Must be one of: GEN, OBC, SC, ST"
        )

    # Check if profile already exists for the user
    result = await db.execute(select(UserProfile).filter(UserProfile.user_id == current_user.id))
    profile = result.scalars().first()

    aadhaar_enc = None
    if payload.aadhaar:
        clean_aadhaar = payload.aadhaar.replace("-", "").replace(" ", "")
        if len(clean_aadhaar) != 12 or not clean_aadhaar.isdigit():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Aadhaar number must contain exactly 12 digits."
            )
        aadhaar_enc = encrypt_value(clean_aadhaar, DB_ENC_KEY)

    if profile:
        # Update existing profile
        profile.full_name = payload.full_name
        profile.dob = parsed_dob
        profile.gender = payload.gender
        profile.category = payload.category.upper()
        profile.state = payload.state
        profile.qualification = payload.qualification
        profile.phone = payload.phone
        if aadhaar_enc:
            profile.aadhaar_encrypted = aadhaar_enc
        profile.email = payload.email
    else:
        # Create new profile
        profile = UserProfile(
            user_id=current_user.id,
            full_name=payload.full_name,
            dob=parsed_dob,
            gender=payload.gender,
            category=payload.category.upper(),
            state=payload.state,
            qualification=payload.qualification,
            phone=payload.phone,
            aadhaar_encrypted=aadhaar_enc,
            email=payload.email
        )
        db.add(profile)

    await db.commit()
    return {"status": "SUCCESS", "message": "User profile saved successfully."}

@router.get("", response_model=ProfileResponse)
async def get_profile(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(UserProfile).filter(UserProfile.user_id == current_user.id))
    profile = result.scalars().first()
    
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User profile not found."
        )

    aadhaar_dec = None
    if profile.aadhaar_encrypted:
        try:
            aadhaar_dec = decrypt_value(profile.aadhaar_encrypted, DB_ENC_KEY)
        except Exception:
            aadhaar_dec = "Decryption Failed"

    return ProfileResponse(
        full_name=profile.full_name,
        dob=profile.dob.isoformat(),
        gender=profile.gender,
        category=profile.category,
        state=profile.state,
        qualification=profile.qualification,
        phone=profile.phone,
        email=profile.email,
        aadhaar_encrypted=profile.aadhaar_encrypted,
        aadhaar_decrypted=aadhaar_dec
    )

@router.post("/documents", response_model=dict)
async def upload_document(
    doc_type: str = Form(..., description="photo/signature/aadhaar/caste_cert/marksheet"),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    if doc_type not in ("photo", "signature", "aadhaar", "caste_cert", "marksheet"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid doc_type. Must be one of: photo, signature, aadhaar, caste_cert, marksheet"
        )

    # Save to uploads/ folder
    upload_dir = "uploads"
    os.makedirs(upload_dir, exist_ok=True)
    
    # Generate unique filename
    file_ext = os.path.splitext(file.filename)[1]
    filename = f"{current_user.id}_{doc_type}_{uuid.uuid4().hex}{file_ext}"
    file_path = os.path.join(upload_dir, filename)

    try:
        contents = await file.read()
        file_size = len(contents)
        with open(file_path, "wb") as f:
            f.write(contents)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save file: {str(e)}"
        )

    # Register in DB
    new_doc = Document(
        user_id=current_user.id,
        doc_type=doc_type,
        file_path=file_path.replace("\\", "/"), # Use standard forward slashes
        file_size=file_size
    )
    db.add(new_doc)
    await db.commit()

    return {
        "status": "SUCCESS",
        "message": f"Document of type '{doc_type}' uploaded successfully.",
        "file_path": new_doc.file_path,
        "file_size": new_doc.file_size
    }

@router.get("/documents", response_model=List[DocumentResponse])
async def list_documents(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Document).filter(Document.user_id == current_user.id))
    docs = result.scalars().all()
    
    return [
        DocumentResponse(
            id=d.id,
            doc_type=d.doc_type,
            file_path=d.file_path,
            file_size=d.file_size,
            uploaded_at=d.uploaded_at.isoformat()
        )
        for d in docs
    ]
