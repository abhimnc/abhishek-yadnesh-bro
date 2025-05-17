import logging

from fastapi import HTTPException, status
from sqlmodel.ext.asyncio.session import AsyncSession

from app.db.models import User, Plan # Plan might be needed later
from app.db.crud import user_usage_crud # Removed plan_crud for now

logger = logging.getLogger(__name__)

# --- Constants --- #
# In Phase 2, we use a hardcoded limit. This will be replaced by plan-based limits in Phase 5.
DEFAULT_FREE_PLAN_VIDEO_LIMIT = 5

class UsageService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def check_and_increment_usage(self, user: User) -> None:
        """Checks if the user can create another video based on limits and increments usage."""
        logger.info(f"Checking usage for user {user.id}")

        # 1. Get current usage record (or create if first time this month)
        usage_record = await user_usage_crud.get_or_create_current_period(self.db, user_id=user.id)
        # Commit immediately after get_or_create in case a new record was made
        # Or rely on the final commit after increment
        await self.db.flush() # Ensure the record exists before checking
        await self.db.refresh(usage_record) # Get the latest state

        # 2. Check against the limit
        # TODO: Fetch user's actual plan and its limit in Phase 5.
        limit = DEFAULT_FREE_PLAN_VIDEO_LIMIT
        logger.debug(f"User {user.id} current usage: {usage_record.videos_created_this_period}, Limit: {limit}")

        if usage_record.videos_created_this_period >= limit:
            logger.warning(f"User {user.id} has reached the usage limit of {limit}.")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Usage limit of {limit} videos per month reached. Upgrade your plan for more."
            )

        # 3. Increment usage if limit is not reached
        logger.info(f"Incrementing usage for user {user.id}. Previous count: {usage_record.videos_created_this_period}")
        await user_usage_crud.increment_usage(self.db, usage_record=usage_record)
        # Note: The commit will happen in the endpoint after this service call succeeds.
        # No db.commit() here to allow rollback if subsequent steps in the endpoint fail.
        logger.info(f"Usage increment successful for user {user.id}. New count (pre-commit): {usage_record.videos_created_this_period}") 