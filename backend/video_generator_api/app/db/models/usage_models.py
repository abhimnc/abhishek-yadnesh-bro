import uuid
from datetime import datetime

from sqlalchemy import UniqueConstraint
from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlmodel import Field, Relationship, SQLModel

from .base_model import SQLModelBase

# User Video Usage Model
class UserVideoUsage(SQLModelBase, table=True):
    __tablename__ = "user_video_usage" # Explicit table name

    user_id: uuid.UUID = Field(
        foreign_key="user_account.id", index=True, nullable=False
    )
    period_identifier: str = Field(max_length=7, nullable=False) # Format: YYYY-MM
    videos_created_this_period: int = Field(default=0, nullable=False)
    period_start_date: datetime = Field(
        nullable=False, sa_type=TIMESTAMP(timezone=True)
    )
    period_end_date: datetime = Field(
        nullable=False, sa_type=TIMESTAMP(timezone=True)
    )

    # Define relationship back to User (Optional, add back_populates in User model if needed)
    # user: "User" = Relationship(back_populates="usage_records")

    # Define unique constraint for user and period
    __table_args__ = (
        UniqueConstraint("user_id", "period_identifier", name="uq_user_period"),
    ) 