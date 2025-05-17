import uuid
from typing import List, Optional, Type

from sqlalchemy import update
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

from ..models import (
    GeneratedVideo,
    GeneratedVideoAsset,
    VideoGenerationTask,
    VideoGenerationTaskStatus,
)
from .crud_base import CRUDBase

# --- Schemas for CRUD Operations (Simple cases, define inline or move to schemas.py if complex) ---

# Although SQLModel can often be used directly, defining explicit schemas for creation
# can be clearer, especially if input differs slightly from the model.

class VideoGenerationTaskCreateSchema(SQLModel):
    user_id: uuid.UUID
    prompt_text: str
    # Status defaults to PENDING in model

class VideoGenerationTaskUpdateSchema(SQLModel):
    status: Optional[VideoGenerationTaskStatus] = None
    progress_percentage: Optional[int] = None
    error_message: Optional[str] = None
    celery_task_id: Optional[str] = None

class GeneratedVideoCreateSchema(SQLModel):
    task_id: uuid.UUID
    user_id: uuid.UUID
    title: Optional[str] = "Untitled Video"
    final_video_url: Optional[str] = None
    duration_seconds: Optional[int] = None
    visibility: Optional[str] = "private"

class GeneratedVideoUpdateSchema(SQLModel):
    title: Optional[str] = None
    final_video_url: Optional[str] = None
    duration_seconds: Optional[int] = None
    visibility: Optional[str] = None

class GeneratedVideoAssetCreateSchema(SQLModel):
    video_id: uuid.UUID
    asset_type: str
    order_index: int
    asset_url: str

class GeneratedVideoAssetUpdateSchema(SQLModel):
    asset_type: Optional[str] = None
    order_index: Optional[int] = None
    asset_url: Optional[str] = None


# --- CRUD Classes ---

class CRUDVideoGenerationTask(CRUDBase[VideoGenerationTask, VideoGenerationTaskCreateSchema, VideoGenerationTaskUpdateSchema]):

    async def update_status_and_progress(
        self,
        db: AsyncSession,
        *,
        db_obj: VideoGenerationTask,
        status: Optional[VideoGenerationTaskStatus] = None,
        progress: Optional[int] = None,
        error: Optional[str] = None,
    ) -> VideoGenerationTask:
        """Updates status, progress, and error message atomically."""
        update_data = {}
        if status is not None:
            update_data["status"] = status
        if progress is not None:
            update_data["progress_percentage"] = progress
        # Allow explicitly setting error to None to clear it
        if error is not None or "error_message" in update_data: # Check if error is being set or potentially cleared
             update_data["error_message"] = error

        if not update_data:
            return db_obj # No changes needed

        # Use SQLAlchemy core update for potential efficiency / atomicity
        stmt = (
            update(self.model)
            .where(self.model.id == db_obj.id)
            .values(**update_data)
            .execution_options(synchronize_session="fetch") # Update the session object
        )
        await db.execute(stmt)
        # No need to commit here, handled by the caller (e.g., endpoint or service)
        await db.refresh(db_obj)
        return db_obj

    async def update_celery_task_id(
        self, db: AsyncSession, *, db_obj: VideoGenerationTask, celery_task_id: str
    ) -> VideoGenerationTask:
        """Updates the Celery task ID for a video generation task."""
        # Merge the object into the current session if it's from another session
        if db_obj not in db:
            db_obj = await db.merge(db_obj)
        
        db_obj.celery_task_id = celery_task_id
        db.add(db_obj) # db.add() is still appropriate after merge for dirty marking
        # No commit here, will be committed by the calling scope (videos.py endpoint)
        # Await db.flush() to send changes to DB if needed before refresh
        await db.flush([db_obj])
        await db.refresh(db_obj)
        return db_obj

    async def get_by_user(
        self, db: AsyncSession, *, user_id: uuid.UUID, skip: int = 0, limit: int = 100
    ) -> List[VideoGenerationTask]:
        """Retrieve video generation tasks for a specific user."""
        stmt = (
            select(self.model)
            .where(self.model.user_id == user_id)
            .offset(skip)
            .limit(limit)
            .order_by(self.model.created_at.desc()) # Example ordering
        )
        result = await db.execute(stmt)
        return result.scalars().all()

    async def get_with_video(self, db: AsyncSession, *, id: uuid.UUID) -> Optional[VideoGenerationTask]:
        """Get a task and eagerly load its associated GeneratedVideo."""
        stmt = (
            select(self.model)
            .where(self.model.id == id)
            .options(selectinload(self.model.generated_video))
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()


class CRUDGeneratedVideo(CRUDBase[GeneratedVideo, GeneratedVideoCreateSchema, GeneratedVideoUpdateSchema]):

    async def get_by_user(
        self, db: AsyncSession, *, user_id: uuid.UUID, skip: int = 0, limit: int = 100
    ) -> List[GeneratedVideo]:
        """Retrieve generated videos for a specific user."""
        stmt = (
            select(self.model)
            .where(self.model.user_id == user_id)
            .offset(skip)
            .limit(limit)
            .order_by(self.model.created_at.desc())
        )
        result = await db.execute(stmt)
        return result.scalars().all()

    async def get_by_task_id(self, db: AsyncSession, *, task_id: uuid.UUID) -> Optional[GeneratedVideo]:
        """Retrieve a generated video by its associated task ID."""
        stmt = select(self.model).where(self.model.task_id == task_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()


class CRUDGeneratedVideoAsset(CRUDBase[GeneratedVideoAsset, GeneratedVideoAssetCreateSchema, GeneratedVideoAssetUpdateSchema]):
    pass


# Instantiate CRUD objects
video_task_crud = CRUDVideoGenerationTask(VideoGenerationTask)
generated_video_crud = CRUDGeneratedVideo(GeneratedVideo)
video_asset_crud = CRUDGeneratedVideoAsset(GeneratedVideoAsset) 