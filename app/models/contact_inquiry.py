"""ContactInquiry model for website contact & bulk order enquiries."""

from sqlalchemy import Boolean, Column, Integer, String, Text

from app.core.database import Base
from app.models.base import TimestampMixin


class ContactInquiry(Base, TimestampMixin):
    __tablename__ = "contact_inquiries"

    id = Column(Integer, primary_key=True, index=True)
    inquiry_type = Column(String(20), default="contact", nullable=False, index=True)  # contact | bulk
    name = Column(String(255), nullable=False)
    phone = Column(String(50), nullable=True)
    email = Column(String(255), nullable=True)
    subject = Column(String(255), nullable=True)
    message = Column(Text, nullable=True)
    details_json = Column(Text, nullable=True)  # bulk-order extras: event date, guests, etc.
    is_read = Column(Boolean, default=False, nullable=False, index=True)
    is_resolved = Column(Boolean, default=False, nullable=False, index=True)

    def __repr__(self) -> str:
        return f"<ContactInquiry {self.inquiry_type} from {self.name}>"
