"""FAQ service for managing storefront frequently asked questions."""

from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundException
from app.models.faq import FAQ
from app.schemas.faq import FAQCreate, FAQUpdate


class FAQService:
    def __init__(self, db: Session):
        self.db = db

    def list_faqs(self, active_only: bool = True, category: str | None = None) -> list[FAQ]:
        query = self.db.query(FAQ)
        if active_only:
            query = query.filter(FAQ.is_active == True)
        if category:
            query = query.filter(FAQ.category == category)
        return query.order_by(FAQ.sort_order, desc(FAQ.created_at)).all()

    def get_faq(self, faq_id: int) -> FAQ:
        faq = self.db.query(FAQ).filter(FAQ.id == faq_id).first()
        if not faq:
            raise NotFoundException("FAQ", faq_id)
        return faq

    def create_faq(self, payload: FAQCreate) -> FAQ:
        faq = FAQ(**payload.model_dump())
        self.db.add(faq)
        self.db.commit()
        self.db.refresh(faq)
        return faq

    def update_faq(self, faq_id: int, payload: FAQUpdate) -> FAQ:
        faq = self.get_faq(faq_id)
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(faq, field, value)
        self.db.commit()
        self.db.refresh(faq)
        return faq

    def delete_faq(self, faq_id: int) -> None:
        faq = self.get_faq(faq_id)
        self.db.delete(faq)
        self.db.commit()
