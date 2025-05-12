from authlib.integrations.starlette_client import OAuth
from app.core.config import settings

oauth = OAuth()

# Register Google OAuth client if configured
if settings.GOOGLE_CLIENT_ID and settings.GOOGLE_CLIENT_SECRET:
    oauth.register(
        name='google',
        client_id=settings.GOOGLE_CLIENT_ID,
        client_secret=settings.GOOGLE_CLIENT_SECRET,
        server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
        client_kwargs={
            'scope': 'openid email profile',
            # Consider adding prompt: 'consent' if you always want to ask for consent,
            # or 'select_account' if you want the user to choose between multiple Google accounts.
            # 'redirect_uri': str(settings.GOOGLE_REDIRECT_URI) # Ensure this is a string for Authlib
        },
        # Ensure your GOOGLE_REDIRECT_URI in .env matches one registered in Google Cloud Console
    )
else:
    print("Google OAuth not configured. GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET are missing.")
    # You might want to raise a warning or log this more formally in a real application 