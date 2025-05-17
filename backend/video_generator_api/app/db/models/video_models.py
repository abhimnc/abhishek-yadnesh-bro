import uuid
from enum import Enum as PyEnum
from typing import List, Optional

from sqlalchemy import CheckConstraint, Enum as SaEnum, ForeignKey, Column
from sqlalchemy.dialects.postgresql import ENUM as PgEnum
from sqlalchemy.orm import RelationshipProperty
from sqlmodel import Field, Relationship, SQLModel

from .base_model import SQLModelBase

# Define Enum for Status
class VideoGenerationTaskStatus(str, PyEnum):
    PENDING = "pending"
    PROCESSING = "processing" # Covers all intermediate steps like script, image, audio, assembly
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled" # Optional: If user cancellation is implemented later

# Create the PostgreSQL Enum type
# This reference is primarily for Alembic env.py; Column definition below handles type
video_status_enum = PgEnum(VideoGenerationTaskStatus, name="videogenerationtaskstatus")


# Video Generation Task Model
class VideoGenerationTask(SQLModelBase, table=True):
    __tablename__ = "video_generation_task" # Explicit table name

    user_id: uuid.UUID = Field(
        foreign_key="user_account.id", index=True, nullable=False
    )
    prompt_text: str = Field(nullable=False) # Assuming TEXT based on plan, SQLModel handles it

    # Revised status field definition using SQLModel best practices
    status: VideoGenerationTaskStatus = Field(
        default=VideoGenerationTaskStatus.PENDING,
        index=True,
        nullable=False,
        # sa_column is removed. SQLModel should infer SaEnum from the type hint.
        # If inference were to fail, the alternative is sa_type=SaEnum(VideoGenerationTaskStatus)
    )

    # progress_percentage field without sa_column_kwargs
    progress_percentage: int = Field(
        default=0,
        nullable=False,
    )
    error_message: Optional[str] = Field(default=None) # Assuming TEXT
    celery_task_id: Optional[str] = Field(default=None, max_length=255, index=True)

    # Define the relationship to GeneratedVideo (one-to-one)
    # The property name 'generated_video' matches the back_populates in GeneratedVideo
    generated_video: Optional["GeneratedVideo"] = Relationship(
        back_populates="task", sa_relationship_kwargs={"uselist": False}
    )

    # Define table-level constraints using __table_args__
    __table_args__ = (
        CheckConstraint(
            "progress_percentage >= 0 AND progress_percentage <= 100",
            name="ck_video_task_progress_range" # Naming constraint is good practice
        ),
        # Add other table-level constraints here if needed
    )


# Generated Video Model
class GeneratedVideo(SQLModelBase, table=True):
    __tablename__ = "generated_video" # Explicit table name

    task_id: uuid.UUID = Field(
        foreign_key="video_generation_task.id", unique=True, index=True, nullable=False
    )
    user_id: uuid.UUID = Field(
        foreign_key="user_account.id", index=True, nullable=False # Denormalized
    )
    title: str = Field(default="Untitled Video", max_length=255, nullable=False)
    final_video_url: Optional[str] = Field(default=None, max_length=512)
    duration_seconds: Optional[int] = Field(default=None)
    visibility: str = Field(default="private", max_length=20, nullable=False) # e.g., private, unlisted, public

    # Define relationship back to VideoGenerationTask (many-to-one, but functionally one-to-one via unique=True on task_id)
    task: VideoGenerationTask = Relationship(back_populates="generated_video")
    # Define relationship to GeneratedVideoAsset (one-to-many)
    assets: List["GeneratedVideoAsset"] = Relationship(back_populates="video")


# Generated Video Asset Model
class GeneratedVideoAsset(SQLModelBase, table=True):
    __tablename__ = "generated_video_asset" # Explicit table name

    video_id: uuid.UUID = Field(
        foreign_key="generated_video.id", index=True, nullable=False
    )
    asset_type: str = Field(max_length=50, nullable=False) # e.g., 'placeholder_image', 'generated_image', 'audio'
    order_index: int = Field(nullable=False) # Order within the video
    asset_url: str = Field(max_length=512, nullable=False) # URL in cloud storage

    # Define relationship back to GeneratedVideo (many-to-one)
    video: GeneratedVideo = Relationship(back_populates="assets") 