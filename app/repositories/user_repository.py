
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.user import User
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    def __init__(self, db: Session):
        super().__init__(User, db)

    def get_by_email(self, email: str) -> User | None:
        return self.db.query(User).filter(User.email == email).first()

    def get_by_username(self, username: str) -> User | None:
        return self.db.query(User).filter(User.username == username).first()

    def get_by_username_or_email(self, identifier: str) -> User | None:
        return self.db.query(User).filter(
            or_(User.username == identifier, User.email == identifier)
        ).first()

    def get_filtered_users(
        self,
        skip: int = 0,
        limit: int = 50,
        role: str | None = None,
        is_active: bool | None = None,
        search: str | None = None,
    ) -> tuple[list[User], int]:
        query = self.db.query(User)

        if role:
            query = query.filter(User.role == role.upper())

        if is_active is not None:
            query = query.filter(User.is_active == is_active)

        if search:
            search_pattern = f"%{search}%"
            query = query.filter(
                or_(
                    User.username.ilike(search_pattern),
                    User.email.ilike(search_pattern),
                    User.full_name.ilike(search_pattern),
                    User.phone.ilike(search_pattern),
                )
            )

        total = query.count()
        items = query.order_by(User.id.desc()).offset(skip).limit(limit).all()
        return items, total
