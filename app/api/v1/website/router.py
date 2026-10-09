import os
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.dependencies.auth import get_current_active_user, require_roles
from app.dependencies.database import get_db
from app.models.user import User, UserRole
from app.schemas.common import APIResponse
from app.schemas.storefront import (
    PaymentMethodCreate,
    PaymentMethodResponse,
    PaymentMethodUpdate,
    PromoCodeCreate,
    PromoCodeResponse,
    PromoCodeUpdate,
    PromoCodeValidateRequest,
    StorefrontConfigResponse,
    StorefrontConfigUpdate,
)
from app.services.storefront_service import StorefrontService

router = APIRouter(prefix="/website", tags=["Website Storefront Config"])

UPLOAD_DIR = os.path.join(os.getcwd(), "media", "uploads")
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".avif", ".svg"}
MAX_FILE_SIZE = 10 * 1024 * 1024


@router.get("/config", response_model=APIResponse[StorefrontConfigResponse])
def get_storefront_config(db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)):
    service = StorefrontService(db)
    return APIResponse(success=True, message="Storefront config retrieved", data=service.get_config())


@router.put("/config", response_model=APIResponse[StorefrontConfigResponse])
def update_storefront_config(
    payload: StorefrontConfigUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.ADMIN, UserRole.MANAGER])),
):
    service = StorefrontService(db)
    cfg = service.update_config(payload)
    return APIResponse(success=True, message="Storefront config updated", data=cfg)


@router.get("/payment-methods", response_model=APIResponse[list[PaymentMethodResponse]])
def list_payment_methods(db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)):
    service = StorefrontService(db)
    return APIResponse(success=True, message="Payment methods retrieved", data=service.list_payment_methods())


@router.post("/payment-methods", response_model=APIResponse[PaymentMethodResponse], status_code=status.HTTP_201_CREATED)
def create_payment_method(
    payload: PaymentMethodCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.ADMIN, UserRole.MANAGER])),
):
    service = StorefrontService(db)
    return APIResponse(success=True, message="Payment method created", data=service.create_payment_method(payload))


@router.patch("/payment-methods/{pm_id}", response_model=APIResponse[PaymentMethodResponse])
def update_payment_method(
    pm_id: int,
    payload: PaymentMethodUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.ADMIN, UserRole.MANAGER])),
):
    service = StorefrontService(db)
    return APIResponse(success=True, message="Payment method updated", data=service.update_payment_method(pm_id, payload))


@router.delete("/payment-methods/{pm_id}", response_model=APIResponse[dict])
def delete_payment_method(
    pm_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.ADMIN, UserRole.MANAGER])),
):
    service = StorefrontService(db)
    service.delete_payment_method(pm_id)
    return APIResponse(success=True, message="Payment method deleted", data={})


@router.get("/promocodes", response_model=APIResponse[list[PromoCodeResponse]])
def list_promocodes(db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)):
    service = StorefrontService(db)
    return APIResponse(success=True, message="Promo codes retrieved", data=service.list_promocodes())


@router.post("/promocodes", response_model=APIResponse[PromoCodeResponse], status_code=status.HTTP_201_CREATED)
def create_promocode(
    payload: PromoCodeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.ADMIN, UserRole.MANAGER])),
):
    service = StorefrontService(db)
    return APIResponse(success=True, message="Promo code created", data=service.create_promocode(payload))


@router.post("/promocodes/{code}/validate", response_model=APIResponse[dict])
def validate_promocode(
    code: str,
    payload: PromoCodeValidateRequest,
    db: Session = Depends(get_db),
):
    service = StorefrontService(db)
    result = service.validate_promocode(code, payload)
    return APIResponse(success=True, message="Promo code validated", data=result)


@router.get("/promocodes/{pc_id}", response_model=APIResponse[PromoCodeResponse])
def get_promocode(
    pc_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    service = StorefrontService(db)
    promo = service.get_promocode_by_id(pc_id)
    if promo is None:
        raise HTTPException(status_code=404, detail="Promo code not found")
    return APIResponse(success=True, message="Promo code retrieved", data=PromoCodeResponse.model_validate(promo))


@router.patch("/promocodes/{pc_id}", response_model=APIResponse[PromoCodeResponse])
def update_promocode(
    pc_id: int,
    payload: PromoCodeUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.ADMIN, UserRole.MANAGER])),
):
    service = StorefrontService(db)
    return APIResponse(success=True, message="Promo code updated", data=service.update_promocode(pc_id, payload))


@router.delete("/promocodes/{pc_id}", response_model=APIResponse[dict])
def delete_promocode(
    pc_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.ADMIN, UserRole.MANAGER])),
):
    service = StorefrontService(db)
    service.delete_promocode(pc_id)
    return APIResponse(success=True, message="Promo code deleted", data={})


@router.post("/upload", response_model=APIResponse[dict])
async def upload_image(
    file: UploadFile = File(...),
    current_user: User = Depends(require_roles([UserRole.ADMIN, UserRole.MANAGER])),
):
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {ext}")
    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File too large (max 10MB)")
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    filename = f"{uuid.uuid4().hex}{ext}"
    path = os.path.join(UPLOAD_DIR, filename)
    with open(path, "wb") as f:
        f.write(contents)
    return APIResponse(success=True, message="Image uploaded", data={"url": f"/media/uploads/{filename}"})
