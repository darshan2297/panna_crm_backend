from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundException
from app.dependencies.auth import require_permission
from app.dependencies.database import get_db
from app.models.user import User
from app.schemas.common import APIResponse, PaginatedResponse
from app.schemas.restock_order import (
    RestockOrderCreate,
    RestockOrderOut,
    RestockSuggestionItem,
    RestockSummary,
)
from app.services.restock_service import RestockService
from app.utils.pagination import calc_pages

router = APIRouter(prefix="/restock", tags=["Restock & Purchase Orders"])


class StatusUpdateInput(BaseModel):
    status: str  # DRAFT, ORDERED, CANCELLED


@router.get("/suggestions", response_model=APIResponse[list[RestockSuggestionItem]])
def get_restock_suggestions(
    target_type: str | None = Query(None, description="INVENTORY, PACKAGING, or None for all"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("RESTOCK", "VIEW")),
):
    """Retrieve all ingredients and packaging items needing replenishment, ranked by deficit."""
    items = RestockService.get_deficit_suggestions(db=db, target_type=target_type)
    return APIResponse(
        success=True,
        message="Restock suggestions retrieved successfully",
        data=items,
    )


@router.get("/suppliers", response_model=APIResponse[list[str]])
def get_distinct_suppliers(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("RESTOCK", "VIEW")),
):
    """Distinct supplier names across inventory_items and packaging_items."""
    suppliers = RestockService.get_distinct_suppliers(db=db)
    return APIResponse(
        success=True,
        message="Suppliers retrieved successfully",
        data=suppliers,
    )


@router.get("/summary", response_model=APIResponse[RestockSummary])
def get_restock_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("RESTOCK", "VIEW")),
):
    """Retrieve overall restock KPI overview and investment requirement."""
    summary = RestockService.get_restock_summary(db=db)
    return APIResponse(
        success=True,
        message="Restock summary retrieved successfully",
        data=summary,
    )


@router.get("/orders", response_model=APIResponse[PaginatedResponse[RestockOrderOut]])
def list_restock_orders(
    status: str | None = Query(None, description="Filter by status: DRAFT, ORDERED, RECEIVED, CANCELLED"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("RESTOCK", "VIEW")),
):
    """List purchase orders with pagination and status filter."""
    total, items = RestockService.list_orders(
        db=db,
        status=status,
        page=page,
        page_size=page_size,
    )
    pages = calc_pages(total, page_size)

    return APIResponse(
        success=True,
        message="Restock orders retrieved successfully",
        data=PaginatedResponse(
            total=total,
            page=page,
            page_size=page_size,
            pages=pages,
            items=[RestockOrderOut.model_validate(o) for o in items],
        ),
    )


@router.post("/orders", response_model=APIResponse[RestockOrderOut])
def create_restock_order(
    payload: RestockOrderCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("RESTOCK", "CREATE")),
):
    """Create a new restock purchase order."""
    user_name = current_user.full_name or current_user.username or "Kitchen Manager"
    order = RestockService.create_restock_order(
        db=db,
        payload=payload,
        user_name=user_name,
    )
    return APIResponse(
        success=True,
        message=f"Purchase Order {order.po_number} created successfully",
        data=RestockOrderOut.model_validate(order),
    )


@router.get("/orders/{id}", response_model=APIResponse[RestockOrderOut])
def get_restock_order_details(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("RESTOCK", "VIEW")),
):
    """Retrieve detailed purchase order information with items."""
    order = RestockService.get_order_details(db=db, po_id=id)
    if not order:
        raise NotFoundException("Restock Order")
    return APIResponse(
        success=True,
        message="Purchase order details retrieved",
        data=RestockOrderOut.model_validate(order),
    )


@router.patch("/orders/{id}/status", response_model=APIResponse[RestockOrderOut])
def update_restock_order_status(
    id: int,
    payload: StatusUpdateInput,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("RESTOCK", "UPDATE")),
):
    """Update PO status (e.g. mark ORDERED or CANCELLED)."""
    order = RestockService.update_order_status(db=db, po_id=id, new_status=payload.status)
    if not order:
        raise NotFoundException("Restock Order")
    return APIResponse(
        success=True,
        message=f"Order status updated to {order.status}",
        data=RestockOrderOut.model_validate(order),
    )


@router.post("/orders/{id}/receive", response_model=APIResponse[RestockOrderOut])
def receive_restock_goods(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("RESTOCK", "CREATE")),
):
    """
    1-Click Goods Receipt:
    Automatically updates the inventory ingredients and packaging materials stock balances,
    logs STOCK_IN audit transactions, and closes the PO as RECEIVED.
    """
    user_name = current_user.full_name or current_user.username or "Kitchen Store Manager"
    order = RestockService.receive_restock_order(
        db=db,
        po_id=id,
        received_by=user_name,
    )
    return APIResponse(
        success=True,
        message=f"Purchase Order {order.po_number} goods received into stock successfully",
        data=RestockOrderOut.model_validate(order),
    )
