from fastapi import APIRouter, Depends, Path, status
from sqlalchemy.orm import Session

from app.dependencies.database import get_db
from app.schemas.common import APIResponse
from app.schemas.public_order import (
    PaymentWebhookRequest,
    PaymentWebhookResponse,
    PublicOrderTrackResponse,
    WebsiteOrderCreateRequest,
    WebsiteOrderCreateResponse,
)
from app.services.order_service import OrderService

router = APIRouter(prefix="/public", tags=["Public Storefront Gateway"])


@router.post("/orders", response_model=APIResponse[WebsiteOrderCreateResponse], status_code=status.HTTP_201_CREATED)
def submit_website_order(
    payload: WebsiteOrderCreateRequest,
    db: Session = Depends(get_db),
):
    """
    Public Endpoint: Ingest direct online order placed from customer-facing website.
    - No staff auth required
    - Automatic customer profile creation/linking
    - Instant order injection into kitchen pipeline with PB-W reference
    """
    service = OrderService(db)
    order_data = service.create_website_order(payload)
    return APIResponse(
        success=True,
        message="Order placed successfully! Kitchen has received your request.",
        data=order_data,
    )


@router.get("/orders/track/{order_number}", response_model=APIResponse[PublicOrderTrackResponse])
def track_website_order(
    order_number: str = Path(..., description="Order number (e.g. PB-W-20261003-1001)"),
    db: Session = Depends(get_db),
):
    """
    Public Endpoint: Customer real-time order tracking.
    - Sanitized customer view (privacy-masked phone, non-confidential status timeline)
    - Real-time preparation & delivery ETA
    """
    service = OrderService(db)
    tracking_data = service.track_public_order(order_number)
    return APIResponse(
        success=True,
        message="Order tracking status retrieved successfully",
        data=tracking_data,
    )


@router.post("/orders/{order_number}/payment-webhook", response_model=APIResponse[PaymentWebhookResponse])
def payment_status_webhook(
    order_number: str = Path(..., description="Order number for callback"),
    payload: PaymentWebhookRequest = ...,
    db: Session = Depends(get_db),
):
    """
    Public/Gateway Callback: Payment gateway status webhook.
    - Updates order payment status (PAID/FAILED/REFUNDED)
    - Auto-confirms paid orders into kitchen preparation pipeline
    - Logs audit event with gateway reference ID
    """
    service = OrderService(db)
    webhook_res = service.process_payment_webhook(order_number, payload)
    return APIResponse(
        success=True,
        message=webhook_res.message,
        data=webhook_res,
    )


@router.get("/shop-status")
def get_shop_status(db: Session = Depends(get_db)):
    """Public Endpoint: Report open/closed state of each sales channel."""
    from app.models.integration import IntegrationConfig

    configs = db.query(IntegrationConfig).all()
    platforms = {c.platform: bool(c.shop_open) for c in configs}
    return APIResponse(
        success=True,
        message="Shop status retrieved successfully",
        data={
            "platforms": platforms,
            "website_open": platforms.get("WEBSITE", True),
            "zomato_open": platforms.get("ZOMATO", True),
            "swiggy_open": platforms.get("SWIGGY", True),
        },
    )


@router.get("/orders/gateway/health")
def website_gateway_health() -> dict[str, str]:
    """Lightweight ping to verify public website order ingestion gateway readiness."""
    return {
        "status": "online",
        "service": "Panna Website Order Integration Gateway",
        "version": "1.0.0",
        "platform": "WEBSITE",
    }


@router.get("/menu")
def get_public_menu(db: Session = Depends(get_db)):
    """
    Public Endpoint: Categorized menu for customer storefronts.
    Returns active categories with currently available items and portions.
    """
    from app.services.menu_service import MenuService

    service = MenuService(db)
    categories = service.list_categories(is_active=True)
    items = service.list_items(is_active=True, is_available=True)

    # Group items by category
    categorized = []
    items_by_cat = {}
    for itm in items:
        items_by_cat.setdefault(itm.category_id, []).append(itm)

    for cat in categories:
        cat_dict = cat.model_dump()
        cat_dict["items"] = [i.model_dump() for i in items_by_cat.get(cat.id, [])]
        categorized.append(cat_dict)

    return APIResponse(
        success=True,
        message="Public menu retrieved successfully",
        data=categorized,
    )
