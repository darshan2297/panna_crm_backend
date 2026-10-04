from sqlalchemy import Boolean, Column, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.models.base import TimestampMixin


class MenuCategory(Base, TimestampMixin):
    __tablename__ = "menu_categories"

    name = Column(String(100), nullable=False, unique=True, index=True)
    slug = Column(String(120), nullable=False, unique=True, index=True)
    description = Column(Text, nullable=True)
    display_order = Column(Integer, default=0, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False, index=True)

    # Relationships
    items = relationship("MenuItem", back_populates="category", cascade="all, delete-orphan", order_by="MenuItem.display_order")

    def __repr__(self) -> str:
        return f"<MenuCategory(id={self.id}, name='{self.name}', items={len(self.items) if self.items else 0})>"


class MenuItem(Base, TimestampMixin):
    __tablename__ = "menu_items"

    category_id = Column(Integer, ForeignKey("menu_categories.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(150), nullable=False, index=True)
    slug = Column(String(180), nullable=False, unique=True, index=True)
    description = Column(Text, nullable=True)
    is_veg = Column(Boolean, default=False, nullable=False, index=True)
    spice_level = Column(String(30), default="MEDIUM", nullable=False)  # MILD, MEDIUM, SPICY, EXTRA_SPICY
    preparation_time_minutes = Column(Integer, default=25, nullable=False)
    image_url = Column(String(500), nullable=True)
    is_available = Column(Boolean, default=True, nullable=False, index=True)  # In Stock toggle
    is_active = Column(Boolean, default=True, nullable=False, index=True)  # Published toggle
    display_order = Column(Integer, default=0, nullable=False)

    # Relationships
    category = relationship("MenuCategory", back_populates="items")
    portions = relationship("MenuItemPortion", back_populates="menu_item", cascade="all, delete-orphan", order_by="MenuItemPortion.base_price")

    def __repr__(self) -> str:
        return f"<MenuItem(id={self.id}, name='{self.name}', veg={self.is_veg}, available={self.is_available})>"


class MenuItemPortion(Base, TimestampMixin):
    __tablename__ = "menu_item_portions"

    menu_item_id = Column(Integer, ForeignKey("menu_items.id", ondelete="CASCADE"), nullable=False, index=True)
    portion_size = Column(String(50), nullable=False)  # "250g", "500g", "750g", "1kg", "Single", "Regular"
    weight_grams = Column(Integer, nullable=True)  # 250, 500, 750, 1000
    serves_persons = Column(String(50), nullable=True)  # "1 Person", "1-2 Persons", "2-3 Persons"
    cost_price = Column(Float, default=0.0, nullable=False)  # Internal food prep cost
    base_price = Column(Float, nullable=False)  # Direct website / base selling price
    zomato_price = Column(Float, nullable=False)  # Zomato price (+22% default markup)
    swiggy_price = Column(Float, nullable=False)  # Swiggy price (+20% default markup)
    is_available = Column(Boolean, default=True, nullable=False)

    # Relationships
    menu_item = relationship("MenuItem", back_populates="portions")

    def __repr__(self) -> str:
        return f"<MenuItemPortion(id={self.id}, item_id={self.menu_item_id}, size='{self.portion_size}', base={self.base_price})>"
