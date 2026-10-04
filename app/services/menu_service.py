from sqlalchemy import func, or_
from sqlalchemy.orm import Session, joinedload

from app.core.exceptions import ConflictException, NotFoundException
from app.models.menu import MenuCategory, MenuItem, MenuItemPortion
from app.schemas.menu import (
    MenuCategoryCreate,
    MenuCategoryResponse,
    MenuCategoryUpdate,
    MenuItemCreate,
    MenuItemPortionResponse,
    MenuItemResponse,
    MenuItemUpdate,
    MenuSummaryResponse,
    PlatformPriceCalculationResponse,
)
from app.utils.text import slugify


class MenuService:
    def __init__(self, db: Session):
        self.db = db

    # ---------------- Categories ----------------

    def list_categories(self, is_active: bool | None = None) -> list[MenuCategoryResponse]:
        query = self.db.query(MenuCategory, func.count(MenuItem.id).label("items_count")).outerjoin(
            MenuItem, MenuItem.category_id == MenuCategory.id
        )

        if is_active is not None:
            query = query.filter(MenuCategory.is_active == is_active)

        query = query.group_by(MenuCategory.id).order_by(MenuCategory.display_order, MenuCategory.name)
        results = query.all()

        responses = []
        for cat, items_count in results:
            resp = MenuCategoryResponse.model_validate(cat)
            resp.items_count = items_count
            responses.append(resp)
        return responses

    def get_category_by_id(self, category_id: int) -> MenuCategory:
        cat = self.db.query(MenuCategory).filter(MenuCategory.id == category_id).first()
        if not cat:
            raise NotFoundException("Menu category", category_id)
        return cat

    def create_category(self, payload: MenuCategoryCreate) -> MenuCategoryResponse:
        existing = self.db.query(MenuCategory).filter(MenuCategory.name.ilike(payload.name.strip())).first()
        if existing:
            raise ConflictException(f"Category with name '{payload.name}' already exists")

        base_slug = slugify(payload.name)
        slug = base_slug
        count = 1
        while self.db.query(MenuCategory).filter(MenuCategory.slug == slug).first():
            slug = f"{base_slug}-{count}"
            count += 1

        cat = MenuCategory(
            name=payload.name.strip(),
            slug=slug,
            description=payload.description.strip() if payload.description else None,
            display_order=payload.display_order,
            is_active=payload.is_active,
        )
        self.db.add(cat)
        self.db.commit()
        self.db.refresh(cat)

        resp = MenuCategoryResponse.model_validate(cat)
        resp.items_count = 0
        return resp

    def update_category(self, category_id: int, payload: MenuCategoryUpdate) -> MenuCategoryResponse:
        cat = self.get_category_by_id(category_id)

        if payload.name is not None and payload.name.strip() != cat.name:
            cat.name = payload.name.strip()
            cat.slug = slugify(payload.name)
        if payload.description is not None:
            cat.description = payload.description.strip() if payload.description else None
        if payload.display_order is not None:
            cat.display_order = payload.display_order
        if payload.is_active is not None:
            cat.is_active = payload.is_active

        self.db.commit()
        self.db.refresh(cat)

        items_count = self.db.query(MenuItem).filter(MenuItem.category_id == cat.id).count()
        resp = MenuCategoryResponse.model_validate(cat)
        resp.items_count = items_count
        return resp

    def delete_category(self, category_id: int) -> None:
        cat = self.get_category_by_id(category_id)
        self.db.delete(cat)
        self.db.commit()

    # ---------------- Menu Items ----------------

    def _format_item_response(self, item: MenuItem) -> MenuItemResponse:
        portions_resp = []
        starting_price = 0.0
        if item.portions:
            prices = [p.base_price for p in item.portions]
            starting_price = min(prices) if prices else 0.0

            for p in item.portions:
                p_resp = MenuItemPortionResponse.model_validate(p)
                if p.base_price > 0 and p.cost_price > 0:
                    p_resp.profit_margin_percent = round(((p.base_price - p.cost_price) / p.base_price) * 100, 1)
                else:
                    p_resp.profit_margin_percent = 0.0
                portions_resp.append(p_resp)

        return MenuItemResponse(
            id=item.id,
            category_id=item.category_id,
            category_name=item.category.name if item.category else "",
            name=item.name,
            slug=item.slug,
            description=item.description,
            is_veg=item.is_veg,
            spice_level=item.spice_level,
            preparation_time_minutes=item.preparation_time_minutes,
            image_url=item.image_url,
            is_available=item.is_available,
            is_active=item.is_active,
            display_order=item.display_order,
            starting_price=starting_price,
            portions=portions_resp,
            created_at=item.created_at,
            updated_at=item.updated_at,
        )

    def list_items(
        self,
        category_id: int | None = None,
        is_veg: bool | None = None,
        is_available: bool | None = None,
        is_active: bool | None = None,
        search: str | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[MenuItemResponse]:
        query = self.db.query(MenuItem).options(joinedload(MenuItem.category), joinedload(MenuItem.portions))

        if category_id:
            query = query.filter(MenuItem.category_id == category_id)
        if is_veg is not None:
            query = query.filter(MenuItem.is_veg == is_veg)
        if is_available is not None:
            query = query.filter(MenuItem.is_available == is_available)
        if is_active is not None:
            query = query.filter(MenuItem.is_active == is_active)
        if search:
            s = f"%{search.strip()}%"
            query = query.filter(
                or_(
                    MenuItem.name.ilike(s),
                    MenuItem.description.ilike(s),
                )
            )

        query = query.order_by(MenuItem.display_order, MenuItem.name)
        items = query.offset(skip).limit(limit).all()

        return [self._format_item_response(item) for item in items]

    def get_item_by_id(self, item_id: int) -> MenuItem:
        item = (
            self.db.query(MenuItem)
            .options(joinedload(MenuItem.category), joinedload(MenuItem.portions))
            .filter(MenuItem.id == item_id)
            .first()
        )
        if not item:
            raise NotFoundException("Menu item", item_id)
        return item

    def get_item_response(self, item_id: int) -> MenuItemResponse:
        item = self.get_item_by_id(item_id)
        return self._format_item_response(item)

    def create_item(self, payload: MenuItemCreate) -> MenuItemResponse:
        self.get_category_by_id(payload.category_id)

        existing = self.db.query(MenuItem).filter(MenuItem.name.ilike(payload.name.strip())).first()
        if existing:
            raise ConflictException(f"Menu item with name '{payload.name}' already exists")

        base_slug = slugify(payload.name)
        slug = base_slug
        count = 1
        while self.db.query(MenuItem).filter(MenuItem.slug == slug).first():
            slug = f"{base_slug}-{count}"
            count += 1

        item = MenuItem(
            category_id=payload.category_id,
            name=payload.name.strip(),
            slug=slug,
            description=payload.description.strip() if payload.description else None,
            is_veg=payload.is_veg,
            spice_level=payload.spice_level.upper() if payload.spice_level else "MEDIUM",
            preparation_time_minutes=payload.preparation_time_minutes,
            image_url=payload.image_url.strip() if payload.image_url else None,
            is_available=payload.is_available,
            is_active=payload.is_active,
            display_order=payload.display_order,
        )
        self.db.add(item)
        self.db.flush()

        # Add portions
        for p in payload.portions:
            # Auto compute default platform markup if omitted
            zomato_price = p.zomato_price if p.zomato_price is not None else round(p.base_price * 1.22)
            swiggy_price = p.swiggy_price if p.swiggy_price is not None else round(p.base_price * 1.20)

            portion = MenuItemPortion(
                menu_item_id=item.id,
                portion_size=p.portion_size.strip(),
                weight_grams=p.weight_grams,
                serves_persons=p.serves_persons.strip() if p.serves_persons else None,
                cost_price=p.cost_price,
                base_price=p.base_price,
                zomato_price=zomato_price,
                swiggy_price=swiggy_price,
                is_available=p.is_available,
            )
            self.db.add(portion)

        self.db.commit()
        return self.get_item_response(item.id)

    def update_item(self, item_id: int, payload: MenuItemUpdate) -> MenuItemResponse:
        item = self.get_item_by_id(item_id)

        if payload.category_id is not None:
            self.get_category_by_id(payload.category_id)
            item.category_id = payload.category_id
        if payload.name is not None and payload.name.strip() != item.name:
            item.name = payload.name.strip()
            item.slug = slugify(payload.name)
        if payload.description is not None:
            item.description = payload.description.strip() if payload.description else None
        if payload.is_veg is not None:
            item.is_veg = payload.is_veg
        if payload.spice_level is not None:
            item.spice_level = payload.spice_level.upper()
        if payload.preparation_time_minutes is not None:
            item.preparation_time_minutes = payload.preparation_time_minutes
        if payload.image_url is not None:
            item.image_url = payload.image_url.strip() if payload.image_url else None
        if payload.is_available is not None:
            item.is_available = payload.is_available
        if payload.is_active is not None:
            item.is_active = payload.is_active
        if payload.display_order is not None:
            item.display_order = payload.display_order

        # Handle portions update if provided
        if payload.portions is not None:
            # Recreate or update portions
            existing_portions = {p.id: p for p in item.portions}
            kept_ids = set()

            for p_in in payload.portions:
                zomato_price = p_in.zomato_price
                swiggy_price = p_in.swiggy_price

                if p_in.id and p_in.id in existing_portions:
                    # Update existing portion
                    p = existing_portions[p_in.id]
                    kept_ids.add(p.id)
                    if p_in.portion_size is not None:
                        p.portion_size = p_in.portion_size.strip()
                    if p_in.weight_grams is not None:
                        p.weight_grams = p_in.weight_grams
                    if p_in.serves_persons is not None:
                        p.serves_persons = p_in.serves_persons.strip()
                    if p_in.cost_price is not None:
                        p.cost_price = p_in.cost_price
                    if p_in.base_price is not None:
                        p.base_price = p_in.base_price
                        if zomato_price is None:
                            p.zomato_price = round(p.base_price * 1.22)
                        if swiggy_price is None:
                            p.swiggy_price = round(p.base_price * 1.20)
                    if zomato_price is not None:
                        p.zomato_price = zomato_price
                    if swiggy_price is not None:
                        p.swiggy_price = swiggy_price
                    if p_in.is_available is not None:
                        p.is_available = p_in.is_available
                else:
                    # New portion
                    base_price = p_in.base_price or 0.0
                    zom_p = zomato_price if zomato_price is not None else round(base_price * 1.22)
                    swg_p = swiggy_price if swiggy_price is not None else round(base_price * 1.20)
                    new_p = MenuItemPortion(
                        menu_item_id=item.id,
                        portion_size=p_in.portion_size.strip() if p_in.portion_size else "Standard",
                        weight_grams=p_in.weight_grams,
                        serves_persons=p_in.serves_persons.strip() if p_in.serves_persons else None,
                        cost_price=p_in.cost_price or 0.0,
                        base_price=base_price,
                        zomato_price=zom_p,
                        swiggy_price=swg_p,
                        is_available=p_in.is_available if p_in.is_available is not None else True,
                    )
                    self.db.add(new_p)

            # Delete portions not in kept_ids if list was provided
            for p_id, p in existing_portions.items():
                if p_id not in kept_ids:
                    self.db.delete(p)

        self.db.commit()
        return self.get_item_response(item.id)

    def toggle_item_availability(self, item_id: int, is_available: bool) -> MenuItemResponse:
        item = self.get_item_by_id(item_id)
        item.is_available = is_available
        self.db.commit()
        return self.get_item_response(item.id)

    def delete_item(self, item_id: int) -> None:
        item = self.get_item_by_id(item_id)
        self.db.delete(item)
        self.db.commit()

    # ---------------- Summary & Price Calculation ----------------

    def get_menu_summary(self) -> MenuSummaryResponse:
        total_items = self.db.query(MenuItem).count()
        total_categories = self.db.query(MenuCategory).count()
        veg_items_count = self.db.query(MenuItem).filter(MenuItem.is_veg == True).count()
        non_veg_items_count = self.db.query(MenuItem).filter(MenuItem.is_veg == False).count()
        available_items_count = self.db.query(MenuItem).filter(MenuItem.is_available == True).count()
        out_of_stock_count = self.db.query(MenuItem).filter(MenuItem.is_available == False).count()

        return MenuSummaryResponse(
            total_items=total_items,
            total_categories=total_categories,
            veg_items_count=veg_items_count,
            non_veg_items_count=non_veg_items_count,
            available_items_count=available_items_count,
            out_of_stock_count=out_of_stock_count,
        )

    @staticmethod
    def calculate_platform_prices(base_price: float) -> PlatformPriceCalculationResponse:
        return PlatformPriceCalculationResponse(
            base_price=base_price,
            website_price=base_price,
            zomato_price=round(base_price * 1.22),
            swiggy_price=round(base_price * 1.20),
            zomato_markup_percent=22.0,
            swiggy_markup_percent=20.0,
        )
