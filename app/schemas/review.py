"""Review schemas for storefront customer testimonials."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ReviewCreate(BaseModel):
    customer_name: str = Field(..., min_length=1, max_length=255)
    location: str | None = Field(None, max_length=255)
    rating: int = Field(5, ge=1, le=5)
    review_text: str = Field(..., min_length=1)
    verified_order: bool = True
    dish_loved: str | None = Field(None, max_length=255)
    is_active: bool = True
    sort_order: int = 0


class ReviewUpdate(BaseModel):
    customer_name: str | None = Field(None, min_length=1, max_length=255)
    location: str | None = Field(None, max_length=255)
    rating: int | None = Field(None, ge=1, le=5)
    review_text: str | None = Field(None, min_length=1)
    verified_order: bool | None = None
    dish_loved: str | None = Field(None, max_length=255)
    is_active: bool | None = None
    sort_order: int | None = None


class ReviewResponse(BaseModel):
    id: int
    customer_name: str
    location: str | None = None
    rating: int
    review_text: str
    verified_order: bool
    dish_loved: str | None = None
    is_active: bool
    sort_order: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
