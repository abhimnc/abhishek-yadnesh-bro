import logging
import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel.ext.asyncio.session import AsyncSession

from app.api.v1 import schemas
from app.api.v1.deps import (
    get_async_session,
    get_current_active_user,
    get_usage_service,
)
from app.db import models
from app.db.crud import video_task_crud, generated_video_crud
from app.services.usage_service import UsageService
from app.tasks.video_generation_tasks import simulate_video_processing # Import the Celery task
from app.db.session import AsyncSessionLocal # Import AsyncSessionLocal

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Videos"])

@router.post(
    "/",
    response_model=schemas.VideoTaskCreateResponseSchema,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Submit a new video generation task",
    description="Submits a prompt to generate a video. Checks usage limits before accepting."
)
async def create_video_task(
    *,
    db: AsyncSession = Depends(get_async_session),
    current_user: models.User = Depends(get_current_active_user),
    usage_service: UsageService = Depends(get_usage_service),
    video_in: schemas.VideoCreateRequestSchema,
) -> schemas.VideoTaskCreateResponseSchema:
    """
    Creates a new video generation task after checking usage limits.
    - **prompt_text**: The main text prompt for the video.
    """
    logger.info(f"Received video creation request from user {current_user.id}")

    try:
        # 1. Check usage limit and increment (raises HTTPException if limit reached)
        await usage_service.check_and_increment_usage(user=current_user)
        logger.info(f"Usage check passed for user {current_user.id}")

        # 2. Create VideoGenerationTask record in DB
        task_data = {
            "prompt_text": video_in.prompt_text,
            "user_id": current_user.id
        }
        # Use the specific create schema if defined, or dict if simple
        new_task = await video_task_crud.create(db=db, obj_in=task_data)
        # Need to commit the usage increment and the new task together
        await db.commit()
        await db.refresh(new_task)
        logger.info(f"Created VideoGenerationTask {new_task.id} for user {current_user.id}")

        # 3. Enqueue Celery task
        try:
            celery_task = simulate_video_processing.delay(task_db_id_str=str(new_task.id))
            logger.info(f"Enqueued Celery task {celery_task.id} for DB task {new_task.id}")

            # 4. (Recommended) Update DB record with Celery task ID
            # Use a separate session or handle potential commit issues if task fails immediately
            async with AsyncSessionLocal() as update_db:
                 await video_task_crud.update_celery_task_id(update_db, db_obj=new_task, celery_task_id=celery_task.id)
                 await update_db.commit()
            logger.info(f"Updated DB task {new_task.id} with Celery task ID {celery_task.id}")

        except Exception as e:
            # Handle Celery enqueue error - potentially rollback the DB changes or mark task as failed
            logger.error(f"Failed to enqueue Celery task for DB task {new_task.id}: {e}", exc_info=True)
            # Rollback the initial commit if possible, or mark task as failed
            async with AsyncSessionLocal() as rollback_db:
                task_to_fail = await video_task_crud.get(rollback_db, id=new_task.id)
                if task_to_fail:
                    await video_task_crud.update_status_and_progress(rollback_db, db_obj=task_to_fail, status=models.VideoGenerationTaskStatus.FAILED, error="Failed to queue processing task")
                    await rollback_db.commit()
            # Re-raise or return an appropriate error response
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to schedule video generation. Please try again later."
            )

        return schemas.VideoTaskCreateResponseSchema(
            task_id=new_task.id,
            status=new_task.status, # Should be PENDING initially
            message="Video generation task accepted and queued."
        )

    except HTTPException as http_exc:
        # Catch usage limit exception specifically
        await db.rollback() # Rollback if usage check failed
        raise http_exc
    except Exception as e:
        await db.rollback()
        logger.error(f"Error creating video task for user {current_user.id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while creating the video task."
        )


@router.get(
    "/{task_id}/status",
    response_model=schemas.VideoTaskStatusResponseSchema,
    summary="Get the status of a video generation task",
    description="Retrieves the current status, progress, and results (if completed) of a specific task."
)
async def get_video_task_status(
    task_id: uuid.UUID,
    db: AsyncSession = Depends(get_async_session),
    current_user: models.User = Depends(get_current_active_user),
) -> schemas.VideoTaskStatusResponseSchema:
    """
    Retrieves the status of a video generation task by its ID.
    Ensures the user owns the task.
    """
    logger.debug(f"User {current_user.id} requesting status for task {task_id}")
    # Fetch task and potentially the linked video efficiently
    # Using get_with_video from CRUD might be better if available and performant
    task = await video_task_crud.get_with_video(db=db, id=task_id) # Use eager loading if defined

    if not task:
        logger.warning(f"Task {task_id} not found for user {current_user.id}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    # Check ownership (allow superusers access)
    if task.user_id != current_user.id and not current_user.is_superuser:
        logger.warning(f"User {current_user.id} forbidden from accessing task {task_id} owned by {task.user_id}")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to view this task status")

    video_id_res: Optional[uuid.UUID] = None
    video_url_res: Optional[str] = None

    if task.status == models.VideoGenerationTaskStatus.COMPLETED:
        # Access the eagerly loaded video if get_with_video was used
        video = task.generated_video
        # If not eagerly loaded, query separately (less efficient)
        # if not video:
        #     video = await generated_video_crud.get_by_task_id(db=db, task_id=task.id)

        if video:
            video_id_res = video.id
            video_url_res = video.final_video_url
        else:
             logger.error(f"Task {task_id} is COMPLETED but associated GeneratedVideo not found.")
             # Decide how to handle this inconsistency - maybe mark task as error? For now, return completed without video URL.
             pass # Or potentially update task status back to an error state

    return schemas.VideoTaskStatusResponseSchema(
        task_id=task.id,
        status=task.status,
        progress_percentage=task.progress_percentage,
        error_message=task.error_message,
        video_id=video_id_res,
        video_url=video_url_res
    )

# Placeholder for GET /videos/ (List user's videos) - Phase 2 scope was just creation/status
# @router.get("/", response_model=List[schemas.GeneratedVideoReadSchema])
# async def list_user_videos(...):
#    pass 