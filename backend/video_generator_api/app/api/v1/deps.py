from typing import Generator, Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import get_async_session
from app.db.models.user_models import User
from app.db.crud.crud_user import user_crud
from app.api.v1.schemas import TokenPayload
from app.core.security import decode_token

reusable_oauth2 = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/auth/login" # Points to the login endpoint
)

async def get_current_user(
    db: AsyncSession = Depends(get_async_session),
    token: str = Depends(reusable_oauth2)
) -> User:
    payload = decode_token(token)
    if not payload or not payload.get("sub"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token_data = TokenPayload(sub=str(payload["sub"]), exp=payload.get("exp"))
    
    user = await user_crud.get_by_email(db, email=token_data.sub)
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