"""Contact inquiry router for admin management of website enquiries."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.dependencies.auth import require_permission
from app.dependencies.database import get_db
from app.models.user import User
from app.schemas.common import APIResponse
from app.schemas.contact_inquiry import ContactInquiryResponse, ContactInquiryUpdate
from app.services.contact_inquiry_service import ContactInquiryService

router = APIRouter(prefix="/contact-inquiries", tags=["Contact Inquiries"])


@router.get("", response_model=APIResponse[list[ContactInquiryResponse]])
def list_inquiries(
    inquiry_type: str | None = None,
    unresolved_only: bool = False,
    current_user: User = Depends(require_permission("ENQUIRIES", "VIEW")),
    db: Session = Depends(get_db),
):
    """List all website contact / bulk-order enquiries."""
    service = ContactInquiryService(db)
    items = service.list_inquiries(inquiry_type=inquiry_type, unresolved_only=unresolved_only)
    return APIResponse(
        success=True,
        message="Contact inquiries retrieved successfully",
        data=[ContactInquiryResponse.model_validate(i) for i in items],
    )


@router.patch("/{inquiry_id}", response_model=APIResponse[ContactInquiryResponse])
def update_inquiry(
    inquiry_id: int,
    payload: ContactInquiryUpdate,
    current_user: User = Depends(require_permission("ENQUIRIES", "UPDATE")),
    db: Session = Depends(get_db),
):
    """Mark an enquiry as read / resolved."""
    service = ContactInquiryService(db)
    inquiry = service.update_inquiry(inquiry_id, payload)
    return APIResponse(
        success=True,
        message="Contact inquiry updated successfully",
        data=ContactInquiryResponse.model_validate(inquiry),
    )


@router.delete("/{inquiry_id}", response_model=APIResponse[None])
def delete_inquiry(
    inquiry_id: int,
    current_user: User = Depends(require_permission("ENQUIRIES", "DELETE")),
    db: Session = Depends(get_db),
):
    """Delete an enquiry (Admin only)."""
    service = ContactInquiryService(db)
    service.delete_inquiry(inquiry_id)
    return APIResponse(success=True, message="Contact inquiry deleted successfully", data=None)
