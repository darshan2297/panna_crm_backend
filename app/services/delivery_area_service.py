"""DeliveryArea service for managing storefront delivery zones."""

from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundException
from app.models.delivery_area import DeliveryArea
from app.schemas.delivery_area import DeliveryAreaCreate, DeliveryAreaUpdate


class DeliveryAreaService:
    def __init__(self, db: Session):
        self.db = db

    def list_areas(self, active_only: bool = True) -> list[DeliveryArea]:
        query = self.db.query(DeliveryArea)
        if active_only:
            query = query.filter(DeliveryArea.is_active == True)
        return query.order_by(DeliveryArea.sort_order, desc(DeliveryArea.created_at)).all()

    def get_area(self, area_id: int) -> DeliveryArea:
        area = self.db.query(DeliveryArea).filter(DeliveryArea.id == area_id).first()
        if not area:
            raise NotFoundException("DeliveryArea", area_id)
        return area

    def find_by_pincode(self, pincode: str) -> DeliveryArea | None:
        return (
            self.db.query(DeliveryArea)
            .filter(DeliveryArea.pincode == pincode, DeliveryArea.is_active == True)
            .first()
        )

    def create_area(self, payload: DeliveryAreaCreate) -> DeliveryArea:
        area = DeliveryArea(**payload.model_dump())
        self.db.add(area)
        self.db.commit()
        self.db.refresh(area)
        return area

    def update_area(self, area_id: int, payload: DeliveryAreaUpdate) -> DeliveryArea:
        area = self.get_area(area_id)
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(area, field, value)
        self.db.commit()
        self.db.refresh(area)
        return area

    def delete_area(self, area_id: int) -> None:
        area = self.get_area(area_id)
        self.db.delete(area)
        self.db.commit()
