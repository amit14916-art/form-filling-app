import logging
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from database.models import Wallet, WalletTransaction

logger = logging.getLogger("WalletService")

class WalletService:
    @staticmethod
    async def get_balance(user_id: int, db: AsyncSession) -> Decimal:
        result = await db.execute(select(Wallet).filter(Wallet.user_id == user_id))
        wallet = result.scalars().first()
        if not wallet:
            return Decimal("0.00")
        return wallet.balance

    @staticmethod
    async def debit(user_id: int, amount: Decimal, description: str, db: AsyncSession) -> bool:
        result = await db.execute(select(Wallet).filter(Wallet.user_id == user_id))
        wallet = result.scalars().first()
        if not wallet or wallet.balance < amount:
            return False
        wallet.balance -= amount
        tx = WalletTransaction(
            wallet_id=wallet.id,
            amount=amount,
            type="debit",
            description=description
        )
        db.add(tx)
        return True

    @staticmethod
    async def credit(user_id: int, amount: Decimal, description: str, db: AsyncSession) -> bool:
        result = await db.execute(select(Wallet).filter(Wallet.user_id == user_id))
        wallet = result.scalars().first()
        if not wallet:
            wallet = Wallet(user_id=user_id, balance=Decimal("0.00"), currency="INR")
            db.add(wallet)
            await db.flush()
        wallet.balance += amount
        tx = WalletTransaction(
            wallet_id=wallet.id,
            amount=amount,
            type="credit",
            description=description
        )
        db.add(tx)
        return True
