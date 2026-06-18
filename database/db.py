import os
import logging
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base

logger = logging.getLogger("Database")

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./formfill.db")

engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

Base = declarative_base()

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session

async def init_db():
    from sqlalchemy import text
    try:
        async with engine.begin() as conn:
            # Import models inside to ensure they register on Base
            from database import models
            await conn.run_sync(Base.metadata.create_all)
            
            # Execute database schema alterations on PostgreSQL if database engine is postgresql
            if "postgresql" in str(engine.url):
                await conn.execute(text("ALTER TABLE user_profiles ADD COLUMN IF NOT EXISTS pan VARCHAR(50);"))
                await conn.execute(text("ALTER TABLE user_profiles ADD COLUMN IF NOT EXISTS district VARCHAR(100);"))
                logger.info("Database user_profiles table altered successfully.")
                
            logger.info("Database tables initialized successfully.")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}. Check your PostgreSQL server.")
