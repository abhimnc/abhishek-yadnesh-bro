import uuid
from typing import Optional, List, Dict, Any
from decimal import Decimal
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field as PydanticField, HttpUrl, AnyUrl

from app.db.models.user_models import AuthProvider
from app.db.models.video_models import VideoGenerationTaskStatus

# Token Schemas
class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

class AccessTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

class TokenPayload(BaseModel):
    sub: Optional[uuid.UUID] = None
    type: Optional[str] = None # To distinguish access vs refresh

class RefreshTokenRequest(BaseModel):
    refresh_token: str

# User Schemas
class UserBaseSchema(BaseModel):
    email: EmailStr
    full_name: Optional[str] = None
    avatar_url: Optional[AnyUrl] = None

class UserCreateSchema(UserBaseSchema):
    password: str = PydanticField(..., min_length=8)

# Schema for internal user creation, e.g. via OAuth where password might not be set initially
class UserCreateInternalSchema(UserBaseSchema):
    hashed_password: Optional[str] = None
    auth_provider: AuthProvider = AuthProvider.EMAIL
    is_active: bool = False # Users created via signup start inactive until email verification
    # is_superuser should not be set here, default is False in model
    email_verification_token: Optional[str] = None
    email_verification_token_expires_at: Optional[datetime] = None
    # full_name and avatar_url are inherited from UserBaseSchema and are Optional

class UserUpdateSchema(BaseModel):
    full_name: Optional[str] = None
    avatar_url: Optional[AnyUrl] = None
    # Potentially add other updatable fields like email if you implement verification flow

class UserReadSchema(UserBaseSchema):
    id: uuid.UUID
    is_active: bool
    is_superuser: bool
    auth_provider: AuthProvider
    last_login_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class PasswordChangeSchema(BaseModel):
    current_password: str
    new_password: str = PydanticField(..., min_length=8)


# Plan Schemas
class PlanBaseSchema(BaseModel):
    name: str
    stripe_price_id: str
    video_limit_per_period: int
    max_video_duration_seconds: Optional[int] = None
    features: Optional[Dict[str, Any]] = None # Reverted to Dict[str, Any] for JSONB
    price_monthly: Optional[Decimal] = None # Use Decimal for price
    price_yearly: Optional[Decimal] = None
    currency: str # Made mandatory as per documentation
    description: Optional[str] = None
    is_active: bool = True
    display_order: int = 0

class PlanCreateSchema(PlanBaseSchema):
    pass # Currently same as base, can diverge if needed

class PlanReadSchema(PlanBaseSchema):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class PlanUpdateSchema(BaseModel): # All fields are optional for update
    name: Optional[str] = None
    stripe_price_id: Optional[str] = None
    video_limit_per_period: Optional[int] = None
    max_video_duration_seconds: Optional[int] = None
    features: Optional[Dict[str, Any]] = None
    price_monthly: Optional[Decimal] = None
    price_yearly: Optional[Decimal] = None
    currency: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None
    display_order: Optional[int] = None

    class Config:
        from_attributes = True # Important if you plan to use it with ORM models directly

# OAuth Schemas (minimal for now, expand as needed)
class GoogleOAuthCallbackSchema(BaseModel):
    code: str
    state: Optional[str] = None # If you use state parameter for CSRF protection

# OAuthAccount Schemas (as used by OAuthService in auth.py)
class OAuthAccountCreateSchema(BaseModel):
    user_id: uuid.UUID
    provider: str # Should match AuthProvider enum values from user_models
    provider_user_id: str
    encrypted_access_token: str
    encrypted_refresh_token: Optional[str] = None
    expires_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class MessageResponse(BaseModel):
    message: str

# --- Video Schemas ---

class VideoCreateRequestSchema(BaseModel):
    prompt_text: str = PydanticField(..., min_length=10, max_length=2000)


class VideoTaskBaseSchema(BaseModel):
    task_id: uuid.UUID
    status: VideoGenerationTaskStatus


class VideoTaskCreateResponseSchema(VideoTaskBaseSchema):
    message: str


class VideoTaskStatusResponseSchema(VideoTaskBaseSchema):
    progress_percentage: int
    error_message: Optional[str] = None
    video_id: Optional[uuid.UUID] = None
    video_url: Optional[AnyUrl] = None


class GeneratedVideoReadSchema(BaseModel):
    id: uuid.UUID
    title: str
    final_video_url: Optional[AnyUrl] = None
    created_at: datetime

    class Config:
        from_attributes = True 