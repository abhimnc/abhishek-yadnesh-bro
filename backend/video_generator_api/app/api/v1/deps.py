from typing import Generator, Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
import jwt
from pydantic import ValidationError

from app.core.config import settings
from app.db.session import get_async_session
from app.db.models.user_models import User
from app.db.crud.crud_user import user_crud
from app.api.v1.schemas import TokenPayload
from app.core.security import decode_token
from app.services.usage_service import UsageService

reusable_oauth2 = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/auth/login" # Points to the login endpoint
)

async def get_current_user(
    db: AsyncSession = Depends(get_async_session),
    token: str = Depends(reusable_oauth2)
) -> User:
    try:
        payload = decode_token(token)
        token_data = TokenPayload(**payload)
    except Exception as e:
        print(f"Error decoding token: {e}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Could not validate credentials",
        )
    if not token_data.sub:
         raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid token subject",
        )
    user = await user_crud.get(db, id=token_data.sub)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    if not user_crud.is_active(current_user):
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

async def get_current_active_superuser(
    current_user: User = Depends(get_current_active_user) # Depends on active user
) -> User:
    if not user_crud.is_superuser(current_user):
        raise HTTPException(
            status_code=403, detail="The user doesn't have enough privileges"
        )
    return current_user

async def get_usage_service(db: AsyncSession = Depends(get_async_session)) -> UsageService:
    """Dependency provider for the UsageService."""
    return UsageService(db=db) 