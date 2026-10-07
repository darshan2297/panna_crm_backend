"""FAQ schemas for storefront frequently asked questions."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class FAQCreate(BaseModel):
    question: str = Field(..., min_length=1)
    answer: str = Field(..., min_length=1)
    category: str = Field("ordering", pattern="^(ordering|food|delivery|bulk)$")
    is_active: bool = True
    sort_order: int = 0


class FAQUpdate(BaseModel):
    question: str | None = Field(None, min_length=1)
    answer: str | None = Field(None, min_length=1)
    category: str | None = Field(None, pattern="^(ordering|food|delivery|bulk)$")
    is_active: bool | None = None
    sort_order: int | None = None


class FAQResponse(BaseModel):
    id: int
    question: str
    answer: str
    category: str
    is_active: bool
    sort_order: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
