"""Contact inquiry schemas for website contact & bulk order enquiries."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ContactInquiryCreate(BaseModel):
    inquiry_type: str = Field("contact", pattern="^(contact|bulk)$")
    name: str = Field(..., min_length=1, max_length=255)
    phone: str | None = Field(None, max_length=50)
    email: str | None = Field(None, max_length=255)
    subject: str | None = Field(None, max_length=255)
    message: str | None = None
    details: dict[str, Any] | None = None  # bulk-order extras


class ContactInquiryUpdate(BaseModel):
    is_read: bool | None = None
    is_resolved: bool | None = None


class ContactInquiryResponse(BaseModel):
    id: int
    inquiry_type: str
    name: str
    phone: str | None = None
    email: str | None = None
    subject: str | None = None
    message: str | None = None
    details_json: str | None = None
    is_read: bool
    is_resolved: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
