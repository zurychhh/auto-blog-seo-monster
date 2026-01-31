#!/usr/bin/env python3
"""
List all users in the database.
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import AsyncSessionLocal
from app.models.user import User
from sqlalchemy import select


async def list_users():
    """List all users."""
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User))
        users = result.scalars().all()

        print("=" * 80)
        print("ALL USERS IN DATABASE")
        print("=" * 80)

        for user in users:
            print(f"\nEmail:     {user.email}")
            print(f"Role:      {user.role}")
            print(f"Tenant ID: {user.tenant_id}")
            print(f"Active:    {user.is_active}")
            print("-" * 80)


if __name__ == "__main__":
    asyncio.run(list_users())
