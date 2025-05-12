import uuid
from typing import Optional
from datetime import datetime

from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel # For Pydantic schemas

from app.db.crud.crud_base import CRUDBase
from app.db.models.user_models import OAuthAccount # AuthProvider might not be needed here
# from app.core import security # Not directly used if encryption is handled by service layer

# Schemas for OAuthAccount CRUD operations
# These are Pydantic models, not SQLModels, used for data validation.
# They should align with the fields expected by the OAuthAccount SQLModel.

class OAuthAccountCreateSchema(BaseModel):
    user_id: uuid.UUID
    provider: str # Should match AuthProvider enum values from user_models
    provider_user_id: str
    encrypted_access_token: Optional[str] = None
    encrypted_refresh_token: Optional[str] = None
    expires_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class OAuthAccountUpdateSchema(BaseModel):
    encrypted_access_token: Optional[str] = None
    encrypted_refresh_token: Optional[str] = None
    expires_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class CRUDOAuthAccount(CRUDBase[OAuthAccount, OAuthAccountCreateSchema, OAuthAccountUpdateSchema]):
    async def get_by_provider_and_user_id(
        self, db: AsyncSession, *, provider: str, provider_user_id: str
    ) -> Optional[OAuthAccount]:
        statement = select(self.model).where(
            self.model.provider == provider,
            self.model.provider_user_id == provider_user_id
        )
        result = await db.execute(statement)
        return result.scalar_one_or_none()

    async def create_with_user_id(self, db: AsyncSession, *, obj_in: OAuthAccountCreateSchema) -> OAuthAccount:
        # As per OAuthService in auth.py, encryption is handled before this schema is populated.
        db_obj_data = obj_in.model_dump()
        db_obj = self.model(**db_obj_data) # Use the validated and dumped data
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj
    
    # The base CRUDBase.update method should suffice for typical updates if it handles
    # Pydantic models correctly for obj_in.
    # If specific logic for updating OAuthAccount is needed (e.g., always re-encrypting if raw tokens were passed),
    # override the update method here. Given current design, it's not needed.


oauth_account_crud = CRUDOAuthAccount(OAuthAccount) 