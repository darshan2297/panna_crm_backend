"""FAQ router for admin CRUD operations on storefront FAQs."""

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.dependencies.auth import require_permission
from app.dependencies.database import get_db
from app.models.user import User
from app.schemas.common import APIResponse
from app.schemas.faq import FAQCreate, FAQResponse, FAQUpdate
from app.services.faq_service import FAQService

router = APIRouter(prefix="/faqs", tags=["FAQs"])


@router.get("", response_model=APIResponse[list[FAQResponse]])
def list_faqs(
    active_only: bool = True,
    category: str | None = Query(None, description="Filter by category"),
    current_user: User = Depends(require_permission("FAQS", "VIEW")),
    db: Session = Depends(get_db),
):
    """List all FAQs (active only by default)."""
    service = FAQService(db)
    faqs = service.list_faqs(active_only=active_only, category=category)
    return APIResponse(
        success=True,
        message="FAQs retrieved successfully",
        data=[FAQResponse.model_validate(f) for f in faqs],
    )


@router.post("", response_model=APIResponse[FAQResponse], status_code=status.HTTP_201_CREATED)
def create_faq(
    payload: FAQCreate,
    current_user: User = Depends(require_permission("FAQS", "CREATE")),
    db: Session = Depends(get_db),
):
    """Create a new FAQ (Admin/Manager only)."""
    service = FAQService(db)
    faq = service.create_faq(payload)
    return APIResponse(
        success=True,
        message="FAQ created successfully",
        data=FAQResponse.model_validate(faq),
    )


@router.patch("/{faq_id}", response_model=APIResponse[FAQResponse])
def update_faq(
    faq_id: int,
    payload: FAQUpdate,
    current_user: User = Depends(require_permission("FAQS", "UPDATE")),
    db: Session = Depends(get_db),
):
    """Update a FAQ."""
    service = FAQService(db)
    faq = service.update_faq(faq_id, payload)
    return APIResponse(
        success=True,
        message="FAQ updated successfully",
        data=FAQResponse.model_validate(faq),
    )


@router.delete("/{faq_id}", response_model=APIResponse[None])
def delete_faq(
    faq_id: int,
    current_user: User = Depends(require_permission("FAQS", "DELETE")),
    db: Session = Depends(get_db),
):
    """Delete a FAQ (Admin only)."""
    service = FAQService(db)
    service.delete_faq(faq_id)
    return APIResponse(success=True, message="FAQ deleted successfully", data=None)
