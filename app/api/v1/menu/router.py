
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.dependencies.auth import get_current_active_user, require_roles
from app.dependencies.database import get_db
from app.models.user import User, UserRole
from app.schemas.common import APIResponse
from app.schemas.menu import (
    MenuCategoryCreate,
    MenuCategoryResponse,
    MenuCategoryUpdate,
    MenuItemAvailabilityUpdate,
    MenuItemCreate,
    MenuItemResponse,
    MenuItemUpdate,
    MenuSummaryResponse,
    PlatformPriceCalculationRequest,
    PlatformPriceCalculationResponse,
)
from app.services.menu_service import MenuService

router = APIRouter(prefix="/menu", tags=["Menu Management"])


# ---------------- Summary & Pricing Helpers ----------------

@router.get("/summary", response_model=APIResponse[MenuSummaryResponse])
def get_menu_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Retrieve operational menu KPI summary metrics."""
    service = MenuService(db)
    summary = service.get_menu_summary()
    return APIResponse(
        success=True,
        message="Menu summary retrieved successfully",
        data=summary,
    )


@router.post("/calculate-prices", response_model=APIResponse[PlatformPriceCalculationResponse])
def calculate_platform_prices(
    payload: PlatformPriceCalculationRequest,
    current_user: User = Depends(get_current_active_user),
):
    """Calculate platform pricing rules (Website: 0%, Zomato: +22%, Swiggy: +20%)."""
    calc = MenuService.calculate_platform_prices(payload.base_price)
    return APIResponse(
        success=True,
        message="Platform prices calculated successfully",
        data=calc,
    )


# ---------------- Categories ----------------

@router.get("/categories", response_model=APIResponse[list[MenuCategoryResponse]])
def list_menu_categories(
    is_active: bool | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """List all menu categories with item counts and display order."""
    service = MenuService(db)
    categories = service.list_categories(is_active=is_active)
    return APIResponse(
        success=True,
        message="Menu categories retrieved successfully",
        data=categories,
    )


@router.post("/categories", response_model=APIResponse[MenuCategoryResponse], status_code=status.HTTP_201_CREATED)
def create_menu_category(
    payload: MenuCategoryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.ADMIN, UserRole.MANAGER])),
):
    """Create a new menu category (Admin/Manager only)."""
    service = MenuService(db)
    category = service.create_category(payload)
    return APIResponse(
        success=True,
        message="Menu category created successfully",
        data=category,
    )


@router.patch("/categories/{category_id}", response_model=APIResponse[MenuCategoryResponse])
def update_menu_category(
    category_id: int,
    payload: MenuCategoryUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.ADMIN, UserRole.MANAGER])),
):
    """Update category details or active status."""
    service = MenuService(db)
    category = service.update_category(category_id, payload)
    return APIResponse(
        success=True,
        message="Menu category updated successfully",
        data=category,
    )


@router.delete("/categories/{category_id}", response_model=APIResponse[None], status_code=status.HTTP_200_OK)
def delete_menu_category(
    category_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.ADMIN, UserRole.MANAGER])),
):
    """Delete a menu category and its items (Admin only)."""
    service = MenuService(db)
    service.delete_category(category_id)
    return APIResponse(
        success=True,
        message="Menu category deleted successfully",
        data=None,
    )


# ---------------- Menu Items ----------------

@router.get("/items", response_model=APIResponse[list[MenuItemResponse]])
def list_menu_items(
    category_id: int | None = Query(None, description="Filter by category ID"),
    is_veg: bool | None = Query(None, description="Filter vegetarian vs non-vegetarian"),
    is_available: bool | None = Query(None, description="Filter in-stock vs out-of-stock"),
    is_active: bool | None = Query(None, description="Filter published status"),
    search: str | None = Query(None, description="Search item name or description"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """List menu items with filters and portion prices."""
    service = MenuService(db)
    items = service.list_items(
        category_id=category_id,
        is_veg=is_veg,
        is_available=is_available,
        is_active=is_active,
        search=search,
        skip=skip,
        limit=limit,
    )
    return APIResponse(
        success=True,
        message="Menu items retrieved successfully",
        data=items,
    )


@router.get("/items/{item_id}", response_model=APIResponse[MenuItemResponse])
def get_menu_item(
    item_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Get full details of a specific menu item with portions."""
    service = MenuService(db)
    item = service.get_item_response(item_id)
    return APIResponse(
        success=True,
        message="Menu item retrieved successfully",
        data=item,
    )


@router.post("/items", response_model=APIResponse[MenuItemResponse], status_code=status.HTTP_201_CREATED)
def create_menu_item(
    payload: MenuItemCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.ADMIN, UserRole.MANAGER])),
):
    """Create a new menu dish with portion sizes and platform pricing (Admin/Manager only)."""
    service = MenuService(db)
    item = service.create_item(payload)
    return APIResponse(
        success=True,
        message="Menu item created successfully",
        data=item,
    )


@router.patch("/items/{item_id}", response_model=APIResponse[MenuItemResponse])
def update_menu_item(
    item_id: int,
    payload: MenuItemUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.ADMIN, UserRole.MANAGER])),
):
    """Update menu dish metadata, portions, or platform prices."""
    service = MenuService(db)
    item = service.update_item(item_id, payload)
    return APIResponse(
        success=True,
        message="Menu item updated successfully",
        data=item,
    )


@router.patch("/items/{item_id}/availability", response_model=APIResponse[MenuItemResponse])
def toggle_item_availability(
    item_id: int,
    payload: MenuItemAvailabilityUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Fast 1-click in-stock / out-of-stock toggle (Accessible to Staff, Managers, Admins)."""
    service = MenuService(db)
    item = service.toggle_item_availability(item_id, payload.is_available)
    status_str = "In Stock" if payload.is_available else "Out of Stock"
    return APIResponse(
        success=True,
        message=f"Menu item status updated to {status_str}",
        data=item,
    )


@router.delete("/items/{item_id}", response_model=APIResponse[None], status_code=status.HTTP_200_OK)
def delete_menu_item(
    item_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.ADMIN, UserRole.MANAGER])),
):
    """Delete a menu item and its portions."""
    service = MenuService(db)
    service.delete_item(item_id)
    return APIResponse(
        success=True,
        message="Menu item deleted successfully",
        data=None,
    )
