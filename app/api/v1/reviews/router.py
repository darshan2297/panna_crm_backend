"""Review router for admin CRUD operations on storefront testimonials."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.dependencies.auth import require_permission
from app.dependencies.database import get_db
from app.models.user import User
from app.schemas.common import APIResponse
from app.schemas.review import ReviewCreate, ReviewResponse, ReviewUpdate
from app.services.review_service import ReviewService

router = APIRouter(prefix="/reviews", tags=["Reviews"])


@router.get("", response_model=APIResponse[list[ReviewResponse]])
def list_reviews(
    active_only: bool = True,
    current_user: User = Depends(require_permission("REVIEWS", "VIEW")),
    db: Session = Depends(get_db),
):
    """List all reviews (active only by default)."""
    service = ReviewService(db)
    reviews = service.list_reviews(active_only=active_only)
    return APIResponse(
        success=True,
        message="Reviews retrieved successfully",
        data=[ReviewResponse.model_validate(r) for r in reviews],
    )


@router.post("", response_model=APIResponse[ReviewResponse], status_code=status.HTTP_201_CREATED)
def create_review(
    payload: ReviewCreate,
    current_user: User = Depends(require_permission("REVIEWS", "CREATE")),
    db: Session = Depends(get_db),
):
    """Create a new review (Admin/Manager only)."""
    service = ReviewService(db)
    review = service.create_review(payload)
    return APIResponse(
        success=True,
        message="Review created successfully",
        data=ReviewResponse.model_validate(review),
    )


@router.patch("/{review_id}", response_model=APIResponse[ReviewResponse])
def update_review(
    review_id: int,
    payload: ReviewUpdate,
    current_user: User = Depends(require_permission("REVIEWS", "UPDATE")),
    db: Session = Depends(get_db),
):
    """Update a review."""
    service = ReviewService(db)
    review = service.update_review(review_id, payload)
    return APIResponse(
        success=True,
        message="Review updated successfully",
        data=ReviewResponse.model_validate(review),
    )


@router.delete("/{review_id}", response_model=APIResponse[None])
def delete_review(
    review_id: int,
    current_user: User = Depends(require_permission("REVIEWS", "DELETE")),
    db: Session = Depends(get_db),
):
    """Delete a review (Admin only)."""
    service = ReviewService(db)
    service.delete_review(review_id)
    return APIResponse(success=True, message="Review deleted successfully", data=None)
