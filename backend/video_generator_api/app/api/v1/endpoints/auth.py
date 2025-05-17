import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Body, Request, Response, Query
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
# OAuthError might not be needed here if handled within OAuthService

from app.core.config import settings
from app.core.security import (
    get_password_hash,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
    encrypt_data,
    decrypt_data,
    JWTError
)
from app.db.session import get_async_session
from app.db.crud.crud_user import user_crud
from app.db.models.user_models import User, AuthProvider
from app.api.v1.deps import get_current_active_user
from app.api.v1.schemas import (
    Token, UserCreateSchema, UserCreateInternalSchema, UserReadSchema, UserUpdateSchema,
    AccessTokenResponse, RefreshTokenRequest, PasswordChangeSchema, MessageResponse
)

# Import the service and its dependency provider
from app.services.oauth_service import OAuthService, get_oauth_service
from app.core.email import send_verification_email

router = APIRouter(tags=["Authentication"])


@router.post("/signup", response_model=MessageResponse)
async def signup(
    *,
    db: AsyncSession = Depends(get_async_session),
    user_in: UserCreateSchema = Body(...)
):
    """
    Create new user and send verification email.
    """
    existing_user = await user_crud.get_by_email(db, email=user_in.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The user with this email already exists in the system.",
        )
    
    # Generate verification token
    verification_token = uuid.uuid4().hex
    verification_token_expires = datetime.now(timezone.utc) + timedelta(hours=settings.EMAIL_VERIFICATION_TOKEN_EXPIRE_HOURS)
    
    hashed_password = get_password_hash(user_in.password)
    user_create_internal = UserCreateInternalSchema(
        email=user_in.email,
        hashed_password=hashed_password,
        full_name=user_in.full_name,
        avatar_url=str(user_in.avatar_url) if user_in.avatar_url else None,
        auth_provider=AuthProvider.EMAIL,
        is_active=False,  # User starts as inactive
        is_superuser=False,
        email_verification_token=verification_token,
        email_verification_token_expires_at=verification_token_expires
    )
    
    user = await user_crud.create_user_oauth(db, obj_in=user_create_internal)
    
    # Send verification email
    try:
        await send_verification_email(email_to=user.email, verification_token=verification_token)
    except Exception as e:
        # If email sending fails, delete the user and raise an error
        await user_crud.remove(db, id=user.id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send verification email. Please try again."
        )
    
    return {"message": "Signup successful. Please check your email to verify your account."}


@router.get("/verify-email", response_model=MessageResponse)
async def verify_email(
    *,
    db: AsyncSession = Depends(get_async_session),
    token: str = Query(..., description="Email verification token")
):
    """
    Verify user's email address.
    """
    user = await user_crud.get_by_verification_token(db, token=token)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid verification token."
        )
    
    if user.email_verification_token_expires_at < datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Verification token has expired. Please request a new one."
        )
    
    if user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already verified."
        )
    
    # Update user
    update_data = {
        "is_active": True,
        "email_verification_token": None,
        "email_verification_token_expires_at": None
    }
    await user_crud.update(db, db_obj=user, obj_in=update_data)
    
    return {"message": "Email verified successfully. You can now log in."}


@router.post("/resend-verification-email", response_model=MessageResponse)
async def resend_verification_email(
    *,
    db: AsyncSession = Depends(get_async_session),
    email: str = Body(..., embed=True)
):
    """
    Resend verification email.
    """
    user = await user_crud.get_by_email(db, email=email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found."
        )
    
    if user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already verified."
        )
    
    if user.auth_provider != AuthProvider.EMAIL:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Please use your {user.auth_provider.value} login method."
        )
    
    # Generate new verification token
    verification_token = uuid.uuid4().hex
    verification_token_expires = datetime.now(timezone.utc) + timedelta(hours=settings.EMAIL_VERIFICATION_TOKEN_EXPIRE_HOURS)
    
    # Update user with new token
    update_data = {
        "email_verification_token": verification_token,
        "email_verification_token_expires_at": verification_token_expires
    }
    await user_crud.update(db, db_obj=user, obj_in=update_data)
    
    # Send new verification email
    try:
        await send_verification_email(email_to=user.email, verification_token=verification_token)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send verification email. Please try again."
        )
    
    return {"message": "Verification email sent. Please check your inbox."}


@router.post("/login", response_model=Token)
async def login(
    db: AsyncSession = Depends(get_async_session),
    form_data: OAuth2PasswordRequestForm = Depends()
):
    """
    OAuth2 compatible token login, get an access token for future requests.
    Username field is used for email.
    """
    user = await user_crud.get_by_email(db, email=form_data.username)
    if not user or not user.hashed_password: 
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if user.auth_provider != AuthProvider.EMAIL:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Please use your {user.auth_provider.value} login method.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user")

    await user_crud.update(db, db_obj=user, obj_in={"last_login_at": datetime.now(timezone.utc)})

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    refresh_token_expires = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    
    access_token = create_access_token(
        subject=user.id, expires_delta=access_token_expires
    )
    refresh_token = create_refresh_token(
        subject=user.id, expires_delta=refresh_token_expires
    )
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }


@router.post("/refresh-token", response_model=AccessTokenResponse) # Use schema from schemas.py
async def refresh_token(
    db: AsyncSession = Depends(get_async_session),
    refresh_token_request: RefreshTokenRequest = Body(...)
):
    """
    Refresh access token.
    """
    try:
        payload = decode_token(refresh_token_request.refresh_token)
        if not payload or payload.get("type") != settings.REFRESH_TOKEN_TYPE_CLAIM: 
             raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token type",
                headers={"WWW-Authenticate": "Bearer"},
            )
        token_subject = payload.get("sub")
        if token_subject is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token: no subject",
                headers={"WWW-Authenticate": "Bearer"},
            )
    except JWTError: 
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # We need to get the user by ID now, not email
    user = await user_crud.get(db, id=token_subject)
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    new_access_token = create_access_token(
        subject=user.id, expires_delta=access_token_expires
    )
    return {
        "access_token": new_access_token,
        "token_type": "bearer",
    }


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    response: Response 
):
    """
    Logout user. Client should discard tokens.
    If HttpOnly cookies are used for refresh tokens, clear them here.
    """
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/me", response_model=UserReadSchema)
async def read_users_me(
    current_user: User = Depends(get_current_active_user)
):
    """
    Get current user.
    """
    return current_user


@router.patch("/me", response_model=UserReadSchema)
async def update_user_me(
    *,
    db: AsyncSession = Depends(get_async_session),
    user_in: UserUpdateSchema,
    current_user: User = Depends(get_current_active_user)
):
    """
    Update current user's details (full_name, avatar_url).
    """
    update_data = user_in.model_dump(exclude_unset=True)
    if "avatar_url" in update_data and update_data["avatar_url"] is not None:
        update_data["avatar_url"] = str(update_data["avatar_url"])
        
    updated_user = await user_crud.update(db, db_obj=current_user, obj_in=update_data)
    return updated_user


@router.post("/me/change-password", status_code=status.HTTP_204_NO_CONTENT)
async def change_password_me(
    *,
    db: AsyncSession = Depends(get_async_session),
    password_data: PasswordChangeSchema = Body(...),
    current_user: User = Depends(get_current_active_user)
):
    """
    Change current user's password.
    """
    if not current_user.hashed_password: 
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot change password for users who signed up via OAuth and haven't set a password.",
        )
    if not verify_password(password_data.current_password, current_user.hashed_password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Incorrect current password")
    
    new_hashed_password = get_password_hash(password_data.new_password)
    await user_crud.update(db, db_obj=current_user, obj_in={"hashed_password": new_hashed_password})
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# --- Google OAuth2 Endpoints ---

@router.get("/login/google", name="auth_login_google")
async def login_google(
    request: Request, 
    oauth_service: OAuthService = Depends(get_oauth_service) # Use imported service
):
    """
    Initiate Google OAuth2 login flow. Redirects to Google's authorization page.
    """
    try:
        authorization_url = await oauth_service.get_google_authorization_url(request)
        return RedirectResponse(url=authorization_url, status_code=status.HTTP_307_TEMPORARY_REDIRECT)
    except HTTPException as e:
        raise e # Re-raise HTTPExceptions from the service
    except Exception as e:
        # Log e
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Could not initiate Google login: {str(e)}")


@router.get("/login/google/callback", name="auth_handle_google_callback", response_model=Token)
async def handle_google_auth_callback(
    request: Request, 
    oauth_service: OAuthService = Depends(get_oauth_service) # Use imported service
):
    """
    Handle the callback from Google after user authentication.
    Returns application-specific JWTs.
    """
    try:
        user, app_access_token, app_refresh_token = await oauth_service.process_google_login(request)
    except HTTPException as e: 
        raise e # Re-raise HTTPExceptions from the service
    except Exception as e:
        # Log e
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error processing Google callback: {str(e)}")
    
    return Token(
        access_token=app_access_token,
        refresh_token=app_refresh_token,
        token_type="bearer"
    ) 