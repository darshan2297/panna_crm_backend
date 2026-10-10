from typing import Any

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.dependencies.auth import require_permission
from app.dependencies.database import get_db
from app.models.user import User
from app.schemas.common import APIResponse
from app.schemas.integrations import (
    IntegrationConfigRead,
    IntegrationConfigUpdate,
    IntegrationHealthSummary,
    IntegrationLogRead,
    WebhookSimulateRequest,
)
from app.services.audit_service import record_audit
from app.services.integration_service import IntegrationService

router = APIRouter(prefix="/integrations", tags=["Zomato & Swiggy Integrations"])


@router.get("/status", response_model=APIResponse[IntegrationHealthSummary])
def get_integration_status(
    current_user: User = Depends(require_permission("INTEGRATIONS", "VIEW")),
    db: Session = Depends(get_db),
):
    service = IntegrationService(db)
    data = service.get_health_summary()
    return APIResponse(success=True, message="Integration status retrieved", data=data)


@router.patch("/{platform}", response_model=APIResponse[IntegrationConfigRead])
def update_integration_config(
    platform: str,
    payload: IntegrationConfigUpdate,
    current_user: User = Depends(require_permission("INTEGRATIONS", "UPDATE")),
    db: Session = Depends(get_db),
):
    service = IntegrationService(db)
    config = service.update_config(platform=platform, payload=payload)
    record_audit(
        db=db,
        action="UPDATE",
        entity_type="INTEGRATION",
        entity_id=platform.upper(),
        details=f"Updated configuration for {platform}",
        user_email=current_user.email,
        user_id=current_user.id,
    )
    return APIResponse(success=True, message=f"{platform} settings saved", data=config)


@router.post("/sync/{platform}", response_model=APIResponse[dict[str, Any]])
def sync_platform(
    platform: str,
    current_user: User = Depends(require_permission("INTEGRATIONS", "UPDATE")),
    db: Session = Depends(get_db),
):
    service = IntegrationService(db)
    result = service.trigger_sync(platform=platform)
    record_audit(
        db=db,
        action="SYNC",
        entity_type="INTEGRATION",
        entity_id=platform.upper(),
        details=f"Triggered manual sync for {platform}",
        user_email=current_user.email,
        user_id=current_user.id,
    )
    return APIResponse(success=True, message=result.get("message", "Sync completed"), data=result)


@router.post("/zomato/webhook")
async def zomato_webhook(
    request: Request,
    db: Session = Depends(get_db),
):
    body = await request.json()
    service = IntegrationService(db)
    result = service.process_webhook(platform="ZOMATO", payload=body)
    return result


@router.post("/swiggy/webhook")
async def swiggy_webhook(
    request: Request,
    db: Session = Depends(get_db),
):
    body = await request.json()
    service = IntegrationService(db)
    result = service.process_webhook(platform="SWIGGY", payload=body)
    return result


@router.post("/simulate", response_model=APIResponse[dict[str, Any]])
def simulate_webhook_order(
    payload: WebhookSimulateRequest,
    current_user: User = Depends(require_permission("INTEGRATIONS", "UPDATE")),
    db: Session = Depends(get_db),
):
    service = IntegrationService(db)
    result = service.simulate_webhook_order(payload)
    record_audit(
        db=db,
        action="WEBHOOK_SIMULATION",
        entity_type="INTEGRATION",
        entity_id=result.get("order_number"),
        details=f"Simulated {payload.platform} order ingestion: {result.get('order_number')}",
        user_email=current_user.email,
        user_id=current_user.id,
    )
    return APIResponse(success=True, message="Order webhook simulated and ingested", data=result)


@router.get("/logs", response_model=APIResponse[list[IntegrationLogRead]])
def get_integration_logs(
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(require_permission("INTEGRATIONS", "VIEW")),
    db: Session = Depends(get_db),
):
    service = IntegrationService(db)
    logs = service.get_recent_logs(limit=limit)
    return APIResponse(success=True, message="Integration logs retrieved", data=logs)
