import uuid
from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel
from sqlalchemy import text
from sqlalchemy.dialects.postgresql import TIMESTAMP

class SQLModelBase(SQLModel):
    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        primary_key=True,
        index=True,
        nullable=False,
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        nullable=False,
        sa_type=TIMESTAMP(timezone=True),
        sa_column_kwargs={
            "server_default": text("CURRENT_TIMESTAMP")
        }
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        nullable=False,
        sa_type=TIMESTAMP(timezone=True),
        sa_column_kwargs={
            "server_default": text("CURRENT_TIMESTAMP"),
            "onupdate": text("CURRENT_TIMESTAMP")
        }
    ) 