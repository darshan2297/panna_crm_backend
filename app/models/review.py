"""Review model for customer testimonials displayed on the storefront."""

from sqlalchemy import Boolean, Column, Integer, String, Text

from app.core.database import Base
from app.models.base import TimestampMixin


class Review(Base, TimestampMixin):
    __tablename__ = "reviews"

    customer_name = Column(String(255), nullable=False)
    location = Column(String(255), nullable=True)
    rating = Column(Integer, nullable=False, default=5)
    review_text = Column(Text, nullable=False)
    verified_order = Column(Boolean, default=True, nullable=False)
    dish_loved = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    sort_order = Column(Integer, default=0, nullable=False)

    def __repr__(self) -> str:
        return f"<Review {self.customer_name} ({self.rating}★)>"
