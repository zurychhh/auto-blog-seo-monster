"""
Authentication service - JWT token generation, password hashing, user verification.
"""

from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID

from app.config import settings
from app.models.user import User
from app.schemas.auth import TokenData

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AuthService:
    """Authentication service for JWT and password management."""

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify a plain password against a hashed password."""
        return pwd_context.verify(plain_password, hashed_password)

    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a password using bcrypt."""
        return pwd_context.hash(password)

    @staticmethod
    def create_access_token(
        user_id: UUID,
        tenant_id: Optional[UUID],
        role: str
    ) -> str:
        """
        Create JWT access token.

        Args:
            user_id: User's UUID
            tenant_id: Tenant's UUID (None for superadmin)
            role: User's role (superadmin, admin, editor)

        Returns:
            JWT token string
        """
        expire = datetime.utcnow() + timedelta(hours=settings.JWT_EXPIRY_HOURS)

        payload = {
            "sub": str(user_id),
            "tenant_id": str(tenant_id) if tenant_id else None,
            "role": role,
            "exp": int(expire.timestamp()),
        }

        token = jwt.encode(
            payload,
            settings.JWT_SECRET,
            algorithm=settings.JWT_ALGORITHM
        )

        return token

    @staticmethod
    def decode_token(token: str) -> Optional[TokenData]:
        """
        Decode and verify JWT token.

        Args:
            token: JWT token string

        Returns:
            TokenData if valid, None if invalid
        """
        try:
            payload = jwt.decode(
                token,
                settings.JWT_SECRET,
                algorithms=[settings.JWT_ALGORITHM]
            )

            user_id = UUID(payload.get("sub"))
            tenant_id_str = payload.get("tenant_id")
            tenant_id = UUID(tenant_id_str) if tenant_id_str else None
            role = payload.get("role")
            exp = payload.get("exp")

            if not user_id or not role:
                return None

            return TokenData(
                sub=user_id,
                tenant_id=tenant_id,
                role=role,
                exp=exp
            )
        except JWTError:
            return None

    @staticmethod
    async def authenticate_user(
        db: AsyncSession,
        email: str,
        password: str
    ) -> Optional[User]:
        """
        Authenticate user by email and password.

        Args:
            db: Database session
            email: User's email
            password: Plain text password

        Returns:
            User object if authenticated, None otherwise
        """
        result = await db.execute(
            select(User).where(User.email == email)
        )
        user = result.scalar_one_or_none()

        if not user:
            return None

        if not AuthService.verify_password(password, user.password_hash):
            return None

        if not user.is_active:
            return None

        return user

    @staticmethod
    async def get_user_by_id(db: AsyncSession, user_id: UUID) -> Optional[User]:
        """Get user by ID."""
        result = await db.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
        """Get user by email."""
        result = await db.execute(
            select(User).where(User.email == email)
        )
        return result.scalar_one_or_none()
