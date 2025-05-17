import time
import random
import logging
import uuid
from typing import Optional

from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.celery_app import celery_app
from app.db.session import AsyncSessionLocal
from app.db.crud import video_task_crud, generated_video_crud
from app.db.models import VideoGenerationTask, VideoGenerationTaskStatus, GeneratedVideo

logger = logging.getLogger(__name__)


@celery_app.task(acks_late=True, bind=True)
def simulate_video_processing(self, task_db_id_str: str):
    """Simulates the video generation pipeline with status/progress updates."""
    task_db_id: uuid.UUID
    try:
        task_db_id = uuid.UUID(task_db_id_str)
    except ValueError:
        logger.error(f"Invalid UUID received for task: {task_db_id_str}")
        return # Cannot process

    logger.info(f"Starting simulation for task ID: {task_db_id}")

    async def update_task_status(session: AsyncSession, status: VideoGenerationTaskStatus, progress: Optional[int] = None, error_msg: Optional[str] = None):
        task = await video_task_crud.get(session, id=task_db_id)
        if task:
            await video_task_crud.update_status_and_progress(
                session, db_obj=task, status=status, progress=progress, error=error_msg
            )
            await session.commit()
            logger.info(f"Task {task_db_id} status updated to {status}, progress: {progress}%")
        else:
            logger.error(f"Task {task_db_id} not found during status update.")

    async def run_simulation():
        # 1. Set to Processing
        async with AsyncSessionLocal() as db:
            await update_task_status(db, status=VideoGenerationTaskStatus.PROCESSING, progress=10)

        # 2. Simulate steps
        total_steps = 5
        for i in range(total_steps):
            sleep_time = random.uniform(1, 3) # Simulate work
            time.sleep(sleep_time)
            current_progress = 10 + int((i + 1) / total_steps * 80) # Progress from 10% to 90%
            async with AsyncSessionLocal() as db:
                await update_task_status(db, status=VideoGenerationTaskStatus.PROCESSING, progress=current_progress)
            logger.info(f"Task {task_db_id}: Simulation step {i+1}/{total_steps} completed.")

        # 3. Simulate outcome (80% success)
        success = random.choices([True, False], weights=[80, 20], k=1)[0]

        # 4. Final update
        async with AsyncSessionLocal() as db:
            final_task = await video_task_crud.get(db, id=task_db_id)
            if not final_task:
                logger.error(f"Task {task_db_id} not found for final update.")
                return

            if success:
                logger.info(f"Task {task_db_id} simulation successful. Creating GeneratedVideo entry.")
                # Create GeneratedVideo record
                video_data = {
                    "task_id": final_task.id,
                    "user_id": final_task.user_id,
                    "final_video_url": f"http://example.com/placeholder/{final_task.id}.mp4",
                    "title": f"Generated Video for Task {final_task.id}"
                    # Add other fields as needed, e.g., duration
                }
                await generated_video_crud.create(db=db, obj_in=video_data)
                # Update task status to completed
                await video_task_crud.update_status_and_progress(
                    db, db_obj=final_task, status=VideoGenerationTaskStatus.COMPLETED, progress=100
                )
                await db.commit()
                logger.info(f"Task {task_db_id} successfully completed.")
            else:
                error_message = "Simulated failure during video processing."
                logger.warning(f"Task {task_db_id} simulation failed: {error_message}")
                await video_task_crud.update_status_and_progress(
                    db, db_obj=final_task, status=VideoGenerationTaskStatus.FAILED, progress=final_task.progress_percentage, error=error_message
                )
                await db.commit()
                logger.info(f"Task {task_db_id} marked as failed.")

    # Run the async simulation logic
    import asyncio
    try:
        asyncio.run(run_simulation())
    except Exception as e:
        logger.error(f"Error during task simulation for {task_db_id}: {e}", exc_info=True)
        # Attempt to mark task as failed if exception occurs mid-process
        async def mark_failed_on_error():
             async with AsyncSessionLocal() as db:
                task = await video_task_crud.get(db, id=task_db_id)
                if task and task.status == VideoGenerationTaskStatus.PROCESSING:
                    await video_task_crud.update_status_and_progress(
                        db, db_obj=task, status=VideoGenerationTaskStatus.FAILED, error=f"Task failed due to exception: {e}"
                    )
                    await db.commit()
        try:
            asyncio.run(mark_failed_on_error())
        except Exception as final_e:
             logger.error(f"Failed to mark task {task_db_id} as failed after exception: {final_e}") 