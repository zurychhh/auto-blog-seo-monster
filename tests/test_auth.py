"""
Tests for authentication endpoints.
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient, test_user, test_tenant, db_session: AsyncSession):
    """Test successful login."""
    # Link user to tenant
    test_user.tenant_id = test_tenant.id
    await db_session.commit()

    response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": "test@example.com",
            "password": "testpassword123"
        }
    )

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_invalid_credentials(client: AsyncClient, test_user):
    """Test login with invalid credentials."""
    response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": "test@example.com",
            "password": "wrongpassword"
        }
    )

    assert response.status_code == 401
    assert "incorrect" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_login_nonexistent_user(client: AsyncClient):
    """Test login with non-existent user."""
    response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": "nonexistent@example.com",
            "password": "password123"
        }
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_current_user(client: AsyncClient, auth_headers):
    """Test getting current user info."""
    response = await client.get(
        "/api/v1/auth/me",
        headers=auth_headers
    )

    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "test@example.com"
    assert data["role"] == "admin"


@pytest.mark.asyncio
async def test_get_current_user_unauthorized(client: AsyncClient):
    """Test getting current user without auth."""
    response = await client.get("/api/v1/auth/me")

    assert response.status_code == 403  # No auth header


@pytest.mark.asyncio
async def test_refresh_token(client: AsyncClient, auth_headers):
    """Test token refresh."""
    response = await client.post(
        "/api/v1/auth/refresh",
        headers=auth_headers
    )

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
