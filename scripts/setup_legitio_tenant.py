#!/usr/bin/env python3
"""
Setup Legitio tenant and update admin user.
"""
import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import AsyncSessionLocal
from app.models.tenant import Tenant
from app.models.user import User
from sqlalchemy import select


async def setup_legitio():
    """Setup Legitio tenant and associate admin user."""
    async with AsyncSessionLocal() as db:
        # Check if Legitio tenant exists
        result = await db.execute(
            select(Tenant).where(Tenant.slug == "legitio")
        )
        tenant = result.scalar_one_or_none()

        if not tenant:
            # Create Legitio tenant
            tenant = Tenant(
                name="Legitio",
                slug="legitio",
                is_active=True,
                tokens_limit=1000000,  # 1M tokens
                posts_limit=1000,       # 1000 posts
                settings={
                    "language": "pl",
                    "default_tone": "professional",
                    "default_post_length": "long"
                }
            )
            db.add(tenant)
            await db.commit()
            await db.refresh(tenant)
            print(f"✅ Tenant created: {tenant.name} (ID: {tenant.id})")
        else:
            print(f"✅ Tenant already exists: {tenant.name} (ID: {tenant.id})")

        # Update admin user to associate with tenant
        result = await db.execute(
            select(User).where(User.email == "admin@legitio.pl")
        )
        admin = result.scalar_one_or_none()

        if admin:
            # Change from superadmin to admin with tenant
            admin.tenant_id = tenant.id
            admin.role = "admin"  # Admin for this tenant
            await db.commit()
            print(f"✅ Admin user updated with tenant association")
            print(f"   Email: admin@legitio.pl")
            print(f"   Role: admin (tenant owner)")
            print(f"   Tenant: {tenant.name}")
        else:
            print("❌ Admin user not found. Run create_admin.py first.")
            return

        print()
        print("🎉 Setup complete! You can now:")
        print("   1. Login to dashboard: http://localhost:5173")
        print("   2. Create AI agents")
        print("   3. Generate blog posts")


if __name__ == "__main__":
    asyncio.run(setup_legitio())
