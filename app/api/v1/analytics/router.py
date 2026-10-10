from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from app.dependencies.auth import require_permission
from app.dependencies.database import get_db
from app.models.user import User
from app.schemas.analytics import (
    CustomerSegmentsResponse,
    DishCostingResponse,
    OrderVelocityResponse,
    PlatformBreakdownResponse,
    PLSummaryResponse,
    SalesTrendResponse,
    TopItemsResponse,
)
from app.schemas.common import APIResponse
from app.services.analytics_service import AnalyticsService

router = APIRouter(prefix="/analytics", tags=["Analytics & Reports"])


@router.get("/sales-trend", response_model=APIResponse[SalesTrendResponse])
def get_sales_trend(
    days: int = Query(7, ge=1, le=365, description="Number of days to analyze"),
    current_user: User = Depends(require_permission("ANALYTICS", "VIEW")),
    db: Session = Depends(get_db),
):
    service = AnalyticsService(db)
    data = service.get_sales_trend(days=days)
    return APIResponse(success=True, message=f"{days}-day sales trend retrieved", data=data)


@router.get("/top-items", response_model=APIResponse[TopItemsResponse])
def get_top_items(
    days: int = Query(30, ge=1, le=365),
    limit: int = Query(10, ge=1, le=50),
    sort_by: str = Query("revenue", pattern="^(revenue|quantity)$"),
    current_user: User = Depends(require_permission("ANALYTICS", "VIEW")),
    db: Session = Depends(get_db),
):
    service = AnalyticsService(db)
    data = service.get_top_items(days=days, limit=limit, sort_by=sort_by)
    return APIResponse(success=True, message="Top selling items retrieved", data=data)


@router.get("/platform-breakdown", response_model=APIResponse[PlatformBreakdownResponse])
def get_platform_breakdown(
    days: int = Query(30, ge=1, le=365),
    current_user: User = Depends(require_permission("ANALYTICS", "VIEW")),
    db: Session = Depends(get_db),
):
    service = AnalyticsService(db)
    data = service.get_platform_breakdown(days=days)
    return APIResponse(success=True, message="Platform revenue breakdown retrieved", data=data)


@router.get("/order-velocity", response_model=APIResponse[OrderVelocityResponse])
def get_order_velocity(
    days: int = Query(30, ge=1, le=365),
    current_user: User = Depends(require_permission("ANALYTICS", "VIEW")),
    db: Session = Depends(get_db),
):
    service = AnalyticsService(db)
    data = service.get_order_velocity(days=days)
    return APIResponse(success=True, message="Order velocity heatmap data retrieved", data=data)


@router.get("/customer-segments", response_model=APIResponse[CustomerSegmentsResponse])
def get_customer_segments(
    current_user: User = Depends(require_permission("ANALYTICS", "VIEW")),
    db: Session = Depends(get_db),
):
    service = AnalyticsService(db)
    data = service.get_customer_segments()
    return APIResponse(success=True, message="Customer segment analytics retrieved", data=data)


@router.get("/costing/dishes", response_model=APIResponse[DishCostingResponse])
def get_dish_costing(
    current_user: User = Depends(require_permission("ANALYTICS", "VIEW")),
    db: Session = Depends(get_db),
):
    service = AnalyticsService(db)
    data = service.get_dish_costing()
    return APIResponse(success=True, message="Dish margin and costing analysis retrieved", data=data)


@router.get("/costing/summary", response_model=APIResponse[PLSummaryResponse])
def get_pl_summary(
    days: int = Query(30, ge=1, le=365),
    current_user: User = Depends(require_permission("ANALYTICS", "VIEW")),
    db: Session = Depends(get_db),
):
    service = AnalyticsService(db)
    data = service.get_pl_summary(days=days)
    return APIResponse(success=True, message="Kitchen P&L summary retrieved", data=data)


@router.get("/export")
def export_analytics_csv(
    dataset: str = Query("sales", pattern="^(sales|top_items|costing|platforms)$"),
    days: int = Query(30, ge=1, le=365),
    current_user: User = Depends(require_permission("ANALYTICS", "VIEW")),
    db: Session = Depends(get_db),
):
    service = AnalyticsService(db)
    csv_data = service.export_csv(dataset=dataset, days=days)
    filename = f"panna_crm_{dataset}_{days}d.csv"

    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename={filename}",
            "Content-Type": "text/csv; charset=utf-8",
        },
    )
