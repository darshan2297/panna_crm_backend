from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "Panna Biryani CRM API"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    API_V1_STR: str = "/api/v1"

    # Security
    SECRET_KEY: str = "panna_super_secret_jwt_key_change_in_production_123456789"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 10080  # 7 days
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    ALGORITHM: str = "HS256"

    # Database
    DATABASE_URL: str = "sqlite:///./panna_crm.db"

    # CORS
    BACKEND_CORS_ORIGINS: list[str] | str = [
        "http://localhost:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
    ]

    # Razorpay Payment Gateway (secret stays server-side only)
    RAZORPAY_KEY_ID: str = ""
    RAZORPAY_SECRET_KEY: str = ""

    # WhatsApp (Gupshup / BSP) — API key stays server-side only
    WHATSAPP_API_KEY: str = ""
    WHATSAPP_API_URL: str = "https://api.gupshup.io/sm/api/v1/msg"
    WHATSAPP_SENDER_ID: str = ""  # Registered Gupshup sender / phone number

    # External CRM base URL used by backend services (for self-calls)
    CRM_BASE_URL: str = "http://localhost:8000"

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: str | list[str]) -> list[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, list):
            return [str(i) for i in v]
        elif isinstance(v, str):
            import json

            try:
                parsed = json.loads(v)
                if isinstance(parsed, list):
                    return [str(i) for i in parsed]
            except Exception:
                pass
        return ["http://localhost:3000", "http://localhost:3001"]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


settings = Settings()
