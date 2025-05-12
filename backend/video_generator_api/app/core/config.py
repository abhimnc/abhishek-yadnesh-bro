import os
from typing import List, Union, Optional
from pydantic import AnyHttpUrl, PostgresDsn, validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv
from functools import lru_cache

# Load .env file from the project root (backend/video_generator_api/.env)
# This allows .env to be at the same level as requirements.txt, Dockerfile etc.
dotenv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env")
load_dotenv(dotenv_path=dotenv_path)

class Settings(BaseSettings):
    PROJECT_NAME: str = "Video Generator API"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"

    # Database
    POSTGRES_SERVER: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    DATABASE_URL: Optional[str] = None

    # JWT
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    ACCESS_TOKEN_TYPE_CLAIM: str = "access"
    REFRESH_TOKEN_TYPE_CLAIM: str = "refresh"

    # OAuth Token Encryption
    OAUTH_TOKEN_ENCRYPTION_KEY: str

    # Google OAuth2
    GOOGLE_CLIENT_ID: str
    GOOGLE_CLIENT_SECRET: str
    GOOGLE_REDIRECT_URI: str

    # Celery
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"

    # CORS
    BACKEND_CORS_ORIGINS: List[AnyHttpUrl] = []

    FERNET_KEY: str # For encrypting OAuth tokens

    # Email Settings
    SMTP_HOST: str
    SMTP_PORT: int
    SMTP_USER: str
    SMTP_PASSWORD: str
    EMAIL_FROM: str
    EMAIL_FROM_NAME: str
    EMAIL_VERIFICATION_TOKEN_EXPIRE_HOURS: int = 24
    SERVER_HOST: str

    @validator("BACKEND_CORS_ORIGINS", pre=True)
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> Union[List[str], str]:
        if isinstance(v, str) and not v.startswith("["):
            if v == "*": # Allow all origins with wildcard
                return ["*"]
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)

    @validator("DATABASE_URL", pre=True)
    def build_db_connection_str(cls, v: Optional[str]) -> str:
        if v is None:
            # This could be a place to set a default SQLite DB for local dev if not set
            # For now, we expect it to be set in .env
            raise ValueError("DATABASE_URL must be set in environment variables")
        return str(v)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.DATABASE_URL:
            self.DATABASE_URL = f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}/{self.POSTGRES_DB}"

    model_config = SettingsConfigDict(env_file=".env", extra='ignore')

@lru_cache()
def get_settings() -> Settings:
    return Settings()

settings = get_settings() 