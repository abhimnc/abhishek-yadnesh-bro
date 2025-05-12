from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from contextlib import asynccontextmanager

load_dotenv()

from app.core.config import settings
from app.api.v1.endpoints.auth import router as auth_api_router # Import your auth router
# from app.db.session import init_db # Optional: if you want to run init_db on startup for dev

@asynccontextmanager
async def lifespan(current_app: FastAPI):
    # Startup logic
    print("Application startup...")
    # await init_db() # If you need to initialize DB schema on startup (for dev/testing)
    # print("Database initialized (if init_db was called).")
    yield
    # Shutdown logic
    print("Application shutdown...")

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan,
    # You can add more app metadata here
    # version="0.1.0", 
    # description="Video Generation API",
)

# Set all CORS enabled origins
if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Include API routers
app.include_router(auth_api_router, prefix=settings.API_V1_STR, tags=["Authentication"])
# Add other routers here for videos, payments etc. as they are developed

@app.get("/health", tags=["Health Check"])
async def health_check():
    """Simple health check endpoint."""
    return {"status": "ok", "message": f"Welcome to {settings.PROJECT_NAME}!"}

# If you want a root path for API docs redirection or basic info
@app.get("/", include_in_schema=False)
async def root():
    return {"message": f"Welcome to {settings.PROJECT_NAME}. Docs at /docs or /redoc."}

# To run the app (for development):
# uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Placeholder for Celery app if needed directly (though usually managed separately)
# from app.core.celery_app import celery_app 