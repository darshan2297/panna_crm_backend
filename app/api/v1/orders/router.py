from datetime import datetime

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.dependencies.auth import get_current_active_user
from app.dependencies.database import get_db
from app.models.user import User
from app.schemas.common import APIResponse, PaginatedResponse
from app.schemas.order import (
    OrderCancelRequest,
    OrderCreate,
    OrderDetailResponse,
    OrderResponse,
    OrderStatusSummary,
    OrderUpdateStatus,
)
from app.services.order_service import OrderService

router = APIRouter(prefix="/orders", tags=["Order Management"])


@router.get("", response_model=PaginatedResponse[OrderResponse])
def list_orders(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    platform: str | None = Query(None, description="Filter by platform (WEBSITE, ZOMATO, SWIGGY)"),
    status: str | None = Query(None, description="Filter by status (NEW, CONFIRMED, PREPARING, etc.)"),
    payment_status: str | None = Query(None, description="Filter by payment status (PENDING, PAID, etc.)"),
    search: str | None = Query(None, description="Search by order ID, customer name, or phone"),
    date_from: datetime | None = Query(None, description="Filter from timestamp"),
    date_to: datetime | None = Query(None, description="Filter to timestamp"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """List orders with filtering, search, and pagination."""
    service = OrderService(db)
    items, total, pages = service.list_orders(
        page=page,
        page_size=page_size,
        platform=platform,
        status=status,
        payment_status=payment_status,
        search=search,
        date_from=date_from,
        date_to=date_to,
    )
    return PaginatedResponse(
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
        items=items,
    )


@router.get("/summary", response_model=APIResponse[OrderStatusSummary])
def get_order_status_summary(
    date_from: datetime | None = Query(None, description="Filter summary from timestamp"),
    date_to: datetime | None = Query(None, description="Filter summary to timestamp"),
    platform: str | None = Query(None, description="Filter summary by platform (WEBSITE, ZOMATO, SWIGGY)"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get real-time operational status summary counts for quick UI badges and filters."""
    service = OrderService(db)
    summary = service.get_order_stats_summary(
        date_from=date_from,
        date_to=date_to,
        platform=platform,
    )
    return APIResponse(
        success=True,
        message="Order status counts retrieved successfully",
        data=summary,
    )


@router.get("/{order_id}", response_model=APIResponse[OrderDetailResponse])
def get_order_details(
    order_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Retrieve full details for an order including items, customer, and status timeline."""
    service = OrderService(db)
    details = service.get_order_details(order_id)
    return APIResponse(
        success=True,
        message=f"Order {details.order_number} details retrieved",
        data=details,
    )


@router.post("", response_model=APIResponse[OrderDetailResponse], status_code=status.HTTP_201_CREATED)
def create_order(
    payload: OrderCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Create a new order manually or from direct counter/phone inquiry."""
    service = OrderService(db)
    order = service.create_order(payload=payload, current_user=current_user)
    return APIResponse(
        success=True,
        message=f"Order {order.order_number} created successfully",
        data=order,
    )


@router.patch("/{order_id}/status", response_model=APIResponse[OrderDetailResponse])
def update_order_status(
    order_id: int,
    payload: OrderUpdateStatus,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Update order status through workflow progression (e.g. NEW -> CONFIRMED -> PREPARING -> READY -> OUT_FOR_DELIVERY -> DELIVERED)."""
    service = OrderService(db)
    updated = service.update_order_status(
        order_id=order_id,
        new_status=payload.new_status,
        notes=payload.notes,
        current_user=current_user,
    )
    return APIResponse(
        success=True,
        message=f"Order status updated to {payload.new_status.value}",
        data=updated,
    )


@router.post("/{order_id}/cancel", response_model=APIResponse[OrderDetailResponse])
def cancel_order(
    order_id: int,
    payload: OrderCancelRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Cancel an active order with reason log."""
    service = OrderService(db)
    cancelled = service.cancel_order(
        order_id=order_id,
        reason=payload.reason,
        current_user=current_user,
    )
    return APIResponse(
        success=True,
        message=f"Order {cancelled.order_number} has been cancelled",
        data=cancelled,
    )
