from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.dependencies.auth import get_current_active_user, require_roles
from app.dependencies.database import get_db
from app.models.user import User, UserRole
from app.schemas.common import APIResponse, PaginatedResponse
from app.schemas.packaging import (
    PackagingConsumptionRuleCreate,
    PackagingConsumptionRuleResponse,
    PackagingItemCreate,
    PackagingItemDetailResponse,
    PackagingItemResponse,
    PackagingItemUpdate,
    PackagingOrderSimulationRequest,
    PackagingOrderSimulationResponse,
    PackagingSummaryResponse,
    PackagingTransactionCreate,
    PackagingTransactionResponse,
)
from app.services.packaging_service import PackagingService
from app.utils.pagination import calc_pages

router = APIRouter(prefix="/packaging", tags=["Packaging Management"])


@router.get("/summary", response_model=APIResponse[PackagingSummaryResponse])
def get_packaging_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Retrieve operational packaging KPI metrics, valuations, and daily consumption burn rate."""
    service = PackagingService(db)
    summary = service.get_summary()
    return APIResponse(
        success=True,
        message="Packaging summary retrieved successfully",
        data=summary,
    )


@router.get("/items", response_model=APIResponse[PaginatedResponse[PackagingItemResponse]])
def list_packaging_items(
    category: str | None = Query(None, description="Filter by category (CONTAINER, BAG, ACCOMPANIMENT, CUTLERY, etc.)"),
    stock_status: str | None = Query(None, description="Filter by status (IN_STOCK, LOW_STOCK, CRITICAL, OUT_OF_STOCK)"),
    material: str | None = Query(None, description="Filter by material (Kraft Paper, PP, Clay, Wood, etc.)"),
    search: str | None = Query(None, description="Search by name, SKU, supplier, or description"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=200, description="Items per page"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """List packaging items with search, material, category, and threshold filtering."""
    service = PackagingService(db)
    items, total = service.list_items(
        category=category,
        stock_status=stock_status,
        material=material,
        search=search,
        page=page,
        page_size=page_size,
    )
    pages = calc_pages(total, page_size)
    paginated = PaginatedResponse[PackagingItemResponse](
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
        items=items,
    )
    return APIResponse(
        success=True,
        message="Packaging items retrieved successfully",
        data=paginated,
    )


@router.post("/items", response_model=APIResponse[PackagingItemResponse], status_code=status.HTTP_201_CREATED)
def create_packaging_item(
    payload: PackagingItemCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.ADMIN.value, UserRole.MANAGER.value])),
):
    """Create a new packaging item with automatic SKU generation."""
    service = PackagingService(db)
    created = service.create_item(payload)
    return APIResponse(
        success=True,
        message=f"Packaging item '{created.name}' created successfully",
        data=created,
    )


@router.get("/items/{item_id}", response_model=APIResponse[PackagingItemDetailResponse])
def get_packaging_item(
    item_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Retrieve detailed packaging item information with recent movement history."""
    service = PackagingService(db)
    item = service.get_item(item_id)
    return APIResponse(
        success=True,
        message="Packaging item details retrieved successfully",
        data=item,
    )


@router.patch("/items/{item_id}", response_model=APIResponse[PackagingItemResponse])
def update_packaging_item(
    item_id: int,
    payload: PackagingItemUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.ADMIN.value, UserRole.MANAGER.value])),
):
    """Update packaging item metadata, costs, safety thresholds, or supplier."""
    service = PackagingService(db)
    updated = service.update_item(item_id, payload)
    return APIResponse(
        success=True,
        message=f"Packaging item '{updated.name}' updated successfully",
        data=updated,
    )


@router.delete("/items/{item_id}", response_model=APIResponse[bool])
def delete_packaging_item(
    item_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.ADMIN.value])),
):
    """Soft-delete a packaging item."""
    service = PackagingService(db)
    service.delete_item(item_id)
    return APIResponse(
        success=True,
        message="Packaging item deactivated successfully",
        data=True,
    )


@router.post("/items/{item_id}/adjust", response_model=APIResponse[PackagingItemResponse])
def adjust_packaging_stock(
    item_id: int,
    payload: PackagingTransactionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Record packaging stock movement (STOCK_IN, STOCK_OUT, WASTAGE, AUDIT_CORRECTION)."""
    service = PackagingService(db)
    item, tx = service.adjust_stock(item_id, payload, current_user=current_user)
    return APIResponse(
        success=True,
        message=f"Stock movement recorded. New balance: {item.current_stock} {item.unit}",
        data=item,
    )


@router.get("/transactions", response_model=APIResponse[PaginatedResponse[PackagingTransactionResponse]])
def list_packaging_transactions(
    packaging_item_id: int | None = Query(None, description="Filter by packaging item ID"),
    transaction_type: str | None = Query(None, description="Filter by type (STOCK_IN, STOCK_OUT, WASTAGE, etc.)"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(25, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Chronological audit trail of all packaging movements, purchases, and wastage."""
    service = PackagingService(db)
    txs, total = service.list_transactions(
        packaging_item_id=packaging_item_id,
        transaction_type=transaction_type,
        page=page,
        page_size=page_size,
    )
    pages = calc_pages(total, page_size)
    paginated = PaginatedResponse[PackagingTransactionResponse](
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
        items=txs,
    )
    return APIResponse(
        success=True,
        message="Packaging transactions retrieved successfully",
        data=paginated,
    )


@router.get("/rules", response_model=APIResponse[list[PackagingConsumptionRuleResponse]])
def list_packaging_rules(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Retrieve auto-consumption packaging rules linking dish categories/portions to packaging."""
    service = PackagingService(db)
    rules = service.list_consumption_rules()
    return APIResponse(
        success=True,
        message="Packaging consumption rules retrieved successfully",
        data=rules,
    )


@router.post("/rules", response_model=APIResponse[PackagingConsumptionRuleResponse], status_code=status.HTTP_201_CREATED)
def create_packaging_rule(
    payload: PackagingConsumptionRuleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.ADMIN.value, UserRole.MANAGER.value])),
):
    """Create a new auto-consumption mapping rule for kitchen orders."""
    service = PackagingService(db)
    rule = service.create_consumption_rule(payload)
    return APIResponse(
        success=True,
        message="Packaging consumption rule created successfully",
        data=rule,
    )


@router.delete("/rules/{rule_id}", response_model=APIResponse[bool])
def delete_packaging_rule(
    rule_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.ADMIN.value, UserRole.MANAGER.value])),
):
    """Deactivate a packaging consumption rule."""
    service = PackagingService(db)
    service.delete_consumption_rule(rule_id)
    return APIResponse(
        success=True,
        message="Packaging rule removed successfully",
        data=True,
    )


@router.post("/simulate-order-consumption", response_model=APIResponse[PackagingOrderSimulationResponse])
def simulate_order_consumption(
    payload: PackagingOrderSimulationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Calculate packaging items consumed and total packaging cost in ₹ for an order payload."""
    service = PackagingService(db)
    result = service.simulate_order_consumption(payload.items)
    return APIResponse(
        success=True,
        message="Order packaging consumption simulated successfully",
        data=result,
    )
