from pydantic import BaseModel, Field


class PhoneExistsRequest(BaseModel):
    """Existence-only phone lookup for the storefront promo flow."""

    phone: str = Field(..., min_length=10, max_length=20)