from datetime import datetime

from pydantic import BaseModel


class AuditLogRead(BaseModel):
    id: int
    user_id: int | None = None
    user_email: str | None = None
    action: str
    entity_type: str
    entity_id: str | None = None
    details: str | None = None
    ip_address: str | None = None
    created_at: datetime

    class Config:
        from_attributes = True


class AuditLogFilter(BaseModel):
    action: str | None = None
    entity_type: str | None = None
    search: str | None = None
    user_email: str | None = None
    page: int = 1
    page_size: int = 20


class AuditStats(BaseModel):
    total_logs: int
    today_logs: int
    by_action: dict[str, int]
    by_entity: dict[str, int]
