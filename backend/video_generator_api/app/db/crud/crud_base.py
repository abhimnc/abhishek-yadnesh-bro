from typing import Any, Dict, Generic, List, Optional, Type, TypeVar, Union, cast, Tuple
import uuid
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel
from sqlmodel import SQLModel, select, func
from sqlalchemy.ext.asyncio import AsyncSession

ModelType = TypeVar("ModelType", bound=SQLModel)
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)

class CRUDBase(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    def __init__(self, model: Type[ModelType]):
        """
        CRUD object with default methods to Create, Read, Update, Delete (CRUD).

        **Parameters**

        * `model`: A SQLModel class
        """
        self.model = model

    async def get(self, db: AsyncSession, id: uuid.UUID) -> Optional[ModelType]:
        statement = select(self.model).where(self.model.id == id)
        result = await db.execute(statement)
        return result.scalar_one_or_none()

    async def get_multi(
        self, db: AsyncSession, *, skip: int = 0, limit: int = 100
    ) -> List[ModelType]:
        statement = select(self.model).offset(skip).limit(limit)
        result = await db.execute(statement)
        return result.scalars().all()
    
    async def get_multi_with_total_count(
        self, db: AsyncSession, *, skip: int = 0, limit: int = 100
    ) -> Tuple[List[ModelType], int]:
        statement = select(self.model).offset(skip).limit(limit)
        count_statement = select(func.count()).select_from(self.model)
        
        results = await db.execute(statement)
        total_count_result = await db.execute(count_statement)
        
        return results.scalars().all(), total_count_result.scalar_one()

    async def create(self, db: AsyncSession, *, obj_in: CreateSchemaType) -> ModelType:
        obj_in_data = jsonable_encoder(obj_in) # Converts Pydantic model to dict
        db_obj = self.model(**obj_in_data)  # type: ignore
        db.add(db_obj)
        await db.flush() # Use flush to get the ID before commit, if needed by other operations
        await db.refresh(db_obj)
        return db_obj

    async def update(
        self, db: AsyncSession, *, db_obj: ModelType, obj_in: Union[UpdateSchemaType, Dict[str, Any]]
    ) -> ModelType:
        obj_data = jsonable_encoder(db_obj)
        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.model_dump(exclude_unset=True) # Pydantic V2
        
        for field in obj_data:
            if field in update_data:
                setattr(db_obj, field, update_data[field])
        
        db.add(db_obj)
        await db.flush()
        await db.refresh(db_obj)
        return db_obj

    async def remove(self, db: AsyncSession, *, id: uuid.UUID) -> Optional[ModelType]:
        obj = await self.get(db, id=id)
        if obj:
            await db.delete(obj)
            await db.flush()
        return obj # Returns the deleted object or None if not found 