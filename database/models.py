from datetime import datetime
from decimal import Decimal
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Date, Numeric
from sqlalchemy.orm import relationship
from database.db import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    phone = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    profile = relationship("UserProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")
    documents = relationship("Document", back_populates="user", cascade="all, delete-orphan")
    applications = relationship("ExamApplication", back_populates="user", cascade="all, delete-orphan")
    wallet = relationship("Wallet", back_populates="user", uselist=False, cascade="all, delete-orphan")

class UserProfile(Base):
    __tablename__ = "user_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True, nullable=False)
    full_name = Column(String, nullable=False)
    dob = Column(Date, nullable=False)
    gender = Column(String, nullable=False)
    category = Column(String, nullable=False)  # GEN/OBC/SC/ST
    state = Column(String, nullable=False)
    qualification = Column(String, nullable=False)
    phone = Column(String, nullable=True)
    aadhaar_encrypted = Column(String, nullable=True)
    email = Column(String, nullable=True)
    pan = Column(String, nullable=True)
    district = Column(String, nullable=True)

    # Relationships
    user = relationship("User", back_populates="profile")

class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    doc_type = Column(String, nullable=False)  # photo/signature/aadhaar/caste_cert/marksheet
    file_path = Column(String, nullable=False)
    file_size = Column(Integer, nullable=False)
    uploaded_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="documents")

class ExamApplication(Base):
    __tablename__ = "exam_applications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    exam_name = Column(String, nullable=False)
    portal_url = Column(String, nullable=False)
    status = Column(String, default="eligible")  # eligible/applied/payment_pending/submitted/failed
    applied_at = Column(DateTime, default=datetime.utcnow)
    error_log = Column(String, nullable=True)

    # Relationships
    user = relationship("User", back_populates="applications")

class Wallet(Base):
    __tablename__ = "wallets"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True, nullable=False)
    balance = Column(Numeric(precision=10, scale=2), default=Decimal("0.00"), nullable=False)
    currency = Column(String, default="INR", nullable=False)

    # Relationships
    user = relationship("User", back_populates="wallet")
    transactions = relationship("WalletTransaction", back_populates="wallet", cascade="all, delete-orphan")

class WalletTransaction(Base):
    __tablename__ = "wallet_transactions"

    id = Column(Integer, primary_key=True, index=True)
    wallet_id = Column(Integer, ForeignKey("wallets.id", ondelete="CASCADE"), nullable=False)
    amount = Column(Numeric(precision=10, scale=2), nullable=False)
    type = Column(String, nullable=False)  # credit/debit
    description = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    wallet = relationship("Wallet", back_populates="transactions")
