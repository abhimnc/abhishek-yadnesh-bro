## FastAPI Video Generation Platform: Detailed Plan

This plan focuses on a robust, scalable, and production-ready architecture.

**Project Goal:** To create a FastAPI application enabling users to sign up/login, generate videos from prompts (using LLMs for script, images, audio, SRT), and manage subscriptions for video creation limits and features.

---

### 1. Core Technologies & Setup

* **Programming Language:** Python 3.10+
* **Framework:** FastAPI
* **Asynchronous Task Queue:** Celery (with Redis or RabbitMQ as a message broker and result backend) - Crucial for long-running video generation tasks.
* **Database:** Supabase (PostgreSQL) - Provides a managed PostgreSQL instance, along with other backend services. We will be using it primarily for its database capabilities.
* **ORM:** SQLModel (combines SQLAlchemy and Pydantic, allowing models to be used both as database models and API schemas) - To be used with the Supabase PostgreSQL database.
* **Data Validation:** Pydantic (comes with FastAPI).
* **Authentication:**
    * JWT (JSON Web Tokens) for stateless authentication. `python-jose` and `passlib` (for password hashing, specifically bcrypt).
    * OAuth2 with Google authentication using `authlib` for social login integration. Access/refresh tokens for OAuth accounts stored encrypted (e.g., using Fernet symmetric encryption with an application-specific key).
* **LLM API Integrations (Abstracted Service Layer):**
    * An abstraction layer (`llm_service_interface.py`) will be created to allow for easier swapping or addition of LLM providers.
    * Script Generation: (e.g., OpenAI GPT-4/3.5-turbo, Anthropic Claude, Google Gemini)
    * Image Generation: (e.g., OpenAI DALL-E 3, Stability AI Stable Diffusion API, Midjourney API if available)
    * Text-to-Speech (TTS): (e.g., OpenAI TTS, ElevenLabs, Google Cloud TTS)
    * Speech-to-Text (SRT Generation): (e.g., OpenAI Whisper API, AssemblyAI, Google Cloud Speech-to-Text)
* **Video Processing:** `FFmpeg` (via `ffmpeg-python` wrapper).
* **Payment Gateway:** Stripe (excellent documentation, SDKs, and webhook support).
* **Cloud Storage:** Supabase Storage (integrated with Supabase), AWS S3, Google Cloud Storage, or Azure Blob Storage (for storing generated images, audio, SRT files, and final videos).
* **Containerization (Recommended for Production):** Docker, Docker Compose.
* **Environment Management:** `python-dotenv` for local development. Secure management of secrets (API keys, Supabase URL and service key, database credentials) using environment variables, with consideration for production systems like HashiCorp Vault or cloud provider secret managers.
* **Database Migrations:** Alembic (to be configured to work with the Supabase PostgreSQL instance).

---

### 2. Database Schema Design (PostgreSQL with SQLModel)

We'll need several models. All `id` fields will be UUID (Primary Key) unless stated. Timestamps are `TIMESTAMP WITH TIME ZONE (Default: NOW())`.

1.  **`User`**
    * `id`: UUID
    * `email`: VARCHAR(255) (Unique, Indexed - consider case-insensitive index: `CREATE INDEX idx_user_email_lower ON "user" (LOWER(email));`)
    * `hashed_password`: VARCHAR(255) (Nullable for OAuth users)
    * `full_name`: VARCHAR(100) (Optional)
    * `is_active`: BOOLEAN (Default: True)
    * `is_superuser`: BOOLEAN (Default: False)
    * `auth_provider`: VARCHAR(20) (e.g., 'email', 'google', Default: 'email')
    * `avatar_url`: VARCHAR(512) (Nullable)
    * `created_at`: TIMESTAMP WITH TIME ZONE
    * `updated_at`: TIMESTAMP WITH TIME ZONE
    * `last_login_at`: TIMESTAMP WITH TIME ZONE (Nullable)

2.  **`OAuthAccount`** (For managing multiple OAuth providers per user)
    * `id`: UUID
    * `user_id`: UUID (Foreign Key to `User.id`, Indexed, `ondelete="CASCADE"`)
    * `provider`: VARCHAR(20) (e.g., 'google', 'facebook', 'github')
    * `provider_user_id`: VARCHAR(255) (Provider's user ID)
    * `encrypted_access_token`: TEXT (Encrypted using a strong symmetric encryption like AES-256-GCM via Fernet, key managed in app config)
    * `encrypted_refresh_token`: TEXT (Encrypted, Nullable)
    * `expires_at`: TIMESTAMP WITH TIME ZONE (Nullable)
    * `created_at`: TIMESTAMP WITH TIME ZONE
    * `updated_at`: TIMESTAMP WITH TIME ZONE
    * UNIQUE (`provider`, `provider_user_id`)

3.  **`Plan`** (Subscription plans)
    * `id`: UUID
    * `name`: VARCHAR(100) (e.g., "Free Tier", "Pro Monthly")
    * `stripe_price_id`: VARCHAR(255) (Unique, from Stripe)
    * `video_limit_per_period`: INTEGER (e.g., per month)
    * `max_video_duration_seconds`: INTEGER (Nullable)
    * `features`: JSONB (e.g., `{"resolution": "1080p", "custom_watermark": false, "available_voices": ["voice_a", "voice_b"]}`)
    * `price_monthly`: DECIMAL(10, 2) (Nullable)
    * `price_yearly`: DECIMAL(10, 2) (Nullable)
    * `currency`: VARCHAR(3) (e.g., "USD")
    * `description`: TEXT (Nullable)
    * `is_active`: BOOLEAN (Default: True) (For soft-deleting plans)
    * `display_order`: INTEGER (Default: 0)

4.  **`Subscription`**
    * `id`: UUID
    * `user_id`: UUID (Foreign Key to `User.id`, Indexed, `ondelete="CASCADE"`)
    * `plan_id`: UUID (Foreign Key to `Plan.id`, Indexed, `ondelete="SET NULL"` or restrict)
    * `stripe_customer_id`: VARCHAR(255) (Unique)
    * `stripe_subscription_id`: VARCHAR(255) (Unique, Nullable if customer exists but no active subscription)
    * `status`: VARCHAR(50) (e.g., 'active', 'canceled', 'past_due', 'incomplete', 'trialing')
    * `current_period_start`: TIMESTAMP WITH TIME ZONE (Nullable)
    * `current_period_end`: TIMESTAMP WITH TIME ZONE (Nullable)
    * `cancel_at_period_end`: BOOLEAN (Default: False)
    * `created_at`: TIMESTAMP WITH TIME ZONE
    * `updated_at`: TIMESTAMP WITH TIME ZONE

5.  **`VideoGenerationTask`**
    * `id`: UUID
    * `user_id`: UUID (Foreign Key to `User.id`, Indexed, `ondelete="CASCADE"`)
    * `prompt_text`: TEXT (Main input prompt)
    * `user_prompt_details`: JSONB (Nullable, for more complex inputs like scene descriptions, style preferences)
    * `status`: VARCHAR(50) (e.g., 'pending', 'script_generating', 'image_generating', 'audio_generating', 'srt_generating', 'video_assembling', 'completed', 'failed', 'cancelled', Indexed)
    * `progress_percentage`: INTEGER (Nullable, Default: 0, 0-100)
    * `estimated_time_remaining_seconds`: INTEGER (Nullable)
    * `error_message`: TEXT (Nullable)
    * `celery_task_id`: VARCHAR(255) (Nullable, Indexed)
    * `retry_count`: INTEGER (Default: 0)
    * `created_at`: TIMESTAMP WITH TIME ZONE
    * `updated_at`: TIMESTAMP WITH TIME ZONE

6.  **`GeneratedVideo`**
    * `id`: UUID
    * `task_id`: UUID (Foreign Key to `VideoGenerationTask.id`, Unique, Indexed, `ondelete="CASCADE"`)
    * `user_id`: UUID (Foreign Key to `User.id`, Indexed, `ondelete="CASCADE"`)
    * `title`: VARCHAR(255) (Derived from prompt/script, potentially overridden by `user_defined_title`)
    * `user_defined_title`: VARCHAR(255) (Nullable)
    * `script_text`: TEXT (Nullable)
    * `final_video_url`: VARCHAR(512) (URL to video in cloud storage)
    * `srt_file_url`: VARCHAR(512) (URL to SRT in cloud storage)
    * `audio_file_url`: VARCHAR(512) (URL to audio in cloud storage)
    * `thumbnail_url`: VARCHAR(512) (Optional, URL to a thumbnail)
    * `duration_seconds`: INTEGER (Nullable)
    * `visibility`: VARCHAR(20) (Default: 'private', e.g., 'private', 'unlisted', 'public')
    * `generation_metadata`: JSONB (Nullable, e.g., models used, quality settings, aspect ratio)
    * `created_at`: TIMESTAMP WITH TIME ZONE
    * `updated_at`: TIMESTAMP WITH TIME ZONE (If allowing edits to metadata)

7.  **`GeneratedVideoAsset`** (Stores individual image/audio segment details)
    * `id`: UUID
    * `video_id`: UUID (Foreign Key to `GeneratedVideo.id`, Indexed, `ondelete="CASCADE"`)
    * `asset_type`: VARCHAR(20) (e.g., 'image', 'audio_segment')
    * `order_index`: INTEGER (Order of the asset in the video, e.g., sentence_index for images)
    * `source_prompt_text`: TEXT (Nullable, e.g., prompt for this specific image)
    * `asset_url`: VARCHAR(512) (URL to asset in cloud storage)
    * `asset_generation_metadata`: JSONB (Nullable, e.g., specific model used, generation parameters)
    * `status`: VARCHAR(50) (Default: 'completed', e.g., 'completed', 'failed_generation', 'placeholder_used')
    * `created_at`: TIMESTAMP WITH TIME ZONE

8.  **`UserVideoUsage`**
    * `id`: UUID
    * `user_id`: UUID (Foreign Key to `User.id`, Indexed, `ondelete="CASCADE"`)
    * `subscription_id`: UUID (Foreign Key to `Subscription.id`, Nullable, Indexed, `ondelete="SET NULL"`)
    * `period_identifier`: VARCHAR(7) (e.g., '2025-05' for monthly, or based on subscription cycle if not strictly calendar month)
    * `videos_created_this_period`: INTEGER (Default: 0)
    * `credits_used_this_period`: INTEGER (Default: 0) (If using a credit system more granular than video count)
    * `credits_allotted_this_period`: INTEGER (Based on plan at start of period)
    * `period_start_date`: TIMESTAMP WITH TIME ZONE
    * `period_end_date`: TIMESTAMP WITH TIME ZONE
    * `last_usage_timestamp`: TIMESTAMP WITH TIME ZONE (Nullable)
    * UNIQUE (`user_id`, `period_identifier`)

---

### 3. Application Structure (Directory Layout)

```
backend/
├── video_generator_api/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                     # FastAPI app instantiation and main routers
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   └── v1/
│   │   │       ├── __init__.py
│   │   │       ├── endpoints/
│   │   │       │   ├── __init__.py
│   │   │       │   ├── auth.py         # Login, Signup, OAuth2, Refresh, Logout, User Profile
│   │   │       │   └── videos.py       # Video creation, status (Phase 2)
│   │   │       │   # ├── payments.py     # Stripe checkout, webhooks, plans (future)
│   │   │       │   # └── admin.py        # (Optional) Admin-specific endpoints (future)
│   │   │       ├── deps.py             # Common dependencies (get_current_user, db_session, get_usage_service)
│   │   │       └── schemas.py          # Pydantic schemas (incl. video schemas)
│   │   ├── core/
│   │   │   ├── __init__.py
│   │   │   ├── config.py               # Settings (Pydantic BaseSettings)
│   │   │   ├── security.py             # Password hashing, JWT creation/validation, token encryption utils
│   │   │   ├── oauth.py                # OAuth2 client configuration and helpers
│   │   │   ├── email.py                # Email utilities
│   │   │   └── celery_app.py           # Celery application instance (incl. video task)
│   │   ├── db/
│   │   │   ├── __init__.py
│   │   │   ├── session.py              # Database session management (async)
│   │   │   ├── models/                 # SQLModel models
│   │   │   │   ├── __init__.py
│   │   │   │   ├── base_model.py       # Base model with common fields
│   │   │   │   ├── user_models.py
│   │   │   │   ├── video_models.py     # Video task, generated video, asset models (Phase 2)
│   │   │   │   ├── usage_models.py     # User video usage model (Phase 2)
│   │   │   │   └── payment_models.py
│   │   │   └── crud/                   # CRUD operations for each model
│   │   │       ├── __init__.py
│   │   │       ├── crud_base.py        # Generic CRUD base class
│   │   │       ├── crud_user.py
│   │   │       ├── crud_oauth_account.py
│   │   │       ├── crud_plan.py
│   │   │       ├── crud_video.py       # CRUD operations for video models (Phase 2)
│   │   │       └── crud_usage.py       # CRUD operations for usage model (Phase 2)
│   │   │       # └── ... (other cruds, future)
│   │   ├── services/                   # Business logic, interactions with external APIs
│   │   │   ├── __init__.py
│   │   │   ├── oauth_service.py        # OAuth2 providers integration (Google)
│   │   │   ├── usage_service.py        # Logic for tracking and checking user usage (Phase 2)
│   │   │   # ├── llm_service_interface.py # Defines common interface for LLM operations (future)
│   │   │   # ├── llm_providers/          # Implementations for specific LLM providers (future)
│   │   │   # │   ├── __init__.py
│   │   │   # │   ├── openai_service.py
│   │   │   # │   └── anthropic_service.py
│   │   │   # ├── video_processing_service.py # Video assembly using FFmpeg (future)
│   │   │   # ├── payment_service.py      # Stripe interaction logic (future)
│   │   │   # └── cloud_storage_service.py # Uploading/managing files in S3/GCS (future)
│   │   └── tasks/                      # Celery tasks
│   │       ├── __init__.py
│   │       ├── placeholder_tasks.py    # Basic placeholder tasks for testing Celery
│   │       ├── video_generation_tasks.py # Dummy video processing task (Phase 2)
│   │       # └── payment_tasks.py          # Background tasks related to payments (future)
│   ├── tests/                          # Unit and integration tests (future)
│   │   ├── __init__.py
│   │   ├── conftest.py
│   │   └── ... (test files mirroring app structure)
│   ├── .env.example                    # Example environment variables
│   ├── .env                            # Environment variables (ignored by git)
│   ├── .gitignore
│   ├── alembic/                        # Alembic migration scripts
│   │   ├── versions/                   # Migration versions
│   │   ├── env.py                      # Alembic environment configuration
│   │   ├── script.py.mako              # Template for migration scripts
│   │   └── README                      # Alembic README
│   ├── alembic.ini                     # Alembic configuration
│   ├── backend_documentation.md        # Documentation file (updated Phase 2)
│   └── requirements.txt                # Python dependencies
├── .venv/                              # Virtual environment (ignored by git)
├── pyproject.toml                      # Python project metadata
├── uv.lock                             # UV lock file
├── .python-version                     # Python version specification
├── plan.md                             # This planning document
└── README.md                           # Project README
```

---

### 4. API Endpoints Plan

**Authentication (`/api/v1/auth`)**

* **`POST /signup`**:
    * Request: User registration details (email, password, full\_name).
    * Response: User details (excluding password), access token, refresh token.
* **`POST /login`**:
    * Request: `OAuth2PasswordRequestForm` (username field will be used for email).
    * Response: Access token, refresh token, token type.
* **`POST /refresh-token`**:
    * Request: `{ "refresh_token": "string" }`.
    * Response: New access token, token type.
* **`POST /logout`**: (Requires Auth)
    * Logic: Client-side token deletion. Optionally, implement server-side JWT blacklisting (e.g., using Redis) if immediate invalidation is critical.
    * Response: `200 OK` or `204 No Content`.
* **`GET /me`**: (Requires Auth)
    * Response: Current authenticated user details (`User` model excluding sensitive info).
* **`PATCH /me`**: (Requires Auth)
    * Request: `{ "full_name": "Optional[str]", "avatar_url": "Optional[str]" }`.
    * Response: Updated user details.
* **`POST /me/change-password`**: (Requires Auth)
    * Request: `{ "current_password": "str", "new_password": "str" }`.
    * Response: `200 OK` or `204 No Content`.
* **`GET /login/google`**: (Initiates Google OAuth2 flow)
    * Redirects to Google authentication page.
* **`GET /login/google/callback`**:
    * Handles Google OAuth2 callback.
    * Logic:
        1.  Exchange authorization code for token from Google.
        2.  Get user info from Google.
        3.  Look up user by email or create if not exists. Update `User.auth_provider`, `User.avatar_url`.
        4.  Create/Update `OAuthAccount` (store encrypted tokens).
        5.  Generate JWT access and refresh tokens for our app.
        6.  Redirect to frontend with tokens (e.g., in URL params for SPA pickup, or set secure HttpOnly cookies). Consider an intermediate backend endpoint for the SPA to POST the auth code to, which then returns JWTs in the response body.

**Video Generation (`/api/v1/videos`)**

* **`POST /`**: (Create Video Request)
    * Requires Auth.
    * Request: `{ "prompt_text": "string", "user_prompt_details": { "title": "Optional[str]", "aspect_ratio": "16:9", "scenes": [ ... ] }, "output_preferences": { "include_srt_overlay": true } }`
    * Logic:
        1.  Verify user authentication and active status.
        2.  Check subscription status and usage limits via `usage_service`.
        3.  If allowed:
            * Create `VideoGenerationTask` record with 'pending' status, storing `prompt_text` and `user_prompt_details`.
            * Enqueue `generate_video_pipeline` Celery task with `task_id` and relevant parameters.
            * Tentatively update/record usage in `UserVideoUsage` (or confirm after task starts actual processing).
            * Response: `{ "task_id": "uuid", "status": "pending", "message": "Video generation initiated." }`
        4.  If not allowed: Response: `402 Payment Required` or `403 Forbidden` (e.g., "Upgrade plan or usage limit reached.").
* **`GET /{task_id}/status`**:
    * Requires Auth.
    * Response: `{ "task_id": "uuid", "status": "current_status", "progress_percentage": int, "estimated_time_remaining_seconds": int (optional), "error_message": "str" (optional) }`
* **`GET /`**: (List user's videos)
    * Requires Auth.
    * Params: `?skip=0&limit=20&status=completed&sort_by=created_at&order=desc`
    * Response: List of `GeneratedVideo` models (paginated).
* **`GET /{video_id}`**: (Get a specific completed video)
    * Requires Auth (ensure user owns the video or respects `visibility`).
    * Response: `GeneratedVideo` model details (including all URLs).
* **`DELETE /{video_id}`**: (Requires Auth)
    * Logic: Mark video as deleted (soft delete) or hard delete. If hard delete, enqueue a task to remove assets from cloud storage.
    * Response: `204 No Content`.

**Subscription & Payments (`/api/v1/payments`)**

* **`GET /plans`**: (No Auth or Requires Auth, depending on if you want to show plans before login)
    * Response: List of available `Plan` details (name, price, features, stripe\_price\_id).
* **`POST /create-checkout-session`**:
    * Requires Auth.
    * Request: `{ "plan_id": "uuid" }` (internal plan ID, map to `stripe_price_id`).
    * Logic: Uses Stripe API to create a checkout session. Store `stripe_customer_id` if new.
    * Response: `{ "checkout_url": "stripe_checkout_url", "session_id": "stripe_session_id" }`.
* **`POST /manage-subscription`**:
    * Requires Auth.
    * Logic: Uses Stripe API to create a Customer Portal session.
    * Response: `{ "portal_url": "stripe_customer_portal_url" }`.
* **`POST /webhook`**: (Stripe Webhook)
    * No Auth (public endpoint, Stripe request signature *must* be verified).
    * Request: Stripe event object.
    * Logic:
        * Verify Stripe signature.
        * Handle events: `checkout.session.completed`, `invoice.payment_succeeded`, `customer.subscription.updated`, `customer.subscription.deleted`, `invoice.payment_failed`.
        * Update `Subscription` and `UserVideoUsage` models accordingly (create/update subscription, status, period details, (re)set usage for new period).
    * Response: `200 OK` to Stripe.
* **`GET /subscription`**:
    * Requires Auth.
    * Response: Current user's `Subscription` details and associated `Plan` details.

---

### 5. Detailed Workflow for Video Generation (Celery Task)

`tasks.video_generation_tasks.generate_video_pipeline(task_id: UUID, generation_options: dict)`

1.  **Initialization:**
    * Fetch `VideoGenerationTask` record by `task_id`. Fetch user and their `Plan` details.
    * Update status to `script_generating`. Log start.
    * Set initial `progress_percentage`.

2.  **Step A: Create Script (LLM Call via `llm_service`)**
    * Input: `task.prompt_text` and `task.user_prompt_details`.
    * Call `llm_service.generate_script(...)`. Script should be structured (e.g., list of scenes, each with sentences).
    * Handle LLM API errors gracefully (retries with exponential backoff via Celery, specific error logging).
    * Store generated script structure (e.g., in `task.temp_script_data` or directly proceed).
    * Update task status to `image_generating`, update progress.

3.  **Step B: Generate Image Prompts & Images (LLM Calls via `llm_service`)**
    * For each sentence/scene in the script:
        * If user provided specific image prompts in `task.user_prompt_details.scenes`, use those.
        * Else, call `llm_service.generate_image_prompt_for_scene(scene_text)`.
        * Call `llm_service.generate_image(image_prompt, style_preferences_from_task_options)`. Returns image data/URL.
        * Upload image to cloud storage (`cloud_storage_service.upload_file(...)`). Get public URL.
        * Store image URL, source prompt, and metadata in a temporary list associated with this task.
    * Error Handling for Image Generation:
        * If an image fails after retries: Log error, use a pre-defined placeholder image, record this in the asset's status (`GeneratedVideoAsset.status = 'placeholder_used'`), and continue. Do not fail the entire video for one image.
    * Update task status to `audio_generating`, update progress.

4.  **Step C: Generate Audio (LLM Call via `llm_service`)**
    * Call `llm_service.generate_audio_for_script(full_script_text, voice_preferences_from_task_options)`.
    * Upload audio to cloud storage. Get public URL.
    * Store audio URL.
    * Update task status to `srt_generating`, update progress.

5.  **Step D: Generate SRT File (API Call or Library via `llm_service`)**
    * Call `llm_service.generate_srt_from_audio(audio_url_or_data)`. Evaluate STT services for timing accuracy.
    * Upload SRT file to cloud storage. Get public URL.
    * Store SRT URL.
    * Update task status to `video_assembling`, update progress.

6.  **Step E: Assemble Video (via `video_processing_service`)**
    * Download/access all generated images (or placeholders) and the main audio file (use signed URLs if direct access is not feasible/secure).
    * Use `video_processing_service.assemble_video(image_assets_info, audio_url, srt_url, output_options)`:
        * Synchronize images with audio:
            * Prioritize SRT timings for image/clip durations.
            * If SRT timings are imprecise or unavailable for certain segments, use estimated durations (e.g., based on sentence length/word count in script, or default duration per image, ensuring total image duration matches audio).
        * Overlay text from SRT onto video frames if `generation_options.include_srt_overlay` is true.
        * Apply other options like aspect ratio, resolution (based on plan/user choice).
    * Upload final video to cloud storage. Get public URL.
    * Clean up any temporary local files.

7.  **Finalization:**
    * Create `GeneratedVideo` record with all details (script, URLs, title, metadata).
    * Create `GeneratedVideoAsset` records for each image and other assets.
    * Update `VideoGenerationTask` status to `completed`, `progress_percentage` to 100.
    * Finalize `UserVideoUsage` update (confirm credits used).
    * Log completion.
    * (Optional) Send notification to user (e.g., email, WebSocket).

8.  **Error Handling (Throughout the pipeline):**
    * Use Celery's retry mechanisms (exponential backoff) for transient errors in external API calls.
    * If a critical step (e.g., script generation, audio generation, video assembly) fails after retries:
        * Update `VideoGenerationTask` status to `failed`.
        * Store a detailed `error_message`.
        * Log the error comprehensively.
        * Policy for `UserVideoUsage`: For system failures, consider not decrementing usage or providing a refund/credit. This might require a separate process or manual intervention initially.
    * Ensure Celery workers are configured for resource limits (CPU, memory) to prevent OOM errors, especially during video processing.

---

### 6. Key Considerations & Best Practices

* **Asynchronous Operations:** All LLM calls and video processing *must* be in Celery tasks. FastAPI endpoints return immediately.
* **Configuration Management:** Use `Pydantic BaseSettings` for app config. Manage secrets (API keys, `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`, other DB connection details if needed, Fernet key) via environment variables or dedicated secret management tools (e.g., HashiCorp Vault, AWS/GCP Secret Manager). `alembic.ini` for migration configs (pointing to Supabase).
* **Error Handling & Logging:**
    * Robust error handling in API endpoints and Celery tasks.
    * **Structured Logging:** Use Python's `logging` module with JSON formatting for easier parsing in centralized logging systems (ELK stack, Grafana Loki, Datadog).
    * **Distributed Tracing:** Implement using OpenTelemetry for end-to-end visibility of requests across FastAPI and Celery workers.
    * **Metrics:** Collect key application and business metrics (e.g., API latencies, error rates, Celery queue lengths, video generation times, LLM costs) using Prometheus/Grafana or similar.
* **Security:**
    * Password hashing (bcrypt).
    * JWT for authentication, with short-lived access tokens and long-lived refresh tokens. Secure HttpOnly cookies for web clients if applicable.
    * OAuth2 token validation and secure storage (encryption for `OAuthAccount` tokens).
    * HTTPS for all communication.
    * Input validation (Pydantic).
    * Stripe webhook signature verification.
    * **Rate Limiting:** On critical/expensive API endpoints (login, signup, video creation, LLM-dependent endpoints) using `slowapi` or similar.
    * Protect LLM API keys: Never client-side. Use secure backend storage and consider API key rotation policies.
    * **Content Moderation:** Implement checks for user-generated prompts (and potentially generated content) using moderation APIs or LLMs to prevent abuse.
    * Regular security audits and dependency scanning.
* **Idempotency:** Design payment webhooks and critical Celery tasks for idempotency.
* **Scalability:**
    * Stateless API design.
    * Scale Celery workers independently based on workload.
    * Utilize Supabase's managed PostgreSQL and its inherent scalability features.
    * Cloud storage for assets (Supabase Storage or other cloud providers).
* **Cost Management:**
    * LLM APIs can be expensive. Monitor usage closely. Provide different quality/model options that map to different costs.
    * Consider Supabase pricing tiers and associated database/storage costs.
    * Optimize image sizes and video encoding parameters.
    * Implement caching where appropriate (e.g., for plan details, potentially for certain deterministic LLM utility calls, though less for core generation).
* **Testing:**
    * **Unit Tests:** For business logic, CRUD operations, services. Mock external dependencies (LLMs, Stripe, Cloud Storage).
    * **Integration Tests:** For API endpoints and Celery task interactions.
    * **End-to-End Tests (Limited):** For critical user flows.
* **SQLModel vs. Separate Schemas:** While SQLModel allows models to serve as both DB and API schemas, if request/response structures become highly complex and diverge significantly from the database model, consider defining separate Pydantic schemas in an `app/api/v1/schemas.py` (or per-endpoint module) for clarity and to avoid cluttering DB models with API-specific concerns. Start with SQLModel's unified approach.
* **Frontend Interaction (Not in scope, but good to remember):**
    * Frontend polls `/videos/{task_id}/status` or uses WebSockets for real-time updates.
    * Handles Stripe redirect and Customer Portal redirect.
    * Displays "Upgrade" prompts, plan details.
    * Manages OAuth2 login flow.

---

### 7. Implementation Phases (Suggested)

1.  **Phase 1: Core Setup & User Authentication** ✅
    * Project structure, FastAPI app, SQLModel base models (`User`, `OAuthAccount`, `Plan`, base models).
    * Supabase project setup and database connection configuration. Alembic migrations setup for Supabase.
    * CRUD operations for `User`, `OAuthAccount`, `Plan` (implemented in `crud_user.py`, `crud_oauth_account.py`, `crud_plan.py`).
    * `/auth/*` endpoints (signup, login, refresh, me, password change, Google OAuth) implemented in `auth.py`.
    * Basic Celery setup with placeholder tasks for testing the configuration.
    * Comprehensive documentation in `backend_documentation.md`.
2.  **Phase 2: Basic Video Task Submission & Status (No LLMs yet)**
    * SQLModel models (`VideoGenerationTask`, `GeneratedVideo`, `UserVideoUsage`, `GeneratedVideoAsset`).
    * `/videos/` (POST to create task), `/videos/{task_id}/status` endpoints.
    * Dummy Celery task that simulates processing steps and updates status/progress.
    * Basic `usage_service` and plan-based limit check (e.g., hardcoded free limit initially).
3.  **Phase 3: LLM Integrations & Asset Generation (Celery Task)**
    * Implement `llm_service_interface` and provider-specific implementations (e.g., OpenAI).
    * Integrate one LLM service at a time into the Celery task: Script, Image prompt + Image gen, Audio gen, SRT gen.
    * Implement `cloud_storage_service` for uploading assets.
    * Populate `GeneratedVideoAsset` and link to `GeneratedVideo`.
4.  **Phase 4: Video Assembly**
    * Implement `video_processing_service` using FFmpeg.
    * Integrate into the Celery task; manage temporary files.
5.  **Phase 5: Subscription & Payments**
    * SQLModel model (`Subscription`). CRUD for Subscription.
    * Stripe integration (`payment_service`).
    * `/payments/*` endpoints (plans, create-checkout, webhook, manage-subscription).
    * Full integration of subscription checks and `UserVideoUsage` updates into video creation logic.
6.  **Phase 6: Refinement & Production Readiness**
    * Thorough testing (unit, integration, few E2E).
    * Comprehensive logging, metrics, and tracing setup.
    * Security audit/review (content moderation, rate limiting, dependency scan).
    * API Documentation (OpenAPI auto-docs refinement).
    * Containerization (Docker, Docker Compose optimization).
    * Deployment strategy (e.g., blue/green or canary on cloud platform).
    * Database backup and restore strategy.
    * User documentation/FAQ.

---

### 8. Future Considerations / Advanced Features

* **Admin Panel:** For user management, subscription oversight, task monitoring/management, platform analytics.
* **Video Templates/Styles:** Predefined themes or styles users can choose.
* **Enhanced Customization:** More granular control over voice, music, image styles, transitions.
* **Background Music:** Option to add royalty-free background music.
* **User Uploads:** Allow users to upload their own images/audio clips to incorporate.
* **Collaboration Features:** Multiple users on a video project.
* **Direct Social Sharing:** Integrations to share videos directly to social media.
* **API for Developers:** Allow third-party developers to use the video generation service.
* **AI-Powered Editing Suggestions:** LLM-based suggestions for improving scripts or visual flow.

---