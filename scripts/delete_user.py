#!/usr/bin/env python3
"""
Delete admin@test.com user.
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import AsyncSessionLocal
from app.models.user import User
from sqlalchemy import select, delete


async def delete_user():
    """Delete admin@test.com user."""
    async with AsyncSessionLocal() as db:
        # Delete admin@test.com
        result = await db.execute(
            delete(User).where(User.email == "admin@test.com")
        )
        await db.commit()

        print(f"✅ Deleted admin@test.com (rows affected: {result.rowcount})")


if __name__ == "__main__":
    asyncio.run(delete_user())
