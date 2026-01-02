"""
Pytest configuration and fixtures.
"""

import pytest
import asyncio
from typing import AsyncGenerator, Generator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from httpx import AsyncClient

from app.main import app
from app.database import Base, get_db
from app.config import settings

# Test database URL (use different DB for tests)
TEST_DATABASE_URL = "postgresql+asyncpg://postgres:password@localhost:5432/autoblog_test"

# Create test engine
test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestSessionLocal = async_sessionmaker(
    test_engine,
    class_=AsyncSession,
    expire_on_commit=False
)


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Create test database session."""
    # Create tables
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Create session
    async with TestSessionLocal() as session:
        yield session

    # Drop tables after test
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture(scope="function")
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Create test client with overridden database dependency."""

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.fixture
async def test_user(db_session: AsyncSession):
    """Create a test user."""
    from app.models.user import User
    from app.services.auth_service import AuthService

    user = User(
        email="test@example.com",
        password_hash=AuthService.hash_password("testpassword123"),
        role="admin",
        is_active=True
    )

    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    return user


@pytest.fixture
async def test_tenant(db_session: AsyncSession):
    """Create a test tenant."""
    from app.models.tenant import Tenant

    tenant = Tenant(
        name="Test Tenant",
        slug="test-tenant",
        tokens_limit=100000,
        posts_limit=50
    )

    db_session.add(tenant)
    await db_session.commit()
    await db_session.refresh(tenant)

    return tenant


@pytest.fixture
async def auth_headers(test_user, test_tenant, db_session: AsyncSession):
    """Create auth headers with JWT token."""
    from app.services.auth_service import AuthService

    # Link user to tenant
    test_user.tenant_id = test_tenant.id
    await db_session.commit()

    # Create token
    token = AuthService.create_access_token(
        user_id=test_user.id,
        tenant_id=test_tenant.id,
        role=test_user.role
    )

    return {"Authorization": f"Bearer {token}"}
