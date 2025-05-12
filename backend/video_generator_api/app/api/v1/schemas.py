import uuid
from typing import Optional, List, Dict, Any
from decimal import Decimal
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field as PydanticField, HttpUrl

from app.db.models.user_models import AuthProvider

# Token Schemas
class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

class AccessTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

class TokenPayload(BaseModel):
    sub: Optional[str] = None
    exp: Optional[int] = None
    type: Optional[str] = None

class RefreshTokenRequest(BaseModel):
    refresh_token: str

# User Schemas
class UserBaseSchema(BaseModel):
    email: EmailStr
    full_name: Optional[str] = None
    avatar_url: Optional[HttpUrl] = None

class UserCreateSchema(UserBaseSchema):
    password: str

# Schema for internal user creation, e.g. via OAuth where password might not be set initially
class UserCreateInternalSchema(UserBaseSchema):
    hashed_password: Optional[str] = None
    auth_provider: str = "email"
    is_active: bool = False
    is_superuser: bool = False
    email_verification_token: Optional[str] = None
    email_verification_token_expires_at: Optional[datetime] = None
    # full_name and avatar_url are inherited from UserBaseSchema and are Optional

class UserUpdateSchema(BaseModel):
    full_name: Optional[str] = None
    avatar_url: Optional[HttpUrl] = None
    # Potentially add other updatable fields like email if you implement verification flow

class UserReadSchema(UserBaseSchema):
    id: uuid.UUID
    is_active: bool
    is_superuser: bool
    auth_provider: str
    last_login_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class PasswordChangeSchema(BaseModel):
    current_password: str
    new_password: str


# Plan Schemas
class PlanBaseSchema(BaseModel):
    name: str
    stripe_price_id: str
    video_limit_per_period: int
    max_video_duration_seconds: Optional[int] = None
    features: Optional[Dict[str, Any]] = None
    price_monthly: Optional[Decimal] = None
    price_yearly: Optional[Decimal] = None
    currency: str = "USD"
    description: Optional[str] = None
    is_active: bool = True
    display_order: int = 0

class PlanCreateSchema(PlanBaseSchema):
    pass # Currently same as base, can diverge if needed

class PlanReadSchema(PlanBaseSchema):
    id: uuid.UUID

    class Config:
        from_attributes = True

# OAuth Schemas (minimal for now, expand as needed)
class GoogleOAuthCallbackSchema(BaseModel):
    code: str
    state: Optional[str] = None # If you use state parameter for CSRF protection

# OAuthAccount Schemas (as used by OAuthService in auth.py)
class OAuthAccountCreateSchema(BaseModel):
    user_id: uuid.UUID
    provider: str # Should match AuthProvider enum values from user_models
    provider_user_id: str
    encrypted_access_token: Optional[str] = None
    encrypted_refresh_token: Optional[str] = None
    expires_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class MessageResponse(BaseModel):
    message: str 