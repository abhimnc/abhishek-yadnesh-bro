from typing import Any, Dict, Optional, Union
import uuid
from datetime import datetime, timezone

from sqlalchemy import func # For LOWER function
from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.crud.crud_base import CRUDBase
from app.db.models.user_models import User, AuthProvider
from app.api.v1.schemas import UserCreateSchema, UserUpdateSchema, UserCreateInternalSchema # Using Pydantic schemas for type hinting
from app.core.security import get_password_hash

class CRUDUser(CRUDBase[User, UserCreateSchema, UserUpdateSchema]):
    async def get_by_email(self, db: AsyncSession, *, email: str) -> Optional[User]:
        result = await db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def get_by_verification_token(self, db: AsyncSession, *, token: str) -> Optional[User]:
        result = await db.execute(select(User).where(User.email_verification_token == token))
        return result.scalar_one_or_none()

    async def create(self, db: AsyncSession, *, obj_in: UserCreateSchema, auth_provider: AuthProvider = AuthProvider.EMAIL) -> User:
        db_obj_data = obj_in.model_dump(exclude_unset=True)
        db_obj_data["hashed_password"] = get_password_hash(obj_in.password)
        db_obj_data["auth_provider"] = auth_provider
        # Ensure email is stored as lowercase if that's your strategy, or rely on DB index
        # db_obj_data["email"] = db_obj_data["email"].lower()
        
        db_obj = self.model(**db_obj_data)
        db.add(db_obj)
        await db.flush()
        await db.refresh(db_obj)
        return db_obj

    async def create_user_oauth(
        self, db: AsyncSession, *, obj_in: UserCreateInternalSchema
    ) -> User:
        db_obj = User(
            email=obj_in.email,
            hashed_password=obj_in.hashed_password,
            full_name=obj_in.full_name,
            avatar_url=obj_in.avatar_url,
            is_active=obj_in.is_active,
            is_superuser=obj_in.is_superuser,
            auth_provider=obj_in.auth_provider,
            email_verification_token=obj_in.email_verification_token,
            email_verification_token_expires_at=obj_in.email_verification_token_expires_at
        )
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def update(
        self, db: AsyncSession, *, db_obj: User, obj_in: Union[UserUpdateSchema, Dict[str, Any]]
    ) -> User:
        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.model_dump(exclude_unset=True)
        
        return await super().update(db, db_obj=db_obj, obj_in=update_data)
    
    async def update_last_login(self, db: AsyncSession, *, user: User) -> User:
        user.last_login_at = datetime.now(timezone.utc)
        db.add(user)
        await db.flush()
        await db.refresh(user)
        return user

    def is_superuser(self, user: User) -> bool:
        return user.is_superuser

    def is_active(self, user: User) -> bool:
        return user.is_active

user_crud = CRUDUser(User) 