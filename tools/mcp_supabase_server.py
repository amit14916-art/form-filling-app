import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
from mcp.server.fastmcp import FastMCP
from sqlalchemy import text
from sqlalchemy.future import select
from database.db import AsyncSessionLocal
from database.models import User, UserProfile, ExamApplication, Wallet

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("MCPSupabaseServer")

mcp = FastMCP("SupabaseConnector")

@mcp.tool()
async def supabase_execute_query(sql_query: str) -> str:
    """
    Executes a raw read-only SQL query on the Supabase database and returns results as formatted text.
    Only SELECT statements are allowed for read-only safety.
    """
    if not sql_query.strip().lower().startswith("select"):
        return "ERROR: Only SELECT queries are permitted for safety."
    
    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(text(sql_query))
            rows = result.fetchall()
            keys = result.keys()
            if not rows:
                return "Query returned 0 rows."
            
            output = [", ".join(keys)]
            for r in rows:
                output.append(", ".join(str(val) for val in r))
            return "\n".join(output)
    except Exception as e:
        logger.error(f"[MCPSupabaseServer] Query execution failed: {e}")
        return f"ERROR: Query failed: {str(e)}"

@mcp.tool()
async def supabase_get_user_by_email(email: str) -> str:
    """
    Retrieves user information from Supabase using the email address.
    """
    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(User).filter(User.email == email))
            user = result.scalars().first()
            if not user:
                return f"User not found with email: {email}"
            return f"User ID: {user.id}, Email: {user.email}, Phone: {user.phone}, Created At: {user.created_at}"
    except Exception as e:
        return f"ERROR: Failed to retrieve user: {str(e)}"

@mcp.tool()
async def supabase_get_user_profile(user_id: int) -> str:
    """
    Retrieves user profile details from Supabase using the user ID.
    """
    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(UserProfile).filter(UserProfile.user_id == user_id))
            profile = result.scalars().first()
            if not profile:
                return f"Profile not found for user ID: {user_id}"
            return (
                f"Profile ID: {profile.id}, Name: {profile.full_name}, DOB: {profile.dob}, "
                f"Gender: {profile.gender}, Category: {profile.category}, State: {profile.state}, "
                f"Qualification: {profile.qualification}"
            )
    except Exception as e:
        return f"ERROR: Failed to retrieve user profile: {str(e)}"

@mcp.tool()
async def supabase_get_exam_applications(user_id: int) -> str:
    """
    Lists all exam applications submitted by the user.
    """
    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(ExamApplication).filter(ExamApplication.user_id == user_id))
            apps = result.scalars().all()
            if not apps:
                return f"No applications found for user ID: {user_id}"
            
            output = []
            for app in apps:
                output.append(f"App ID: {app.id}, Exam: {app.exam_name}, Status: {app.status}, Applied At: {app.applied_at}")
            return "\n".join(output)
    except Exception as e:
        return f"ERROR: Failed to retrieve applications: {str(e)}"

@mcp.tool()
async def supabase_get_wallet_balance(user_id: int) -> str:
    """
    Retrieves wallet balance for the given user ID.
    """
    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(Wallet).filter(Wallet.user_id == user_id))
            wallet = result.scalars().first()
            if not wallet:
                return f"Wallet not found for user ID: {user_id}"
            return f"Wallet ID: {wallet.id}, Balance: {wallet.balance} {wallet.currency}"
    except Exception as e:
        return f"ERROR: Failed to retrieve wallet: {str(e)}"

if __name__ == "__main__":
    mcp.run()
