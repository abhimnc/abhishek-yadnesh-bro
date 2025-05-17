# Backend Documentation - Phase 1 & 2: Core Setup, Auth, & Basic Video Tasks

This document details the backend implementation for Phase 1 and Phase 2 of the FastAPI Video Generation Platform.
*   **Phase 1**: Focused on establishing the core project structure, setting up user authentication (including email/password and Google OAuth2), defining initial database models (`User`, `OAuthAccount`, `Plan`), and integrating a basic Celery setup.
*   **Phase 2**: Added models for video generation tracking (`VideoGenerationTask`, `GeneratedVideo`, `GeneratedVideoAsset`), user usage (`UserVideoUsage`), implemented API endpoints for submitting video tasks and checking their status, created a dummy Celery task for simulation, and added a basic usage limit service.

## Table of Contents

1.  [Project Structure Overview](#project-structure-overview)
2.  [Core Components](#core-components)
    *   [Configuration (`app/core/config.py`)](#configuration-appcoreconfigpy)
    *   [Security Utilities (`app/core/security.py`)](#security-utilities-appcoresecuritypy)
    *   [OAuth Client (`app/core/oauth.py`)](#oauth-client-appcoreoauthpy)
    *   [Email Utilities (`app/core/email.py`)](#email-utilities-appcoreemailpy)
    *   [Celery Application (`app/core/celery_app.py`)](#celery-application-appcorecelery_apppy)
3.  [Database Layer](#database-layer)
    *   [Database Session (`app/db/session.py`)](#database-session-appdbsessionpy)
    *   [Base Model (`app/db/models/base_model.py`)](#base-model-appdbmodelsbase_modelpy)
    *   [User Models (`app/db/models/user_models.py`)](#user-models-appdbmodelsuser_modelspy)
    *   [Payment Models (`app/db/models/payment_models.py`)](#payment-models-appdbmodelspayment_modelspy)
    *   [Video Models (`app/db/models/video_models.py`)](#video-models-appdbmodelsvideo_modelspy)
    *   [Usage Models (`app/db/models/usage_models.py`)](#usage-models-appdbmodelsusage_modelspy)
    *   [CRUD Operations (`app/db/crud/`)](#crud-operations-appdbcrud)
        *   [Base CRUD (`crud_base.py`)](#base-crud-crud_basepy)
        *   [User CRUD (`crud_user.py`)](#user-crud-crud_userpy)
        *   [OAuth Account CRUD (`crud_oauth_account.py`)](#oauth-account-crud-crud_oauth_accountpy)
        *   [Plan CRUD (`crud_plan.py`)](#plan-crud-crud_planpy)
        *   [Video CRUD (`crud_video.py`)](#video-crud-crud_videopy)
        *   [Usage CRUD (`crud_usage.py`)](#usage-crud-crud_usagepy)
4.  [API Layer](#api-layer)
    *   [API Schemas (`app/api/v1/schemas.py`)](#api-schemas-appapiv1schemaspy)
    *   [API Dependencies (`app/api/v1/deps.py`)](#api-dependencies-appapiv1depspy)
    *   [Authentication Endpoints (`app/api/v1/endpoints/auth.py`)](#authentication-endpoints-appapiv1endpointsauthpy)
    *   [Video Endpoints (`app/api/v1/endpoints/videos.py`)](#video-endpoints-appapiv1endpointsvideospy)
5.  [Services Layer](#services-layer)
    *   [OAuth Service (`app/services/oauth_service.py`)](#oauth-service-appservicesoauth_servicepy)
    *   [Usage Service (`app/services/usage_service.py`)](#usage-service-appservicesusage_servicepy)
6.  [Background Tasks (Celery)](#background-tasks-celery)
    *   [Placeholder Tasks (`app/tasks/placeholder_tasks.py`)](#placeholder-tasks-apptasksplaceholder_taskspy)
    *   [Video Generation Task (`app/tasks/video_generation_tasks.py`)](#video-generation-task-apptasksvideo_generation_taskspy)
7.  [Main Application (`app/main.py`)](#main-application-appmainpy)
8.  [Database Migrations (Alembic)](#database-migrations-alembic)
    *   [Configuration (`alembic.ini`, `alembic/env.py`)](#configuration-alembicini-alembicenvpy)
    *   [Usage](#usage)
9.  [Supporting Files](#supporting-files)
    *   [`requirements.txt`](#requirementstxt)
    *   [`.gitignore`](#gitignore)
    *   [`.env.example` & `.env`](#envexample--env)
10. [Running the Application](#running-the-application)
    *   [Prerequisites](#prerequisites)
    *   [Setting up the Environment](#setting-up-the-environment)
    *   [Database Migrations](#database-migrations)
    *   [Running FastAPI Server](#running-fastapi-server)
    *   [Running Celery Worker](#running-celery-worker)
11. [Key Decisions & Considerations for Phase 1](#key-decisions--considerations-for-phase-1)
12. [Phase 2 Implementation Summary](#phase-2-implementation-summary)

---

## 1. Project Structure Overview

The project structure after Phase 2:

```
video_generator_api/
├── alembic/                  # Alembic migration scripts and environment
├── app/
│   ├── __init__.py
│   ├── api/
│   │   ├── __init__.py
│   │   └── v1/
│   │       ├── __init__.py
│   │       ├── deps.py       # API dependencies (get_current_user, get_usage_service, etc.)
│   │       ├── endpoints/
│   │       │   ├── __init__.py
│   │       │   ├── auth.py   # Authentication endpoints
│   │       │   └── videos.py # Video task creation and status endpoints (Phase 2)
│   │       └── schemas.py    # Pydantic schemas for API I/O (incl. video schemas)
│   ├── core/
│   │   ├── __init__.py
│   │   ├── celery_app.py   # Celery app instance (includes video task)
│   │   ├── config.py
│   │   ├── email.py
│   │   ├── oauth.py
│   │   └── security.py
│   ├── db/
│   │   ├── __init__.py
│   │   ├── crud/
│   │   │   ├── __init__.py
│   │   │   ├── crud_base.py
│   │   │   ├── crud_oauth_account.py
│   │   │   ├── crud_plan.py
│   │   │   ├── crud_user.py
│   │   │   ├── crud_video.py # Video CRUD operations (Phase 2)
│   │   │   └── crud_usage.py # Usage CRUD operations (Phase 2)
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── base_model.py
│   │   │   ├── payment_models.py
│   │   │   ├── user_models.py
│   │   │   ├── video_models.py # Video models (Phase 2)
│   │   │   └── usage_models.py # Usage model (Phase 2)
│   │   └── session.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── oauth_service.py
│   │   └── usage_service.py  # Usage limit checking service (Phase 2)
│   ├── tasks/
│   │   ├── __init__.py
│   │   ├── placeholder_tasks.py
│   │   └── video_generation_tasks.py # Dummy video processing task (Phase 2)
│   └── main.py               # FastAPI app (includes video router)
├── .env
├── .env.example
├── .gitignore
├── alembic.ini
└── requirements.txt
```

---

## 2. Core Components

### Configuration (`app/core/config.py`)

*   **Purpose**: Manages application settings using Pydantic's `BaseSettings`. Settings are loaded from environment variables (via a `.env` file).
*   **Key Features**:
    *   Loads variables like `DATABASE_URL`, `SECRET_KEY`, JWT settings (including `REFRESH_TOKEN_TYPE_CLAIM`), Google OAuth credentials, Celery broker/backend URLs, and API prefix.
    *   `REFRESH_TOKEN_TYPE_CLAIM`: A string (e.g., "refresh") used as a claim within JWT refresh tokens to distinguish them from access tokens.
    *   Uses `@lru_cache` for `get_settings()` to ensure settings are loaded once.
    *   Includes validators for `DATABASE_URL` and `BACKEND_CORS_ORIGINS`.
    *   The `FERNET_KEY` for encrypting OAuth tokens is a critical setting. `OAUTH_TOKEN_ENCRYPTION_KEY` might be a deprecated or alternative name; `FERNET_KEY` is actively used.
    *   **Email Settings**: Includes SMTP configuration (`SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`), email sender details (`EMAIL_FROM`, `EMAIL_FROM_NAME`), and verification token expiry (`EMAIL_VERIFICATION_TOKEN_EXPIRE_HOURS`).
    *   **Server Host**: `SERVER_HOST` setting for generating full URLs in emails.
*   **Usage**: `from app.core.config import settings` allows access to settings throughout the application.

### Security Utilities (`app/core/security.py`)

*   **Purpose**: Provides security-related functions.
*   **Key Features**:
    *   **Password Hashing**: Uses `passlib` with `bcrypt` for securely hashing and verifying passwords (`get_password_hash`, `verify_password`).
    *   **JWT Management**: Uses `python-jose` for creating and decoding JWTs (`create_access_token`, `create_refresh_token`, `decode_token`).
        *   `create_refresh_token()` includes a `type` claim in the JWT payload, using `settings.REFRESH_TOKEN_TYPE_CLAIM` to identify it as a refresh token.
        *   Access and refresh tokens have configurable expiry times.
    *   **Fernet Encryption**: Uses `cryptography.fernet` for symmetric encryption/decryption of sensitive data, specifically OAuth tokens stored in the database (`encrypt_data`, `decrypt_data`). The `FERNET_KEY` from settings is used for this.

### OAuth Client (`app/core/oauth.py`)

*   **Purpose**: Configures the OAuth client using `authlib`.
*   **Key Features**:
    *   Initializes an `OAuth` instance from `authlib.integrations.starlette_client`.
    *   Registers the Google OAuth client (`oauth.google`) if `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` are present in the settings.
    *   Specifies Google's OpenID configuration URL and the required scopes (`openid email profile`).
*   **Note**: The `GOOGLE_REDIRECT_URI` configured in `.env` must match one registered in the Google Cloud Console for the OAuth client. This URI is typically used when generating the authorization URL in the `OAuthService`.

### Email Utilities (`app/core/email.py`)

*   **Purpose**: Provides functions for sending emails, particularly verification emails.
*   **Key Features**:
    *   Uses Python's standard library `smtplib` and MIME modules for email composition.
    *   `send_verification_email(email_to, verification_token)`: Sends an email with a verification link to the user.
    *   Creates both HTML and plain text email bodies for better compatibility.
    *   Includes proper email headers (From, To, Subject, Date, Message-ID).
    *   Uses SSL connection for secure communication with the SMTP server.
    *   Comprehensive error handling and logging for email sending failures.
*   **Usage**: Called from authentication endpoints when user registration or verification token renewal is needed.

### Celery Application (`app/core/celery_app.py`)

*   **Purpose**: Defines and configures the Celery application instance for background task processing.
*   **Key Features**:
    *   Creates a `Celery` instance, configured with broker and backend URLs from `settings`.
    *   Automatically discovers tasks from modules listed in the `include` parameter (e.g., `app.tasks.placeholder_tasks`).
    *   Sets default configurations like JSON serialization, UTC timezone.
*   **Usage**: Celery workers will be started using this application instance.

---

## 3. Database Layer

The database layer uses SQLModel (which combines SQLAlchemy and Pydantic) for ORM and PostgreSQL as the database. All database operations are asynchronous.

### Database Session (`app/db/session.py`)

*   **Purpose**: Manages asynchronous database sessions.
*   **Key Features**:
    *   Creates an `async_engine` using `create_async_engine` from `sqlalchemy.ext.asyncio`.
    *   Defines `AsyncSessionLocal`, a sessionmaker for creating `AsyncSession` instances. `expire_on_commit=False` is set, which is important for FastAPI.
    *   Provides an async dependency `get_async_session()` for use in API endpoints. This dependency handles session creation, commit on success, rollback on error, and closing the session.
    *   Includes an `init_db()` function (commented out by default in `main.py` startup) for creating all tables based on SQLModel metadata. This is mainly for development/testing; Alembic is used for production schema management.

### Base Model (`app/db/models/base_model.py`)

*   **Purpose**: Defines a `SQLModelBase` class that other SQLModel table models inherit from.
*   **Key Features**:
    *   `id`: UUID primary key, auto-generated.
    *   `created_at`: Timestamp (with timezone), defaults to `CURRENT_TIMESTAMP` at the database level.
    *   `updated_at`: Timestamp (with timezone), defaults to `CURRENT_TIMESTAMP` and automatically updates to `CURRENT_TIMESTAMP` on modification at the database level.

### User Models (`app/db/models/user_models.py`)

*   **`AuthProvider` (Enum)**: Defines authentication providers (`email`, `google`). Uses `sqlalchemy.dialects.postgresql.ENUM` for database-level enum type.
*   **`User` (SQLModel, table=True)**:
    *   Inherits from `SQLModelBase`.
    *   Table name: `user_account`.
    *   **Core Fields**: `email` (unique, indexed), `hashed_password` (nullable for OAuth users), `full_name`, `is_active`, `is_superuser`, `auth_provider`, `avatar_url`, `last_login_at`.
    *   **Email Verification Fields**: 
        *   `email_verification_token`: For storing a unique token sent in verification emails.
        *   `email_verification_token_expires_at`: Timestamp indicating when the verification token expires.
    *   Includes a PostgreSQL-specific index `idx_user_email_lower` for case-insensitive unique email checks using `LOWER(email)`.
    *   Relationship: `oauth_accounts` (one-to-many with `OAuthAccount`).
*   **`OAuthAccount` (SQLModel, table=True)**:
    *   Inherits from `SQLModelBase`.
    *   Fields: `user_id` (FK to `User`), `provider`, `provider_user_id`, `encrypted_access_token` (TEXT), `encrypted_refresh_token` (TEXT), `expires_at`.
    *   Constraints: Unique constraint on (`provider`, `provider_user_id`). Index on (`user_id`, `provider`).
    *   Relationship: `user` (many-to-one with `User`).

### Payment Models (`app/db/models/payment_models.py`)

*   **`Plan` (SQLModel, table=True)**:
    *   Inherits from `SQLModelBase`.
    *   Fields: `name` (unique), `stripe_price_id` (unique, indexed), `video_limit_per_period`, `max_video_duration_seconds`, `features` (JSONB), `price_monthly` (Decimal), `price_yearly` (Decimal), `currency`, `description`, `is_active`, `display_order`.
    *   This model represents subscription plans available in the system.

### Video Models (`app/db/models/video_models.py`)

*   **Purpose**: Defines models related to video generation tasks and their outputs. Added in Phase 2.
*   **Key Components**:
    *   `VideoGenerationTaskStatus` (Enum): Defines possible statuses (`pending`, `processing`, `completed`, `failed`, `cancelled`). Uses `sqlalchemy.dialects.postgresql.ENUM` for database type.
    *   `VideoGenerationTask` (SQLModel, table=True): Represents a request to generate a video.
        *   Fields: `user_id` (FK), `prompt_text`, `status` (Enum), `progress_percentage`, `error_message` (nullable), `celery_task_id` (nullable).
        *   Relationship: One-to-one with `GeneratedVideo` (via `generated_video` back-populating attribute).
    *   `GeneratedVideo` (SQLModel, table=True): Represents the final generated video metadata.
        *   Fields: `task_id` (FK, unique), `user_id` (FK, denormalized), `title`, `final_video_url` (nullable), `duration_seconds` (nullable), `visibility`.
        *   Relationships: One-to-one back to `VideoGenerationTask` (`task`), one-to-many to `GeneratedVideoAsset` (`assets`).
    *   `GeneratedVideoAsset` (SQLModel, table=True): Represents individual assets (like images) used in a video.
        *   Fields: `video_id` (FK), `asset_type`, `order_index`, `asset_url`.
        *   Relationship: Many-to-one back to `GeneratedVideo` (`video`).

### Usage Models (`app/db/models/usage_models.py`)

*   **Purpose**: Defines models for tracking user resource usage, specifically video generation counts per period. Added in Phase 2.
*   **Key Components**:
    *   `UserVideoUsage` (SQLModel, table=True): Tracks video creations per user per month.
        *   Fields: `user_id` (FK), `period_identifier` (YYYY-MM format), `videos_created_this_period`, `period_start_date`, `period_end_date`.
        *   Constraint: Unique constraint on (`user_id`, `period_identifier`).

### CRUD Operations (`app/db/crud/`)

#### Base CRUD (`crud_base.py`)

*   `CRUDBase`: A generic class providing common async CRUD methods: `get`, `get_multi`, `get_multi_with_total_count`, `create`, `update`, `remove`.
*   Uses Pydantic schemas for input type validation (`CreateSchemaType`, `UpdateSchemaType`).

#### User CRUD (`crud_user.py`)

*   `CRUDUser`: Inherits from `CRUDBase` for the `User` model.
*   `get_by_email()`: Fetches a user by email (case-insensitive).
*   `get_by_verification_token()`: Fetches a user by their email verification token.
*   `create()`: Original method for creating users, primarily for email/password signup, expecting `UserCreateSchema`. Hashes password and sets `auth_provider`.
*   `create_user_oauth()`: New method specifically for creating users that can accommodate OAuth signups or internal user creation. Expects `UserCreateInternalSchema`, which allows for an optional `hashed_password` and explicit `auth_provider`.
*   `update_last_login()`: Updates the `last_login_at` timestamp for a user.
*   Helper methods: `is_superuser()`, `is_active()`.
*   An instance `user_crud` is created for use in services and API endpoints.

#### OAuth Account CRUD (`crud_oauth_account.py`)

*   `CRUDOAuthAccount`: Inherits from `CRUDBase` for the `OAuthAccount` model.
*   Defines Pydantic schemas `OAuthAccountCreateSchema` and `OAuthAccountUpdateSchema` for data validation during CRUD operations. These schemas expect already encrypted token data.
*   `get_by_provider_and_user_id()`: Fetches an OAuth account by provider and provider's user ID. (Renamed from `get_by_provider_user_id`).
*   `create_with_user_id()`: Method for creating `OAuthAccount` instances. It expects an `OAuthAccountCreateSchema` where token fields (`encrypted_access_token`, `encrypted_refresh_token`) are assumed to be already encrypted by the calling service (e.g., `OAuthService`).
*   The base `update()` method from `CRUDBase` is used, expecting an `OAuthAccountUpdateSchema` with already encrypted token data if tokens are being updated.
*   An instance `oauth_account_crud` is created.

#### Plan CRUD (`crud_plan.py`)

*   `CRUDPlan`: Inherits from `CRUDBase` for the `Plan` model.
*   Defines a basic `PlanUpdateSchema`.
*   `get_by_name()`: Fetches a plan by its name.
*   `get_active_plans()`: Fetches all active plans, ordered by `display_order`.
*   An instance `plan_crud` is created.

#### Video CRUD (`crud_video.py`)

*   **Purpose**: Provides CRUD operations for video-related models. Added in Phase 2.
*   **Key Components**:
    *   Internal Pydantic schemas (`VideoGenerationTaskCreateSchema`, etc.) for validation.
    *   `CRUDVideoGenerationTask`: Inherits `CRUDBase`.
        *   `update_status_and_progress()`: Atomically updates status, progress, error message using SQLAlchemy core `update`.
        *   `update_celery_task_id()`: Updates the Celery task ID.
        *   `get_by_user()`: Retrieves tasks for a user.
        *   `get_with_video()`: Retrieves a task and eagerly loads the related `GeneratedVideo`.
    *   `CRUDGeneratedVideo`: Inherits `CRUDBase`.
        *   `get_by_user()`: Retrieves videos for a user.
        *   `get_by_task_id()`: Retrieves a video by its task ID.
    *   `CRUDGeneratedVideoAsset`: Inherits `CRUDBase` (standard methods).
    *   Instantiated objects: `video_task_crud`, `generated_video_crud`, `video_asset_crud`.

#### Usage CRUD (`crud_usage.py`)

*   **Purpose**: Provides CRUD operations for the `UserVideoUsage` model. Added in Phase 2.
*   **Key Components**:
    *   `CRUDUserVideoUsage`: Inherits `CRUDBase`.
        *   `get_current_period_record()`: Fetches the record for the current month.
        *   `_get_current_month_period()`: Helper to calculate month start/end dates.
        *   `get_or_create_current_period()`: Gets the current record or creates it if missing.
        *   `increment_usage()`: Atomically increments the `videos_created_this_period` counter using SQLAlchemy core `update`.
    *   Instantiated object: `user_usage_crud`.

---    

## 4. API Layer

Handles incoming HTTP requests, validation, and responses. Versioned under `/api/v1`.

### API Schemas (`app/api/v1/schemas.py`)

*   **Purpose**: Defines Pydantic models for request and response data validation and serialization.
*   **Key Schemas**:
    *   **Token**: `Token` (for login/OAuth callback response), `AccessTokenResponse` (for refresh token response), `TokenPayload` (data within JWT), `RefreshTokenRequest`.
    *   **User**: `UserBaseSchema`, `UserCreateSchema` (for email signup, includes password), `UserCreateInternalSchema` (for internal/OAuth user creation, `hashed_password` is optional), `UserUpdateSchema`, `UserReadSchema` (for API responses, uses `Config.from_attributes = True`), `PasswordChangeSchema`.
    *   **Plan**: `PlanBaseSchema`, `PlanCreateSchema`, `PlanReadSchema`.
    *   **OAuth**: `GoogleOAuthCallbackSchema` (for handling the OAuth callback query parameters).
    *   **OAuthAccount**: `OAuthAccountCreateSchema` (used by `OAuthService` to prepare data for `crud_oauth_account`).
    *   **Message**: `MessageResponse` (simple schema for returning text messages to the client).
*   **Phase 2 Additions**:
    *   Imported `VideoGenerationTaskStatus` Enum.
    *   `VideoCreateRequestSchema`: Input for creating a video task (`prompt_text`).
    *   `VideoTaskBaseSchema`: Base for task responses (`task_id`, `status`).
    *   `VideoTaskCreateResponseSchema`: Response after submitting a task (`task_id`, `status`, `message`).
    *   `VideoTaskStatusResponseSchema`: Response for checking task status (`task_id`, `status`, `progress_percentage`, `error_message`, `video_id`, `video_url`).
    *   `GeneratedVideoReadSchema`: Basic schema for listing completed videos (future use).
*   Uses `EmailStr`, `HttpUrl`, `datetime` for specific field type validation.

### API Dependencies (`app/api/v1/deps.py`)

*   **Purpose**: Defines FastAPI dependencies used by API endpoints.
*   **Key Dependencies**:
    *   `reusable_oauth2`: An `OAuth2PasswordBearer` instance configured with the token URL (`/api/v1/auth/login`).
    *   `get_async_session`: (Imported from `app.db.session`) Provides a database session to endpoints.
    *   `get_current_user()`: Decodes the JWT from the `Authorization: Bearer` header, validates it, and fetches the corresponding user from the database. Raises `HTTPException` for errors.
    *   `get_current_active_user()`: Depends on `get_current_user` and checks if the user is active.
    *   `get_current_active_superuser()`: Depends on `get_current_active_user` and checks if the user is a superuser.
*   **Phase 2 Additions**:
    *   `get_usage_service()`: Dependency provider that creates and returns an instance of `UsageService`.

### Authentication Endpoints (`app/api/v1/endpoints/auth.py`)

*   **Purpose**: Implements all authentication-related API endpoints. Relies on `app.services.oauth_service.OAuthService` for Google OAuth logic.
*   **Email Registration & Verification Endpoints**:
    *   **`POST /signup`**: Creates a new user via email/password.
        *   Request: `UserCreateSchema`.
        *   Response: `MessageResponse` (success message instructing to check email).
        *   Logic: Checks if user already exists. Creates inactive user with a verification token. Sends verification email.
    *   **`GET /verify-email`**: Verifies a user's email address using a token.
        *   Request: `token` query parameter.
        *   Response: `MessageResponse` (verification success).
        *   Logic: Validates token, checks expiration, activates user account, clears token data.
    *   **`POST /resend-verification-email`**: Resends a verification email.
        *   Request: `email` in request body.
        *   Response: `MessageResponse` (email sent confirmation).
        *   Logic: Finds user by email, generates new token, updates user record, sends new verification email.
*   **Standard Auth Endpoints**:
    *   **`POST /login`**: Logs in a user with email and password.
        *   Request: `OAuth2PasswordRequestForm` (username=email, password).
        *   Response: `Token` (access and refresh tokens).
        *   Logic: Authenticates user, checks if active, updates `last_login_at`, generates JWTs.
    *   **`POST /refresh-token`**: Refreshes an access token using a refresh token.
        *   Request: `RefreshTokenRequest`.
        *   Response: `AccessTokenResponse` (new access token).
        *   Logic: Validates refresh token (checking `type` claim), issues new access token.
    *   **`POST /logout`**: Placeholder for logout. For JWTs, this is mainly client-side token deletion.
        *   Response: `204 No Content`.
    *   **`GET /me`**: Gets the current authenticated user's details.
        *   Requires Auth: Depends on `get_current_active_user`.
        *   Response: `UserReadSchema`.
    *   **`PATCH /me`**: Updates the current authenticated user's details.
        *   Requires Auth: Depends on `get_current_active_user`.
        *   Request: `UserUpdateSchema`.
        *   Response: `UserReadSchema`.
    *   **`POST /me/change-password`**: Changes the current authenticated user's password.
        *   Requires Auth: Depends on `get_current_active_user`.
        *   Request: `PasswordChangeSchema`.
        *   Response: `204 No Content`.
*   **Google OAuth2 Endpoints**:
    *   **`GET /login/google`**: Initiates Google OAuth2 login flow.
        *   Depends on `get_oauth_service` from `app.services.oauth_service`.
        *   Calls `oauth_service.get_google_authorization_url()` which generates the redirect URL to Google.
        *   Redirects user to Google's authentication page.
    *   **`GET /login/google/callback`**: Handles the callback from Google after authentication.
        *   Depends on `get_oauth_service`.
        *   Calls `oauth_service.process_google_login()` which:
            *   Exchanges authorization code for tokens from Google.
            *   Fetches user info from Google.
            *   Finds or creates the user and links/updates the `OAuthAccount`.
            *   Handles encryption of Google's tokens before storage.
            *   Generates application-specific JWTs (access and refresh tokens).
        *   Response: `Token`.

### Video Endpoints (`app/api/v1/endpoints/videos.py`)

*   **Purpose**: Implements endpoints for video task creation and status checking. Added in Phase 2.
*   **Endpoints**: 
    *   **`POST /`**: (Submit a new video generation task)
        *   Requires Auth: Depends on `get_current_active_user`.
        *   Request: `VideoCreateRequestSchema` (`prompt_text`).
        *   Dependencies: `get_async_session`, `get_current_active_user`, `get_usage_service`.
        *   Logic:
            1.  Calls `usage_service.check_and_increment_usage()` (raises 403 if limit reached).
            2.  Creates `VideoGenerationTask` record via `video_task_crud.create()`.
            3.  Commits transaction (task creation & usage increment).
            4.  Enqueues `simulate_video_processing` Celery task.
            5.  Updates the DB task with the Celery task ID (in a separate transaction context for safety).
            6.  Handles potential Celery enqueue errors (attempts to mark task as failed).
        *   Response: `VideoTaskCreateResponseSchema` (Status 202 Accepted).
    *   **`GET /{task_id}/status`**: (Get the status of a video generation task)
        *   Requires Auth: Depends on `get_current_active_user`.
        *   Dependencies: `get_async_session`, `get_current_active_user`.
        *   Logic:
            1.  Fetches `VideoGenerationTask` using `video_task_crud.get_with_video()` (eager loads related `GeneratedVideo`).
            2.  Checks if task exists (404 if not).
            3.  Checks if the current user owns the task (403 if not, superusers bypass).
            4.  Formats `VideoTaskStatusResponseSchema`, including `video_id` and `video_url` if the task is 'completed' and the associated `GeneratedVideo` exists.
        *   Response: `VideoTaskStatusResponseSchema`.

--- 

## 5. Services Layer

Contains business logic that orchestrates operations between the API layer and the database/external services.

### OAuth Service (`app/services/oauth_service.py`)

*   **Purpose**: Encapsulates the logic for processing Google OAuth 2.0 logins.
*   **`OAuthService` Class**:
    *   **Initialization**: Takes an `AsyncSession` as a dependency. Initializes the Google client (`self.google_client`) from `app.core.oauth.oauth`. Includes basic checks for client availability.
    *   **`get_google_authorization_url(request: Request)` Method**:
        *   Constructs the redirect URI for the Google callback.
        *   Uses `self.google_client.create_authorization_url()` to generate the Google authentication URL and a `state` parameter for CSRF protection.
        *   Stores the `state` in the user's session if `SessionMiddleware` is active.
        *   Returns the authorization URL.
    *   **`process_google_login(request: Request)` Method**:
        *   Verifies the `state` parameter from the callback against the one stored in the session (if applicable) to prevent CSRF.
        *   Exchanges the authorization code (from `request`) for an access token from Google using `self.google_client.authorize_access_token()`.
        *   Fetches user information from Google using the obtained token (typically from the `userinfo` claim in the ID token or by calling the userinfo endpoint).
        *   Normalizes the email (e.g., to lowercase).
        *   **User and OAuthAccount Handling**:
            1.  Searches for an existing `OAuthAccount` using `oauth_account_crud.get_by_provider_and_user_id()`.
            2.  **Existing `OAuthAccount`**:
                *   Retrieves the associated `User`. Handles potential data inconsistencies if the user is missing.
                *   Updates the stored Google OAuth tokens (`encrypted_access_token`, `encrypted_refresh_token`, `expires_at`) in the `OAuthAccount` after encrypting them with `security.encrypt_data()`.
            3.  **No Existing `OAuthAccount`**:
                *   Searches for an existing `User` by email using `user_crud.get_by_email()`.
                *   **Existing `User` (by email)**:
                    *   Links the Google account. Checks for provider conflicts (e.g., if email is already linked to a different OAuth provider).
                    *   Updates `User.auth_provider` to `AuthProvider.GOOGLE` if it was `AuthProvider.EMAIL`.
                    *   Optionally updates user's `avatar_url` or `full_name` from Google profile if not already set.
                *   **New `User`**:
                    *   Creates a new `User` record using `user_crud.create_user_oauth()` with `UserCreateInternalSchema` (no password initially, `auth_provider` set to `GOOGLE`).
                *   Creates a new `OAuthAccount` record using `oauth_account_crud.create_with_user_id()`, storing encrypted Google tokens.
        *   Checks if the processed user is active.
        *   Updates the user's `last_login_at` timestamp.
        *   Generates application-specific JWT access and refresh tokens for the authenticated user using `security.create_access_token()` and `security.create_refresh_token()`.
        *   Returns a tuple: `(User, app_access_token, app_refresh_token)`.
*   **`get_oauth_service()` Dependency**: A FastAPI dependency provider function that creates and returns an instance of `OAuthService`.

### Usage Service (`app/services/usage_service.py`)

*   **Purpose**: Encapsulates logic for checking and managing user resource usage limits. Added in Phase 2.
*   **`UsageService` Class**: 
    *   **Initialization**: Takes an `AsyncSession`.
    *   **`check_and_increment_usage(user: User)` Method**:
        1.  Gets or creates the `UserVideoUsage` record for the current month using `user_usage_crud`.
        2.  Compares `videos_created_this_period` against a hardcoded limit (`DEFAULT_FREE_PLAN_VIDEO_LIMIT = 5` for Phase 2).
        3.  Raises `HTTPException` (403 Forbidden) if the limit is reached.
        4.  If limit not reached, calls `user_usage_crud.increment_usage()` to increment the counter.
        5.  **Important**: Does not commit the transaction; this is handled by the calling API endpoint to ensure atomicity with task creation.

---   

## 6. Background Tasks (Celery)

Celery is set up for handling long-running background operations, though no specific long tasks are implemented in Phase 1 beyond placeholders.

### Placeholder Tasks (`app/tasks/placeholder_tasks.py`)

*   **Purpose**: Provides example Celery tasks to verify the Celery setup.
*   **Tasks**:
    *   `example_task(x, y)`: A simple task that adds two numbers after a simulated delay.
    *   `another_example_task(message)`: Another simple task that processes a string message.
*   These tasks are included in the `celery_app` and can be called to test worker functionality.
*   Both tasks include logging via print statements to demonstrate task execution progress.
*   The first task uses `acks_late=True` to demonstrate how to configure Celery to acknowledge tasks only after successful completion.

### Video Generation Task (`app/tasks/video_generation_tasks.py`)

*   **Purpose**: Defines the (currently dummy) Celery task for processing video generation requests. Added in Phase 2.
*   **Task**: `simulate_video_processing(task_db_id_str: str)`
    *   `@celery_app.task(acks_late=True, bind=True)`: Registered Celery task.
    *   **Logic**: 
        1.  Takes the database ID of the `VideoGenerationTask` as input.
        2.  Uses nested async helper functions (`update_task_status`, `run_simulation`) and `asyncio.run()` to manage async DB operations within the sync Celery task runner.
        3.  Updates task status to 'processing'.
        4.  Simulates work steps with `time.sleep()` and updates `progress_percentage` incrementally.
        5.  Randomly determines success or failure.
        6.  On success: Creates a `GeneratedVideo` record with a placeholder URL and updates task status to 'completed'.
        7.  On failure: Updates task status to 'failed' and sets an error message.
        8.  Includes error handling to attempt marking the task as 'failed' if an unexpected exception occurs during simulation.
    *   **Note**: The use of `asyncio.run()` inside a sync task is functional for simulation but should be refactored for production async workers (e.g., using `async def` Celery tasks). 

--- 

## 7. Main Application (`app/main.py`)

*   **Purpose**: Initializes the FastAPI application, sets up middleware, includes API routers, and defines startup/shutdown events.
*   **Key Features**:
    *   Creates a `FastAPI` app instance with a project title and OpenAPI URL.
    *   Uses `asynccontextmanager` for the `lifespan` parameter to handle startup and shutdown events.
    *   **CORS Middleware**: Configured if `BACKEND_CORS_ORIGINS` is set in `settings`.
    *   **Session Middleware (Recommended for OAuth CSRF)**: If robust CSRF protection for OAuth is desired, `Starlette`'s `SessionMiddleware` should be added here, configured with `settings.SECRET_KEY`.
    *   **Routers**: Includes the `auth_router_v1` from `app.api.v1.endpoints.auth` under the prefix `/api/v1/auth`.
    *   **Health Check**: A simple `/health` endpoint providing an API status check.
    *   **Root Endpoint**: A `/` endpoint that provides a welcome message.
*   **Phase 2 Changes**:
    *   Imports `videos` router from `app.api.v1.endpoints`.
    *   Includes the `video_router_v1.router` using `app.include_router` with prefix `/api/v1/videos` and tag "Videos".
*   **Note**: Database initialization function `init_db()` is commented out, as Alembic is used for schema management in production.

--- 

## 8. Database Migrations (Alembic)

Alembic is used for managing database schema migrations.

### Configuration (`alembic.ini`, `alembic/env.py`)

*   **`alembic.ini`**:
    *   The `sqlalchemy.url` is configured to use an environment variable: `sqlalchemy.url = %(DATABASE_URL)s`. This means the `DATABASE_URL` must be available in the environment when running Alembic commands.
*   **`alembic/env.py`**:
    *   **Phase 2 Changes**:
        *   Imports all new models (`VideoGenerationTask`, `GeneratedVideo`, `GeneratedVideoAsset`, `UserVideoUsage`) to ensure `autogenerate` detects them.
        *   Added `load_dotenv()` to load `.env` file.
        *   Added standard SQLAlchemy naming conventions to `SQLModel.metadata`.
        *   Added `connection.execute()` calls within `do_run_migrations` to conditionally create the custom PostgreSQL ENUM types (`videogenerationtaskstatus`, `authprovider`) using `DO $$ ... END $$;` blocks. This ensures types exist before tables are created/modified.
        *   Ensures `DATABASE_URL` is fetched from environment variables.

### Usage

1.  **Initialization (One-time)**:
    ```bash
    cd backend/video_generator_api
    alembic init alembic
    ```
    Then, modify `alembic.ini` and replace `alembic/env.py` with the provided content.

2.  **Creating a New Migration**:
    After making changes to your SQLModel definitions:
    ```bash
    # Ensure DATABASE_URL is set in your environment (e.g., via .env and a tool like `uv run --`)
    alembic revision -m "your_migration_message" --autogenerate
    ```
    Inspect the generated script in `alembic/versions/`.

3.  **Applying Migrations**:
    ```bash
    # Ensure DATABASE_URL is set
    alembic upgrade head  # Applies all pending migrations
    ```

--- 

## 9. Supporting Files

*   **`requirements.txt`**: Lists all Python dependencies for the project (e.g., `fastapi`, `uvicorn`, `sqlmodel`, `psycopg2-binary`, `alembic`, `python-jose`, `passlib`, `authlib`, `celery`, `redis`). Install using `uv pip install -r requirements.txt`.
*   **`.gitignore`**: Standard Python `.gitignore` to exclude common unnecessary files and directories (e.g., `__pycache__`, `.env`, `venv/`).
*   **`.env.example` & `.env`**:
    *   `.env.example`: Provides a template for required environment variables.
    *   `.env`: (Gitignored) Stores actual environment variable values for local development (e.g., database credentials, API keys, `FERNET_KEY`). This file is loaded by `app/core/config.py`.

--- 

## 10. Running the Application

### Prerequisites

*   Python 3.10+
*   `uv` (or `pip`) for package management
*   PostgreSQL server running
*   Redis server running (for Celery)
*   Google OAuth2 Client ID and Secret (if testing Google login)
*   SMTP server access (for email verification)

### Setting up the Environment

1.  **Clone the repository** (if applicable).
2.  **Navigate to the project directory**: `cd backend/video_generator_api`
3.  **Create and activate a virtual environment**:
    ```bash
    python -m venv venv
    source venv/bin/activate  # Linux/macOS
    # venv\Scripts\activate    # Windows
    ```
4.  **Install dependencies**:
    ```bash
    uv pip install -r requirements.txt
    ```
5.  **Set up `.env` file**:
    *   Copy `.env.example` to `.env`.
    *   Fill in the required values, especially:
        *   `DATABASE_URL` (e.g., `postgresql+asyncpg://user:password@host:port/dbname`)
        *   `SECRET_KEY` (generate a strong random string, also used for SessionMiddleware if enabled)
        *   `FERNET_KEY` (generate using `from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())` in a Python shell)
        *   Google OAuth credentials if testing that feature.
        *   SMTP settings for email functionality.

### Database Migrations

1.  **Initialize Alembic (if not done)**:
    ```bash
    alembic init alembic
    ```
    Modify `alembic.ini` and `alembic/env.py` as per the documentation above.
2.  **Create Initial Migration (if starting fresh)**:
    ```bash
    # Ensure DATABASE_URL from .env is loaded or prefix the command
    alembic revision -m "create_initial_tables" --autogenerate
    ```
3.  **Apply Migrations**:
    ```bash
    alembic upgrade head
    ```

### Running FastAPI Server

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
The API will be accessible at `http://localhost:8000`. Interactive API documentation (Swagger UI) will be at `http://localhost:8000/docs`.

### Running Celery Worker

Open a new terminal, navigate to `backend/video_generator_api/`, activate the virtual environment, and run:
```bash
celery -A app.core.celery_app worker -l info -P solo # Use -P solo on Windows if default pool causes issues
```
Ensure your Redis server (specified in `CELERY_BROKER_URL` and `CELERY_RESULT_BACKEND`) is running.

--- 

## 11. Key Decisions & Considerations for Phase 1

*   **Async Operations**: All database interactions and potentially I/O-bound operations are implemented asynchronously (`async/await`) for better performance.
*   **SQLModel**: Chosen for its combination of SQLAlchemy's power and Pydantic's data validation, simplifying model and schema definition.
*   **JWT Authentication**: Standard token-based authentication with access and refresh tokens. Refresh tokens include a `type` claim for distinction and are returned in the response body. Secure HttpOnly cookies are a future consideration for web frontends.
*   **Email Verification Flow**: Implementation of a secure email verification flow where:
    *   Users start in an inactive state.
    *   A verification token is generated and sent via email.
    *   The token has a configurable expiration time.
    *   Users must verify their email to activate their account.
    *   Tokens can be regenerated if they expire.
*   **Email Service**: SMTP-based email service for sending verification emails with both HTML and plain text versions.
*   **OAuth Token Encryption**: Sensitive OAuth tokens obtained from providers (like Google) are encrypted using Fernet by the `OAuthService` before being stored in the database, enhancing security.
*   **OAuth CSRF Protection**: The `OAuthService` includes logic to store and verify the `state` parameter using FastAPI/Starlette sessions (if `SessionMiddleware` is enabled in `main.py`), which is recommended for CSRF protection.
*   **Case-Insensitive Email**: The `User` model includes a PostgreSQL-specific index for `LOWER(email)` to ensure case-insensitive uniqueness and lookups. Emails are also normalized to lowercase in the `OAuthService`.
*   **Clear Separation of Concerns**: The structure separates API endpoints (`auth.py`), business logic/external service interaction (`oauth_service.py`), CRUD operations, and core utilities.
*   **Configuration Management**: Centralized configuration via environment variables and Pydantic settings.
*   **Alembic for Migrations**: Standard tool for robust schema management.
*   **Basic Celery Integration**: Celery is set up, ready for more complex background tasks in later phases.

This documentation provides a snapshot of the backend after Phase 1. It will be updated as the project progresses through subsequent phases.

---

## 12. Phase 2 Implementation Summary

*   **Models**: Added database models for tracking video tasks (`VideoGenerationTask`), results (`GeneratedVideo`), assets (`GeneratedVideoAsset`), and monthly usage (`UserVideoUsage`).
*   **CRUD**: Implemented asynchronous CRUD operations for all new models.
*   **Usage Service**: Created a service (`UsageService`) to check video creation limits (currently hardcoded) and increment usage.
*   **API Endpoints**: Added `POST /api/v1/videos/` to submit tasks and `GET /api/v1/videos/{task_id}/status` to check progress.
*   **Celery Task**: Implemented a dummy Celery task (`simulate_video_processing`) that updates task status and progress in the database, simulating the generation process.
*   **Integration**: Integrated the new components: router included in `main.py`, Celery task included in `celery_app.py`, CRUDs used by endpoints/tasks, usage service used by the creation endpoint.
*   **Migrations**: Updated Alembic environment to handle new models and ensure custom ENUM types are created.
*   **Focus**: Phase 2 successfully sets up the infrastructure for submitting video tasks and monitoring their status, using a dummy backend process and basic usage limits, without integrating actual LLM or video processing tools yet.
