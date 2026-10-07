"""Service layer for website contact & bulk order enquiries."""

import json

from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundException
from app.models.contact_inquiry import ContactInquiry
from app.models.notification import (
    Notification,
    NotificationChannel,
    NotificationChannelStatus,
    NotificationSeverity,
    NotificationType,
)
from app.schemas.contact_inquiry import ContactInquiryCreate, ContactInquiryUpdate
from app.socket_manager import emit_event


class ContactInquiryService:
    def __init__(self, db: Session):
        self.db = db

    def create_inquiry(self, payload: ContactInquiryCreate) -> ContactInquiry:
        inquiry = ContactInquiry(
            inquiry_type=payload.inquiry_type,
            name=payload.name.strip(),
            phone=payload.phone,
            email=payload.email,
            subject=payload.subject,
            message=payload.message,
            details_json=json.dumps(payload.details) if payload.details else None,
            is_read=False,
            is_resolved=False,
        )
        self.db.add(inquiry)

        # Also raise an in-app notification so the CRM bell rings instantly
        if payload.inquiry_type == "bulk":
            title = f"New Bulk Order Enquiry: {inquiry.name}"
            summary = payload.subject or "Bulk / catering order request"
        else:
            title = f"New Contact Enquiry: {inquiry.name}"
            summary = payload.subject or "General contact form message"
        contact_bits = " • ".join(b for b in [payload.phone, payload.email] if b)
        notif = Notification(
            title=title,
            message=f"{summary}. {contact_bits}".strip(),
            type=NotificationType.SYSTEM.value,
            severity=NotificationSeverity.INFO.value,
            entity_type="CONTACT_INQUIRY",
            entity_id=None,
            is_read=False,
            channel=NotificationChannel.IN_APP.value,
            channel_status=NotificationChannelStatus.SENT.value,
        )
        self.db.add(notif)
        self.db.commit()
        self.db.refresh(inquiry)

        unread = (
            self.db.query(func.count(Notification.id))
            .filter(Notification.is_read == False)  # noqa: E712
            .scalar()
            or 0
        )
        emit_event("notification_created", {"new_count": 1, "unread_count": unread})
        return inquiry

    def list_inquiries(
        self,
        inquiry_type: str | None = None,
        unresolved_only: bool = False,
    ) -> list[ContactInquiry]:
        query = self.db.query(ContactInquiry)
        if inquiry_type:
            query = query.filter(ContactInquiry.inquiry_type == inquiry_type)
        if unresolved_only:
            query = query.filter(ContactInquiry.is_resolved == False)  # noqa: E712
        return query.order_by(desc(ContactInquiry.created_at)).all()

    def update_inquiry(self, inquiry_id: int, payload: ContactInquiryUpdate) -> ContactInquiry:
        inquiry = self.db.query(ContactInquiry).filter(ContactInquiry.id == inquiry_id).first()
        if inquiry is None:
            raise NotFoundException("ContactInquiry", inquiry_id)
        for key, value in payload.model_dump(exclude_unset=True).items():
            setattr(inquiry, key, value)
        self.db.commit()
        self.db.refresh(inquiry)
        return inquiry

    def delete_inquiry(self, inquiry_id: int) -> None:
        inquiry = self.db.query(ContactInquiry).filter(ContactInquiry.id == inquiry_id).first()
        if inquiry is None:
            raise NotFoundException("ContactInquiry", inquiry_id)
        self.db.delete(inquiry)
        self.db.commit()
