import uuid
from datetime import datetime, timezone
from typing import Optional, List
import enum # Import the enum module

from sqlalchemy import Column, String, Index, UniqueConstraint, text, Boolean, DateTime
from sqlalchemy.dialects.postgresql import ENUM as PgEnum, UUID
from sqlalchemy.orm import relationship
from sqlmodel import Field, Relationship

from app.db.models.base_model import SQLModelBase

# Define AuthProvider as a standard Python enum
class AuthProvider(enum.Enum):
    EMAIL = "EMAIL"
    GOOGLE = "GOOGLE"

class UserBase(SQLModelBase):
    email: str = Field(sa_column=Column(String, unique=True, index=True, nullable=False))
    full_name: Optional[str] = Field(default=None, max_length=100)
    is_active: bool = Field(default=False)
    is_superuser: bool = Field(default=False)
    auth_provider: AuthProvider = Field(sa_column=Column(PgEnum(AuthProvider, name="authproviderenum", create_type=False), default=AuthProvider.EMAIL, nullable=False))
    avatar_url: Optional[str] = Field(default=None, max_length=512)
    last_login_at: Optional[datetime] = Field(default=None, sa_column=Column(DateTime(timezone=True), nullable=True))
    email_verification_token: Optional[str] = Field(default=None, sa_column=Column(String, nullable=True, index=True))
    email_verification_token_expires_at: Optional[datetime] = Field(default=None, sa_column=Column(DateTime(timezone=True), nullable=True))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), sa_column=Column(DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP")))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), sa_column=Column(DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"), onupdate=text("CURRENT_TIMESTAMP")))

class User(UserBase, table=True):
    __tablename__ = "user_account" # Explicit table name, "user" can be a reserved keyword
    hashed_password: Optional[str] = Field(default=None)

    oauth_accounts: List["OAuthAccount"] = Relationship(back_populates="user")
    # Add other relationships later e.g. to Subscription, VideoGenerationTask

    __table_args__ = (
        Index("idx_user_email_lower", text("LOWER(email)"), unique=True),
    )

class OAuthAccountBase(SQLModelBase):
    provider: str = Field(max_length=50, nullable=False)
    provider_user_id: str = Field(max_length=255, nullable=False)
    encrypted_access_token: Optional[str] = Field(default=None)
    encrypted_refresh_token: Optional[str] = Field(default=None)
    expires_at: Optional[datetime] = Field(default=None, sa_column=Column(DateTime(timezone=True), nullable=True))

class OAuthAccount(OAuthAccountBase, table=True):
    user_id: uuid.UUID = Field(foreign_key="user_account.id", nullable=False, index=True)
    user: Optional[User] = Relationship(back_populates="oauth_accounts")

    __table_args__ = (
        UniqueConstraint("provider", "provider_user_id", name="uq_oauth_provider_user_id"),
        Index("idx_oauth_user_provider", "user_id", "provider") # useful for finding a user's specific oauth account
    ) 