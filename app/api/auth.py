"""
Authentication API endpoints - login, register, me.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.user import User
from app.schemas.auth import UserLogin, UserRegister, Token, UserResponse
from app.services.auth_service import AuthService
from app.api.deps import get_current_user, get_current_superadmin

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login", response_model=Token)
async def login(
    credentials: UserLogin,
    db: AsyncSession = Depends(get_db)
):
    """
    Login with email and password.

    Returns JWT access token.
    """
    user = await AuthService.authenticate_user(
        db,
        credentials.email,
        credentials.password
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Create access token
    access_token = AuthService.create_access_token(
        user_id=user.id,
        tenant_id=user.tenant_id,
        role=user.role
    )

    return Token(access_token=access_token)


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserRegister,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_superadmin)  # Only superadmin can create users
):
    """
    Register a new user (superadmin only).

    Creates a new user account with hashed password.
    """
    # Check if email already exists
    existing_user = await AuthService.get_user_by_email(db, user_data.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    # Validate tenant_id for non-superadmin users
    if user_data.role != "superadmin" and not user_data.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="tenant_id required for non-superadmin users",
        )

    # Hash password
    password_hash = AuthService.hash_password(user_data.password)

    # Create user
    new_user = User(
        email=user_data.email,
        password_hash=password_hash,
        role=user_data.role,
        tenant_id=user_data.tenant_id,
        is_active=True
    )

    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    return new_user


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """
    Get current authenticated user information.
    """
    return current_user


@router.post("/refresh", response_model=Token)
async def refresh_token(
    current_user: User = Depends(get_current_user)
):
    """
    Refresh JWT access token.

    Returns a new access token with extended expiry.
    """
    access_token = AuthService.create_access_token(
        user_id=current_user.id,
        tenant_id=current_user.tenant_id,
        role=current_user.role
    )

    return Token(access_token=access_token)
