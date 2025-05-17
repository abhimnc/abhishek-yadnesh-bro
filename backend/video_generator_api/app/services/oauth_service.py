import uuid
from typing import Dict, Any, Optional
from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends, HTTPException, status, Request
from authlib.integrations.starlette_client import OAuthError

from app.db.models.user_models import User, OAuthAccount, AuthProvider
from app.db.crud.crud_user import user_crud
from app.db.crud.crud_oauth_account import oauth_account_crud, OAuthAccountCreateSchema, OAuthAccountUpdateSchema
from app.api.v1.schemas import UserCreateSchema, UserCreateInternalSchema # For creating a new user based on OAuth info
from app.core.security import encrypt_data, get_password_hash
from app.core.config import settings
from app.core import security
from app.core.oauth import oauth # Authlib google client instance
from app.db.session import get_async_session

class OAuthService:
    def __init__(self, db: AsyncSession = Depends(get_async_session)):
        self.db = db
        if not hasattr(oauth, 'google'):
            # This situation should ideally be caught at application startup if Google OAuth is critical
            # and GOOGLE_CLIENT_ID/SECRET are not set, preventing the client from being registered.
            print("Critical Error: Google OAuth client not registered. Check GOOGLE_CLIENT_ID/SECRET settings.")
            # Depending on how critical this is, you might raise an unrecoverable error
            # or allow the app to run with Google OAuth disabled (if other auth methods exist).
            # For now, we rely on the check in app.core.oauth.py that prints a warning.
            # A more robust solution would involve a startup check in main.py for essential services.
            pass # Allow to proceed, but google_client will be None if not registered
        self.google_client = getattr(oauth, 'google', None)

    async def get_google_authorization_url(self, request: Request) -> str:
        if not self.google_client:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Google OAuth is not configured on the server.")
        
        redirect_uri = str(request.url_for('auth_handle_google_callback'))
        auth_url, state = self.google_client.create_authorization_url(redirect_uri)
        
        if 'session' in request.scope:
            request.session['oauth_state'] = state
        else:
            # If sessions aren't available, CSRF protection via state in session won't work.
            # Consider alternative CSRF methods or accept the risk if state cannot be stored/verified.
            print("Warning: Session middleware not detected. OAuth state for CSRF protection is not being stored in session.")
            
        return auth_url

    async def process_google_login(self, request: Request) -> tuple[User, str, str]:
        if not self.google_client:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Google OAuth is not configured on the server.")

        if 'session' in request.scope:
            state_from_session = request.session.pop('oauth_state', None)
            state_from_query = request.query_params.get('state')
            if not state_from_session or state_from_session != state_from_query:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid OAuth state. CSRF token mismatch."
                )
        # else: if sessions are not used, skip state validation here, but acknowledge the reduced CSRF protection.

        try:
            token_data = await self.google_client.authorize_access_token(request)
        except OAuthError as error:
            # Log error.error or error.description for more details
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Google OAuth error: {error.description or error.error}"
            )
        except Exception as e:
            # Log e
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Could not fetch token from Google: {str(e)}"
            )

        user_info_google = token_data.get('userinfo')
        if not user_info_google or not user_info_google.get('email'):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Could not fetch user info from Google")

        email = str(user_info_google.get('email')).lower()
        provider_user_id = str(user_info_google.get('sub'))
        full_name = user_info_google.get('name')
        avatar_url = user_info_google.get('picture')

        oauth_account = await oauth_account_crud.get_by_provider_and_user_id(
            self.db, provider=AuthProvider.GOOGLE.value, provider_user_id=provider_user_id
        )

        user: User

        if oauth_account:
            user_maybe = await user_crud.get(self.db, id=oauth_account.user_id)
            if not user_maybe: 
                await oauth_account_crud.remove(self.db, id=oauth_account.id)
                # This indicates a significant data integrity issue.
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="User data inconsistency for OAuth account.")
            user = user_maybe
            
            update_oauth_data = {
                "encrypted_access_token": security.encrypt_data(token_data['access_token']),
                "expires_at": datetime.fromtimestamp(token_data.get('expires_at', int(datetime.now(timezone.utc).timestamp()) + token_data.get('expires_in', 0)), tz=timezone.utc),
            }
            if 'refresh_token' in token_data and token_data['refresh_token']:
                 update_oauth_data["encrypted_refresh_token"] = security.encrypt_data(token_data['refresh_token'])
            await oauth_account_crud.update(self.db, db_obj=oauth_account, obj_in=update_oauth_data)

        else: 
            user_maybe = await user_crud.get_by_email(self.db, email=email)
            if user_maybe: 
                user = user_maybe
                if user.auth_provider != AuthProvider.EMAIL and user.auth_provider != AuthProvider.GOOGLE:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=f"User with email {email} already exists with a different login method."
                    )
                user_update_data = {}
                if user.auth_provider == AuthProvider.EMAIL: 
                    user_update_data["auth_provider"] = AuthProvider.GOOGLE
                if avatar_url and not user.avatar_url:
                    user_update_data["avatar_url"] = avatar_url
                if full_name and not user.full_name:
                     user_update_data["full_name"] = full_name
                if user_update_data:
                    user = await user_crud.update(self.db, db_obj=user, obj_in=user_update_data)
            else: 
                user_to_create = UserCreateInternalSchema(
                    email=email,
                    full_name=full_name,
                    avatar_url=avatar_url,
                    hashed_password=None, 
                    auth_provider=AuthProvider.GOOGLE,
                    is_active=True,
                    is_superuser=False
                )
                user = await user_crud.create_user_oauth(self.db, obj_in=user_to_create)
            
            oauth_account_to_create = OAuthAccountCreateSchema(
                user_id=user.id,
                provider=AuthProvider.GOOGLE.value,
                provider_user_id=provider_user_id,
                encrypted_access_token=security.encrypt_data(token_data['access_token']),
                encrypted_refresh_token=security.encrypt_data(token_data.get('refresh_token')) if token_data.get('refresh_token') else None,
                expires_at=datetime.fromtimestamp(token_data.get('expires_at', int(datetime.now(timezone.utc).timestamp()) + token_data.get('expires_in', 0)), tz=timezone.utc),
            )
            await oauth_account_crud.create_with_user_id(self.db, obj_in=oauth_account_to_create)

        if not user.is_active:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User account is inactive.")

        await user_crud.update(self.db, db_obj=user, obj_in={"last_login_at": datetime.now(timezone.utc)})

        app_access_token = security.create_access_token(subject=user.id)
        app_refresh_token = security.create_refresh_token(subject=user.id)
        
        return user, app_access_token, app_refresh_token

# Dependency provider for OAuthService
async def get_oauth_service(db: AsyncSession = Depends(get_async_session)) -> OAuthService:
    return OAuthService(db=db) 