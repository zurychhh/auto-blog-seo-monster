#!/usr/bin/env python3
"""
Fix admin user - associate with Legitio tenant.
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import AsyncSessionLocal
from app.models.tenant import Tenant
from app.models.user import User
from app.services.auth_service import AuthService
from sqlalchemy import select


async def fix_admin():
    """Fix admin user."""
    async with AsyncSessionLocal() as db:
        # Get Legitio tenant
        result = await db.execute(
            select(Tenant).where(Tenant.slug == "legitio")
        )
        tenant = result.scalar_one_or_none()

        if not tenant:
            print("❌ Legitio tenant not found.")
            return

        print(f"✅ Found tenant: {tenant.name} (ID: {tenant.id})")

        # Check admin@legitio.pl
        result = await db.execute(
            select(User).where(User.email == "admin@legitio.pl")
        )
        admin_user = result.scalar_one_or_none()

        if admin_user:
            print(f"\n✅ Found user: {admin_user.email}")
            print(f"   Current tenant_id: {admin_user.tenant_id}")
            print(f"   Current role: {admin_user.role}")

            # Update to associate with Legitio tenant
            admin_user.tenant_id = tenant.id
            admin_user.role = "admin"
            await db.commit()

            print(f"\n✅ Updated admin@legitio.pl:")
            print(f"   New tenant_id: {admin_user.tenant_id}")
            print(f"   New role: {admin_user.role}")
        else:
            # Create new admin@legitio.pl user
            print(f"\n⚠️  User admin@legitio.pl not found. Creating...")

            password_hash = AuthService.hash_password("Admin123!")

            new_admin = User(
                email="admin@legitio.pl",
                password_hash=password_hash,
                role="admin",
                tenant_id=tenant.id,
                is_active=True
            )
            db.add(new_admin)
            await db.commit()
            await db.refresh(new_admin)

            print(f"✅ Created admin@legitio.pl:")
            print(f"   Email: {new_admin.email}")
            print(f"   Tenant: {tenant.name}")
            print(f"   Role: {new_admin.role}")
            print(f"   Password: Admin123!")

        print("\n🎉 Admin user fixed!")
        print(f"   Email: admin@legitio.pl")
        print(f"   Password: Admin123!")


if __name__ == "__main__":
    asyncio.run(fix_admin())
