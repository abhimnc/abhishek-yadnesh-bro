import uuid
from datetime import datetime, timezone
from typing import Optional
import calendar
from sqlalchemy import update
from sqlalchemy.future import select
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

from ..models import UserVideoUsage
from .crud_base import CRUDBase

# --- Schemas for CRUD Operations ---

class UserVideoUsageCreateSchema(SQLModel):
    user_id: uuid.UUID
    period_identifier: str
    period_start_date: datetime
    period_end_date: datetime
    videos_created_this_period: int = 0

class UserVideoUsageUpdateSchema(SQLModel):
    videos_created_this_period: Optional[int] = None

# --- CRUD Class ---

class CRUDUserVideoUsage(CRUDBase[UserVideoUsage, UserVideoUsageCreateSchema, UserVideoUsageUpdateSchema]):

    async def get_current_period_record(self, db: AsyncSession, *, user_id: uuid.UUID) -> Optional[UserVideoUsage]:
        """Fetches the usage record for the current month for a specific user."""
        now = datetime.now(timezone.utc)
        period_identifier = now.strftime("%Y-%m")
        stmt = select(self.model).where(
            self.model.user_id == user_id,
            self.model.period_identifier == period_identifier
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    def _get_current_month_period(self) -> tuple[str, datetime, datetime]:
        """Calculates the identifier, start, and end dates for the current month in UTC."""
        now = datetime.now(timezone.utc)
        period_identifier = now.strftime("%Y-%m")
        _, last_day = calendar.monthrange(now.year, now.month)
        start_date = datetime(now.year, now.month, 1, tzinfo=timezone.utc)
        # End date is the very start of the next month
        end_date = datetime(now.year, now.month, last_day, 23, 59, 59, 999999, tzinfo=timezone.utc)
        return period_identifier, start_date, end_date

    async def get_or_create_current_period(self, db: AsyncSession, *, user_id: uuid.UUID) -> UserVideoUsage:
        """Gets the usage record for the current month, creating it if it doesn't exist."""
        existing_record = await self.get_current_period_record(db, user_id=user_id)
        if existing_record:
            return existing_record

        # Create new record if it doesn't exist
        period_identifier, start_date, end_date = self._get_current_month_period()
        create_data = UserVideoUsageCreateSchema(
            user_id=user_id,
            period_identifier=period_identifier,
            period_start_date=start_date,
            period_end_date=end_date
        )
        return await self.create(db=db, obj_in=create_data)

    async def increment_usage(self, db: AsyncSession, *, usage_record: UserVideoUsage) -> UserVideoUsage:
        """Increments the video usage count for the given record atomically."""
        # Use SQLAlchemy Core update for atomic increment
        stmt = (
            update(self.model)
            .where(self.model.id == usage_record.id)
            .values(videos_created_this_period=self.model.videos_created_this_period + 1)
            .execution_options(synchronize_session="fetch")
        )
        await db.execute(stmt)
        # No commit here, handled by the caller (service layer)
        await db.refresh(usage_record) # Refresh the object to get the updated value
        return usage_record


# Instantiate CRUD object
user_usage_crud = CRUDUserVideoUsage(UserVideoUsage) 