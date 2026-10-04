from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    username_or_email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class TokenPayload(BaseModel):
    sub: str | None = None
    role: str | None = None
    exp: int | None = None
    type: str | None = None


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str = Field(..., min_length=6, description="New password must be at least 6 characters")


class UpdateProfileRequest(BaseModel):
    full_name: str | None = None
    phone: str | None = None
    email: EmailStr | None = None
