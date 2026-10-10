from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.dependencies.auth import require_permission
from app.dependencies.database import get_db
from app.models.user import User
from app.schemas.common import APIResponse
from app.schemas.dashboard import DashboardResponse, RecentOrderSummary
from app.services.dashboard_service import DashboardService

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/stats", response_model=APIResponse[DashboardResponse])
def get_dashboard_stats(
    current_user: User = Depends(require_permission("DASHBOARD", "VIEW")),
    db: Session = Depends(get_db),
):
    """Retrieve complete live operational overview, KPIs, trends, top items, and alerts."""
    service = DashboardService(db)
    data = service.get_dashboard_data()
    return APIResponse(
        success=True,
        message="Dashboard statistics retrieved successfully",
        data=data,
    )


@router.get("/recent-orders", response_model=APIResponse[list[RecentOrderSummary]])
def get_recent_orders(
    current_user: User = Depends(require_permission("DASHBOARD", "VIEW")),
    db: Session = Depends(get_db),
):
    """Retrieve latest orders for the live kitchen dashboard."""
    service = DashboardService(db)
    data = service.get_dashboard_data()
    return APIResponse(
        success=True,
        message="Recent orders retrieved",
        data=data.recent_orders,
    )
