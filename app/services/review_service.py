"""Review service for managing storefront customer testimonials."""

from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundException
from app.models.review import Review
from app.schemas.review import ReviewCreate, ReviewUpdate


class ReviewService:
    def __init__(self, db: Session):
        self.db = db

    def list_reviews(self, active_only: bool = True) -> list[Review]:
        query = self.db.query(Review)
        if active_only:
            query = query.filter(Review.is_active == True)
        return query.order_by(Review.sort_order, desc(Review.created_at)).all()

    def get_review(self, review_id: int) -> Review:
        review = self.db.query(Review).filter(Review.id == review_id).first()
        if not review:
            raise NotFoundException("Review", review_id)
        return review

    def create_review(self, payload: ReviewCreate) -> Review:
        review = Review(**payload.model_dump())
        self.db.add(review)
        self.db.commit()
        self.db.refresh(review)
        return review

    def update_review(self, review_id: int, payload: ReviewUpdate) -> Review:
        review = self.get_review(review_id)
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(review, field, value)
        self.db.commit()
        self.db.refresh(review)
        return review

    def delete_review(self, review_id: int) -> None:
        review = self.get_review(review_id)
        self.db.delete(review)
        self.db.commit()
