from typing import List, Optional

from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.crud.crud_base import CRUDBase
from app.db.models.payment_models import Plan
from app.api.v1.schemas import PlanCreateSchema, PlanUpdateSchema

class CRUDPlan(CRUDBase[Plan, PlanCreateSchema, PlanUpdateSchema]):
    async def get_by_name(self, db: AsyncSession, *, name: str) -> Optional[Plan]:
        statement = select(self.model).where(self.model.name == name)
        result = await db.execute(statement)
        return result.scalar_one_or_none()

    async def get_active_plans(self, db: AsyncSession, *, skip: int = 0, limit: int = 100) -> List[Plan]:
        statement = select(self.model).where(self.model.is_active == True).order_by(self.model.display_order).offset(skip).limit(limit)
        result = await db.execute(statement)
        return result.scalars().all()

plan_crud = CRUDPlan(Plan) 