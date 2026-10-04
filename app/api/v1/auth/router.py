from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.dependencies.auth import get_current_active_user
from app.dependencies.database import get_db
from app.models.user import User
from app.schemas.auth import (
    ChangePasswordRequest,
    LoginRequest,
    RefreshTokenRequest,
    TokenResponse,
    UpdateProfileRequest,
)
from app.schemas.common import APIResponse
from app.schemas.user import UserResponse
from app.services.auth_service import AuthService
from app.services.user_service import UserService

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login", response_model=TokenResponse)
def login(request: LoginRequest, db: Session = Depends(get_db)):
    """Authenticate staff/admin and issue JWT access & refresh tokens."""
    service = AuthService(db)
    return service.login(
        identifier=request.username_or_email,
        password=request.password,
    )


@router.post("/refresh", response_model=TokenResponse)
def refresh_token(request: RefreshTokenRequest, db: Session = Depends(get_db)):
    """Refresh expired access token using valid refresh token."""
    service = AuthService(db)
    return service.refresh(refresh_token=request.refresh_token)


@router.get("/me", response_model=APIResponse[UserResponse])
def get_me(current_user: User = Depends(get_current_active_user)):
    """Retrieve profile of currently authenticated user."""
    return APIResponse(
        success=True,
        message="User profile retrieved",
        data=UserResponse.model_validate(current_user),
    )


@router.patch("/profile", response_model=APIResponse[UserResponse])
def update_profile(
    request: UpdateProfileRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Update profile details of currently authenticated user."""
    service = UserService(db)
    updated = service.update_profile(current_user.id, request)
    return APIResponse(
        success=True,
        message="Profile updated successfully",
        data=updated,
    )


@router.post("/change-password", response_model=APIResponse[None])
def change_password(
    request: ChangePasswordRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Change password for currently authenticated user."""
    service = UserService(db)
    service.change_password(current_user.id, request)
    return APIResponse(
        success=True,
        message="Password changed successfully",
        data=None,
    )


@router.post("/logout", response_model=APIResponse[None])
def logout(current_user: User = Depends(get_current_active_user)):
    """Logout endpoint to acknowledge session end."""
    return APIResponse(
        success=True,
        message="Logged out successfully",
        data=None,
    )
