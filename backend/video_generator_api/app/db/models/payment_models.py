import uuid
from decimal import Decimal
from typing import Optional, Dict, Any

from sqlalchemy import Column, String, Integer, Numeric, Boolean, JSON
from sqlmodel import Field

from app.db.models.base_model import SQLModelBase

class PlanBase(SQLModelBase):
    name: str = Field(max_length=100, nullable=False, unique=True) # Plan name should be unique
    stripe_price_id: str = Field(max_length=255, unique=True, index=True, nullable=False)
    video_limit_per_period: int = Field(nullable=False)
    max_video_duration_seconds: Optional[int] = Field(default=None)
    features: Optional[Dict[str, Any]] = Field(default_factory=dict, sa_column=Column(JSON))
    price_monthly: Optional[Decimal] = Field(sa_column=Column(Numeric(10, 2)))
    price_yearly: Optional[Decimal] = Field(sa_column=Column(Numeric(10, 2)))
    currency: str = Field(max_length=3, default="USD")
    description: Optional[str] = Field(default=None)
    is_active: bool = Field(default=True)
    display_order: int = Field(default=0)

class Plan(PlanBase, table=True):
    pass
    # Relationships to Subscriptions can be added here if needed,
    # but often it's queried from Subscription to Plan. 