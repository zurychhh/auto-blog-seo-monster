"""
Pydantic schemas for authentication.
"""

from pydantic import BaseModel, EmailStr, Field
from uuid import UUID
from typing import Optional


class UserLogin(BaseModel):
    """Login request schema."""
    email: EmailStr
    password: str = Field(..., min_length=8)


class UserRegister(BaseModel):
    """User registration schema."""
    email: EmailStr
    password: str = Field(..., min_length=8)
    role: str = Field(..., pattern="^(superadmin|admin|editor)$")
    tenant_id: Optional[UUID] = None  # Required for non-superadmin users


class Token(BaseModel):
    """JWT token response."""
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """Token payload data."""
    sub: UUID  # user_id
    tenant_id: Optional[UUID] = None
    role: str
    exp: int


class UserResponse(BaseModel):
    """User data response."""
    id: UUID
    email: str
    role: str
    tenant_id: Optional[UUID] = None
    is_active: bool

    class Config:
        from_attributes = True
