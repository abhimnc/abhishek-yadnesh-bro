from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "video_generator_api_worker",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "app.tasks.placeholder_tasks", 
        "app.tasks.video_generation_tasks",
        # Add other task modules here as they are created
        # e.g., "app.tasks.video_generation_tasks"
    ]
)

# Optional Celery configuration
celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    # task_track_started=True, # Useful for more detailed task state tracking
    # worker_prefetch_multiplier=1, # Can be important for long-running tasks to prevent one worker hoarding jobs
    # task_acks_late=True, # If you want tasks to be acknowledged after completion/failure
)

# To run the Celery worker (from the `backend/video_generator_api` directory):
# celery -A app.core.celery_app worker -l info
# Or for development with auto-reload (though be careful with stateful tasks):
# watchmedo auto-restart --directory=./app --pattern=*.py --recursive -- celery -A app.core.celery_app worker -l info 