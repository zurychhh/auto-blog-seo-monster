#!/usr/bin/env python3
"""
Create admin user for Legitio Blog
"""
import asyncio
import sys
from pathlib import Path
import bcrypt

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import AsyncSessionLocal
from app.models.user import User


async def create_admin():
    """Create admin user if doesn't exist"""
    async with AsyncSessionLocal() as db:
        # Check if admin exists
        from sqlalchemy import select
        result = await db.execute(
            select(User).where(User.email == "admin@legitio.pl")
        )
        existing = result.scalar_one_or_none()

        if existing:
            print("✅ Admin user already exists: admin@legitio.pl")
            return

        # Create admin with bcrypt directly (passlib has Python 3.13 compat issues)
        password = "Admin123!"
        salt = bcrypt.gensalt()
        password_hash = bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

        admin = User(
            email="admin@legitio.pl",
            password_hash=password_hash,
            role="superadmin",
            is_active=True,
            tenant_id=None  # Superadmin has no tenant
        )

        db.add(admin)
        await db.commit()
        await db.refresh(admin)

        print("✅ Admin user created successfully!")
        print(f"   Email: admin@legitio.pl")
        print(f"   Password: Admin123!")
        print(f"   Role: superadmin")
        print(f"   ID: {admin.id}")
        print()
        print("🚀 You can now login to:")
        print("   - API: http://localhost:8000/docs")
        print("   - Dashboard: http://localhost:5173")


if __name__ == "__main__":
    asyncio.run(create_admin())
