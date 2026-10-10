"""DeliveryArea router for admin CRUD operations on storefront delivery zones."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.dependencies.auth import require_permission
from app.dependencies.database import get_db
from app.models.user import User
from app.schemas.common import APIResponse
from app.schemas.delivery_area import (
    DeliveryAreaCreate,
    DeliveryAreaResponse,
    DeliveryAreaUpdate,
)
from app.services.delivery_area_service import DeliveryAreaService

router = APIRouter(prefix="/delivery-areas", tags=["Delivery Areas"])


@router.get("", response_model=APIResponse[list[DeliveryAreaResponse]])
def list_delivery_areas(
    active_only: bool = True,
    current_user: User = Depends(require_permission("DELIVERY_AREAS", "VIEW")),
    db: Session = Depends(get_db),
):
    """List all delivery areas (active only by default)."""
    service = DeliveryAreaService(db)
    areas = service.list_areas(active_only=active_only)
    return APIResponse(
        success=True,
        message="Delivery areas retrieved successfully",
        data=[DeliveryAreaResponse.model_validate(a) for a in areas],
    )


@router.post("", response_model=APIResponse[DeliveryAreaResponse], status_code=status.HTTP_201_CREATED)
def create_delivery_area(
    payload: DeliveryAreaCreate,
    current_user: User = Depends(require_permission("DELIVERY_AREAS", "CREATE")),
    db: Session = Depends(get_db),
):
    """Create a new delivery area (Admin/Manager only)."""
    service = DeliveryAreaService(db)
    area = service.create_area(payload)
    return APIResponse(
        success=True,
        message="Delivery area created successfully",
        data=DeliveryAreaResponse.model_validate(area),
    )


@router.patch("/{area_id}", response_model=APIResponse[DeliveryAreaResponse])
def update_delivery_area(
    area_id: int,
    payload: DeliveryAreaUpdate,
    current_user: User = Depends(require_permission("DELIVERY_AREAS", "UPDATE")),
    db: Session = Depends(get_db),
):
    """Update a delivery area."""
    service = DeliveryAreaService(db)
    area = service.update_area(area_id, payload)
    return APIResponse(
        success=True,
        message="Delivery area updated successfully",
        data=DeliveryAreaResponse.model_validate(area),
    )


@router.delete("/{area_id}", response_model=APIResponse[None])
def delete_delivery_area(
    area_id: int,
    current_user: User = Depends(require_permission("DELIVERY_AREAS", "DELETE")),
    db: Session = Depends(get_db),
):
    """Delete a delivery area (Admin only)."""
    service = DeliveryAreaService(db)
    service.delete_area(area_id)
    return APIResponse(success=True, message="Delivery area deleted successfully", data=None)
