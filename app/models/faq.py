"""FAQ model for frequently asked questions on the storefront."""

from enum import Enum as PyEnum

from sqlalchemy import Boolean, Column, Integer, String, Text

from app.core.database import Base
from app.models.base import TimestampMixin


class FAQCategory(str, PyEnum):
    ORDERING = "ordering"
    FOOD = "food"
    DELIVERY = "delivery"
    BULK = "bulk"


class FAQ(Base, TimestampMixin):
    __tablename__ = "faqs"

    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    category = Column(String(50), default=FAQCategory.ORDERING.value, nullable=False, index=True)
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    sort_order = Column(Integer, default=0, nullable=False)

    def __repr__(self) -> str:
        return f"<FAQ {self.question[:50]}...>"
