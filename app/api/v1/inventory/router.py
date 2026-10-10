from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.dependencies.auth import require_permission
from app.dependencies.database import get_db
from app.models.user import User
from app.schemas.common import APIResponse, PaginatedResponse
from app.schemas.inventory import (
    InventoryItemCreate,
    InventoryItemDetailResponse,
    InventoryItemResponse,
    InventoryItemUpdate,
    InventorySummaryResponse,
    InventoryTransactionCreate,
    InventoryTransactionResponse,
)
from app.services.inventory_service import InventoryService

router = APIRouter(prefix="/inventory", tags=["Inventory Management"])


@router.get("/summary", response_model=APIResponse[InventorySummaryResponse])
def get_inventory_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("INVENTORY", "VIEW")),
):
    """Retrieve operational inventory KPI metrics and category valuations."""
    service = InventoryService(db)
    summary = service.get_summary()
    return APIResponse(
        success=True,
        message="Inventory summary retrieved successfully",
        data=summary,
    )


@router.get("/items", response_model=APIResponse[PaginatedResponse[InventoryItemResponse]])
def list_inventory_items(
    category: str | None = Query(None, description="Filter by category (GRAIN, MEAT, DAIRY, etc.)"),
    status_filter: str | None = Query(
        None, description="Filter by status (IN_STOCK, LOW_STOCK, CRITICAL_STOCK, OUT_OF_STOCK)"
    ),
    search: str | None = Query(None, description="Search query by item name, SKU, or supplier"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=200, description="Items per page"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("INVENTORY", "VIEW")),
):
    """List inventory items with search, category, and threshold filtering."""
    service = InventoryService(db)
    items, total, pages = service.list_items(
        category=category,
        status_filter=status_filter,
        search=search,
        page=page,
        page_size=page_size,
    )
    paginated = PaginatedResponse[InventoryItemResponse](
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
        items=items,
    )
    return APIResponse(
        success=True,
        message="Inventory items retrieved successfully",
        data=paginated,
    )


@router.post("/items", response_model=APIResponse[InventoryItemResponse], status_code=status.HTTP_201_CREATED)
def create_inventory_item(
    payload: InventoryItemCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("INVENTORY", "CREATE")),
):
    """Create a new ingredient or inventory item (Manager or Admin)."""
    service = InventoryService(db)
    item = service.create_item(payload, user_id=current_user.id)
    return APIResponse(
        success=True,
        message=f"Inventory item '{item.name}' created successfully",
        data=item,
    )


@router.get("/items/{item_id}", response_model=APIResponse[InventoryItemDetailResponse])
def get_inventory_item(
    item_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("INVENTORY", "VIEW")),
):
    """Get single item details with its recent stock movement transactions."""
    service = InventoryService(db)
    item_detail = service.get_item(item_id)
    return APIResponse(
        success=True,
        message="Item details retrieved successfully",
        data=item_detail,
    )


@router.patch("/items/{item_id}", response_model=APIResponse[InventoryItemResponse])
def update_inventory_item(
    item_id: int,
    payload: InventoryItemUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("INVENTORY", "UPDATE")),
):
    """Update item metadata, safety thresholds, or supplier info (Manager or Admin)."""
    service = InventoryService(db)
    updated = service.update_item(item_id, payload, user_id=current_user.id)
    return APIResponse(
        success=True,
        message=f"Inventory item '{updated.name}' updated successfully",
        data=updated,
    )


@router.delete("/items/{item_id}", response_model=APIResponse[dict[str, str]])
def delete_inventory_item(
    item_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("INVENTORY", "DELETE")),
):
    """Deactivate / soft-delete inventory item (Admin only)."""
    service = InventoryService(db)
    result = service.delete_item(item_id)
    return APIResponse(
        success=True,
        message=result["message"],
        data=result,
    )


@router.post("/items/{item_id}/adjust", response_model=APIResponse[InventoryTransactionResponse])
def adjust_inventory_stock(
    item_id: int,
    payload: InventoryTransactionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("INVENTORY", "CREATE")),
):
    """Record Stock-In, Stock-Out, Wastage, or Physical Audit count. Accessible to Staff, Manager, Admin."""
    service = InventoryService(db)
    tx = service.adjust_stock(item_id, payload, user_id=current_user.id)
    return APIResponse(
        success=True,
        message=f"Recorded {tx.transaction_type} of {tx.quantity} {tx.item_unit} for {tx.item_name}",
        data=tx,
    )


@router.get("/transactions", response_model=APIResponse[PaginatedResponse[InventoryTransactionResponse]])
def list_inventory_transactions(
    item_id: int | None = Query(None, description="Filter transactions by specific inventory item ID"),
    transaction_type: str | None = Query(
        None, description="Filter by type (STOCK_IN, STOCK_OUT, WASTAGE, AUDIT_CORRECTION)"
    ),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=200, description="Transactions per page"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("INVENTORY", "VIEW")),
):
    """List full chronological inventory audit trail across all stock movements."""
    service = InventoryService(db)
    txs, total, pages = service.list_transactions(
        item_id=item_id,
        transaction_type=transaction_type,
        page=page,
        page_size=page_size,
    )
    paginated = PaginatedResponse[InventoryTransactionResponse](
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
        items=txs,
    )
    return APIResponse(
        success=True,
        message="Inventory transactions retrieved successfully",
        data=paginated,
    )
