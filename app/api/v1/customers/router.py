from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.dependencies.auth import require_permission
from app.dependencies.database import get_db
from app.models.user import User
from app.schemas.common import APIResponse, PaginatedResponse
from app.schemas.customer import (
    CustomerDetailResponse,
    CustomerNoteCreate,
    CustomerOrderBrief,
    CustomerResponse,
    CustomerSummary,
    CustomerUpdate,
)
from app.services.customer_service import CustomerService

router = APIRouter(prefix="/customers", tags=["Customer CRM"])


@router.get("/summary", response_model=APIResponse[CustomerSummary])
def get_customer_summary(
    current_user: User = Depends(require_permission("CUSTOMERS", "VIEW")),
    db: Session = Depends(get_db),
):
    """Get customer KPI summary: totals, segments, revenue."""
    service = CustomerService(db)
    summary = service.get_summary()
    return APIResponse(
        success=True,
        message="Customer summary retrieved",
        data=summary,
    )


@router.get("", response_model=PaginatedResponse[CustomerResponse])
def list_customers(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str | None = Query(None, description="Search by name, phone, or email"),
    segment: str | None = Query(None, description="Filter by segment: VIP, REGULAR, LAPSED, NEW, ALL"),
    sort_by: str = Query("total_spent", description="Sort by: total_spent, total_orders, last_order, name, newest"),
    current_user: User = Depends(require_permission("CUSTOMERS", "VIEW")),
    db: Session = Depends(get_db),
):
    """List customers with search, segment filter, and flexible sorting."""
    service = CustomerService(db)
    items, total, pages = service.list_customers(
        page=page,
        page_size=page_size,
        search=search,
        segment=segment,
        sort_by=sort_by,
    )
    return PaginatedResponse(
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
        items=items,
    )


@router.get("/{customer_id}", response_model=APIResponse[CustomerDetailResponse])
def get_customer(
    customer_id: int,
    current_user: User = Depends(require_permission("CUSTOMERS", "VIEW")),
    db: Session = Depends(get_db),
):
    """Retrieve full 360° customer profile with order history and preferences."""
    service = CustomerService(db)
    detail = service.get_customer(customer_id)
    return APIResponse(
        success=True,
        message="Customer profile retrieved",
        data=detail,
    )


@router.patch("/{customer_id}", response_model=APIResponse[CustomerResponse])
def update_customer(
    customer_id: int,
    payload: CustomerUpdate,
    current_user: User = Depends(require_permission("CUSTOMERS", "UPDATE")),
    db: Session = Depends(get_db),
):
    """Update customer contact details or internal notes."""
    service = CustomerService(db)
    updated = service.update_customer(customer_id, payload)
    return APIResponse(
        success=True,
        message="Customer updated successfully",
        data=updated,
    )


@router.post("/{customer_id}/notes", response_model=APIResponse[CustomerResponse])
def add_customer_note(
    customer_id: int,
    payload: CustomerNoteCreate,
    current_user: User = Depends(require_permission("CUSTOMERS", "CREATE")),
    db: Session = Depends(get_db),
):
    """Append a timestamped internal CRM note to a customer profile."""
    service = CustomerService(db)
    updated = service.add_note(customer_id, payload.note)
    return APIResponse(
        success=True,
        message="Note added to customer profile",
        data=updated,
    )


@router.get("/{customer_id}/orders", response_model=PaginatedResponse[CustomerOrderBrief])
def get_customer_orders(
    customer_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=50),
    current_user: User = Depends(require_permission("CUSTOMERS", "VIEW")),
    db: Session = Depends(get_db),
):
    """Get paginated order history for a specific customer."""
    service = CustomerService(db)
    items, total, pages = service.get_customer_orders(customer_id, page, page_size)
    return PaginatedResponse(
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
        items=items,
    )


@router.post("/refresh-segments", response_model=APIResponse[dict])
def refresh_segments(
    current_user: User = Depends(require_permission("CUSTOMERS", "CREATE")),
    db: Session = Depends(get_db),
):
    """Batch-refresh all customer segments based on recency and spend rules."""
    service = CustomerService(db)
    updated = service.refresh_all_segments()
    return APIResponse(
        success=True,
        message=f"{updated} customer segment(s) updated",
        data={"updated": updated},
    )
