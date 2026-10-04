from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.core.exceptions import BadRequestException, ConflictException, NotFoundException
from app.core.logging import logger
from app.models.packaging import (
    PackagingConsumptionRule,
    PackagingItem,
    PackagingTransaction,
)
from app.schemas.packaging import (
    CategoryPackagingValuation,
    PackagingConsumptionRuleCreate,
    PackagingConsumptionRuleResponse,
    PackagingItemConsumptionEstimate,
    PackagingItemCreate,
    PackagingItemDetailResponse,
    PackagingItemResponse,
    PackagingItemUpdate,
    PackagingOrderSimulationItem,
    PackagingOrderSimulationResponse,
    PackagingSummaryResponse,
    PackagingTransactionCreate,
    PackagingTransactionResponse,
)
from app.utils.sku import generate_sku

if TYPE_CHECKING:
    from app.models.user import User


class PackagingService:
    def __init__(self, db: Session):
        self.db = db

    def _generate_sku(self, name: str, category: str) -> str:
        """Generate a clean unique SKU like PKG-CON-001, PKG-BAG-002."""
        return generate_sku(
            self.db,
            prefix="PKG",
            category=category,
            model=PackagingItem,
            category_column=PackagingItem.category,
            sku_column=PackagingItem.sku,
            use_category_map=True,
        )

    def _format_transaction_response(self, tx: PackagingTransaction) -> PackagingTransactionResponse:
        item = tx.item
        user = tx.performed_by
        return PackagingTransactionResponse(
            id=tx.id,
            packaging_item_id=tx.packaging_item_id,
            item_name=item.name if item else None,
            item_sku=item.sku if item else None,
            item_unit=item.unit if item else None,
            item_category=item.category if item else None,
            transaction_type=tx.transaction_type,
            quantity=tx.quantity,
            stock_before=tx.stock_before,
            stock_after=tx.stock_after,
            unit_cost=tx.unit_cost,
            total_cost=tx.total_cost,
            order_id=tx.order_id,
            reference_no=tx.reference_no,
            notes=tx.notes,
            performed_by_id=tx.performed_by_id,
            performed_by_name=user.full_name if user else None,
            created_at=tx.created_at,
        )

    def _format_item_response(self, item: PackagingItem) -> PackagingItemResponse:
        return PackagingItemResponse(
            id=item.id,
            name=item.name,
            sku=item.sku,
            category=item.category,
            material=item.material,
            capacity=item.capacity,
            unit=item.unit,
            current_stock=round(item.current_stock, 2),
            minimum_stock=round(item.minimum_stock, 2),
            reorder_level=round(item.reorder_level, 2),
            purchase_cost=round(item.purchase_cost, 2),
            supplier=item.supplier,
            storage_location=item.storage_location,
            description=item.description,
            is_active=item.is_active,
            is_low_stock=item.is_low_stock,
            is_critical_stock=item.is_critical_stock,
            total_valuation=item.total_valuation,
            created_at=item.created_at,
            updated_at=item.updated_at,
        )

    def _format_rule_response(self, rule: PackagingConsumptionRule) -> PackagingConsumptionRuleResponse:
        item = rule.packaging_item
        return PackagingConsumptionRuleResponse(
            id=rule.id,
            dish_category=rule.dish_category,
            portion_size=rule.portion_size,
            packaging_item_id=rule.packaging_item_id,
            packaging_item_name=item.name if item else None,
            packaging_item_sku=item.sku if item else None,
            packaging_item_unit=item.unit if item else None,
            packaging_item_cost=item.purchase_cost if item else None,
            quantity_per_order_unit=rule.quantity_per_order_unit,
            description=rule.description,
            is_active=rule.is_active,
            created_at=rule.created_at,
        )

    def get_summary(self) -> PackagingSummaryResponse:
        items = self.db.query(PackagingItem).filter(PackagingItem.is_active == True).all()
        total_items = len(items)
        in_stock_items = 0
        low_stock_items = 0
        critical_stock_items = 0
        out_of_stock_items = 0
        total_val = 0.0

        cat_map: dict[str, dict[str, float]] = {}

        for it in items:
            val = it.total_valuation
            total_val += val

            if it.category not in cat_map:
                cat_map[it.category] = {"count": 0, "val": 0.0}
            cat_map[it.category]["count"] += 1
            cat_map[it.category]["val"] += val

            if it.current_stock <= 0:
                out_of_stock_items += 1
            elif it.is_critical_stock:
                critical_stock_items += 1
            elif it.is_low_stock:
                low_stock_items += 1
            else:
                in_stock_items += 1

        cat_valuations = [
            CategoryPackagingValuation(
                category=cat,
                item_count=int(data["count"]),
                total_valuation=round(data["val"], 2),
            )
            for cat, data in sorted(cat_map.items())
        ]

        # Daily consumption metrics (transactions from start of today)
        today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        daily_txs = (
            self.db.query(PackagingTransaction)
            .filter(
                PackagingTransaction.created_at >= today_start,
                PackagingTransaction.transaction_type.in_(["STOCK_OUT", "ORDER_CONSUMPTION", "WASTAGE"]),
            )
            .all()
        )
        daily_units = sum(tx.quantity for tx in daily_txs)
        daily_cost = sum(tx.total_cost or 0.0 for tx in daily_txs)

        return PackagingSummaryResponse(
            total_items=total_items,
            in_stock_items=in_stock_items,
            low_stock_items=low_stock_items,
            critical_stock_items=critical_stock_items,
            out_of_stock_items=out_of_stock_items,
            total_packaging_value_inr=round(total_val, 2),
            category_valuations=cat_valuations,
            daily_consumption_units=round(daily_units, 2),
            daily_consumption_cost_inr=round(daily_cost, 2),
        )

    def list_items(
        self,
        category: str | None = None,
        stock_status: str | None = None,
        material: str | None = None,
        search: str | None = None,
        page: int = 1,
        page_size: int = 25,
    ) -> tuple[list[PackagingItemResponse], int]:
        query = self.db.query(PackagingItem).filter(PackagingItem.is_active == True)

        if category and category.upper() != "ALL":
            query = query.filter(PackagingItem.category == category.upper())

        if material and material.upper() != "ALL":
            query = query.filter(PackagingItem.material.ilike(f"%{material}%"))

        if search and search.strip():
            kw = f"%{search.strip()}%"
            query = query.filter(
                (PackagingItem.name.ilike(kw))
                | (PackagingItem.sku.ilike(kw))
                | (PackagingItem.supplier.ilike(kw))
                | (PackagingItem.description.ilike(kw))
            )

        if stock_status:
            status_upper = stock_status.upper()
            if status_upper == "OUT_OF_STOCK":
                query = query.filter(PackagingItem.current_stock <= 0)
            elif status_upper == "CRITICAL":
                query = query.filter(
                    PackagingItem.current_stock > 0,
                    PackagingItem.current_stock <= PackagingItem.minimum_stock,
                )
            elif status_upper == "LOW_STOCK":
                query = query.filter(
                    PackagingItem.current_stock > PackagingItem.minimum_stock,
                    PackagingItem.current_stock <= PackagingItem.reorder_level,
                )
            elif status_upper == "IN_STOCK":
                query = query.filter(PackagingItem.current_stock > PackagingItem.reorder_level)

        total = query.count()
        offset = (page - 1) * page_size
        items = query.order_by(PackagingItem.category, PackagingItem.name).offset(offset).limit(page_size).all()
        return [self._format_item_response(it) for it in items], total

    def create_item(self, payload: PackagingItemCreate) -> PackagingItemResponse:
        existing = (
            self.db.query(PackagingItem)
            .filter(
                func.lower(PackagingItem.name) == payload.name.strip().lower(),
                PackagingItem.is_active == True,
            )
            .first()
        )
        if existing:
            raise ConflictException(f"Packaging item with name '{payload.name}' already exists (SKU: {existing.sku}).",)

        sku = payload.sku.strip() if payload.sku and payload.sku.strip() else self._generate_sku(payload.name, payload.category)
        dup_sku = self.db.query(PackagingItem).filter(PackagingItem.sku == sku).first()
        if dup_sku:
            sku = self._generate_sku(payload.name, payload.category)

        new_item = PackagingItem(
            name=payload.name.strip(),
            sku=sku,
            category=payload.category.upper(),
            material=payload.material.strip(),
            capacity=payload.capacity.strip() if payload.capacity else None,
            unit=payload.unit.strip().lower(),
            current_stock=payload.current_stock,
            minimum_stock=payload.minimum_stock,
            reorder_level=payload.reorder_level,
            purchase_cost=payload.purchase_cost,
            supplier=payload.supplier.strip() if payload.supplier else None,
            storage_location=payload.storage_location.strip() if payload.storage_location else None,
            description=payload.description.strip() if payload.description else None,
            is_active=True,
        )
        self.db.add(new_item)
        self.db.flush()

        if new_item.current_stock > 0:
            init_tx = PackagingTransaction(
                packaging_item_id=new_item.id,
                transaction_type="STOCK_IN",
                quantity=new_item.current_stock,
                stock_before=0.0,
                stock_after=new_item.current_stock,
                unit_cost=new_item.purchase_cost,
                total_cost=round(new_item.current_stock * new_item.purchase_cost, 2),
                reference_no="INIT_STOCK",
                notes="Opening initial stock on packaging item creation",
            )
            self.db.add(init_tx)

        self.db.commit()
        self.db.refresh(new_item)
        logger.info(f"Created packaging item {new_item.name} with SKU {new_item.sku}")
        return self._format_item_response(new_item)

    def get_item(self, item_id: int) -> PackagingItemDetailResponse:
        item = (
            self.db.query(PackagingItem)
            .options(joinedload(PackagingItem.transactions).joinedload(PackagingTransaction.performed_by))
            .filter(PackagingItem.id == item_id, PackagingItem.is_active == True)
            .first()
        )
        if not item:
            raise NotFoundException("Packaging item")

        base_resp = self._format_item_response(item)
        recent_txs = [self._format_transaction_response(tx) for tx in item.transactions[:10]]
        return PackagingItemDetailResponse(**base_resp.model_dump(), recent_transactions=recent_txs)

    def update_item(self, item_id: int, payload: PackagingItemUpdate) -> PackagingItemResponse:
        item = self.db.query(PackagingItem).filter(PackagingItem.id == item_id, PackagingItem.is_active == True).first()
        if not item:
            raise NotFoundException("Packaging item")

        update_dict = payload.model_dump(exclude_unset=True)

        if "name" in update_dict and update_dict["name"]:
            new_name = update_dict["name"].strip()
            dup = (
                self.db.query(PackagingItem)
                .filter(
                    func.lower(PackagingItem.name) == new_name.lower(),
                    PackagingItem.id != item_id,
                    PackagingItem.is_active == True,
                )
                .first()
            )
            if dup:
                raise ConflictException(f"Another packaging item already uses name '{new_name}'.",)
            item.name = new_name

        if "sku" in update_dict and update_dict["sku"]:
            new_sku = update_dict["sku"].strip()
            dup_sku = (
                self.db.query(PackagingItem)
                .filter(PackagingItem.sku == new_sku, PackagingItem.id != item_id)
                .first()
            )
            if dup_sku:
                raise ConflictException(f"Another item with SKU '{new_sku}' already exists.",)
            item.sku = new_sku

        for field in [
            "category",
            "material",
            "capacity",
            "unit",
            "current_stock",
            "minimum_stock",
            "reorder_level",
            "purchase_cost",
            "supplier",
            "storage_location",
            "description",
            "is_active",
        ]:
            if field in update_dict:
                setattr(item, field, update_dict[field])

        self.db.commit()
        self.db.refresh(item)
        return self._format_item_response(item)

    def delete_item(self, item_id: int) -> bool:
        item = self.db.query(PackagingItem).filter(PackagingItem.id == item_id, PackagingItem.is_active == True).first()
        if not item:
            raise NotFoundException("Packaging item")
        item.is_active = False
        self.db.commit()
        return True

    def adjust_stock(
        self,
        item_id: int,
        payload: PackagingTransactionCreate,
        current_user: Optional[User] = None,
    ) -> tuple[PackagingItemResponse, PackagingTransactionResponse]:
        item = self.db.query(PackagingItem).filter(PackagingItem.id == item_id, PackagingItem.is_active == True).first()
        if not item:
            raise NotFoundException("Packaging item")

        stock_before = item.current_stock
        tx_type = payload.transaction_type.value
        qty = payload.quantity
        unit_cost = payload.unit_cost if payload.unit_cost is not None else item.purchase_cost
        total_cost = round(qty * unit_cost, 2)

        if tx_type == "STOCK_IN":
            stock_after = stock_before + qty
        elif tx_type in ["STOCK_OUT", "ORDER_CONSUMPTION", "WASTAGE"]:
            if qty > stock_before:
                raise BadRequestException(f"Insufficient stock for '{item.name}'. Available: {stock_before} {item.unit}, attempted: {qty} {item.unit}.",)
            stock_after = stock_before - qty
        elif tx_type == "AUDIT_CORRECTION":
            stock_after = qty
            total_cost = round(abs(stock_after - stock_before) * unit_cost, 2)
        else:
            raise BadRequestException(f"Invalid transaction type: {tx_type}")

        item.current_stock = stock_after

        tx = PackagingTransaction(
            packaging_item_id=item.id,
            transaction_type=tx_type,
            quantity=qty,
            stock_before=stock_before,
            stock_after=stock_after,
            unit_cost=unit_cost,
            total_cost=total_cost,
            order_id=payload.order_id,
            reference_no=payload.reference_no,
            notes=payload.notes,
            performed_by_id=current_user.id if current_user else None,
        )
        self.db.add(tx)
        self.db.commit()
        self.db.refresh(item)
        self.db.refresh(tx)

        return self._format_item_response(item), self._format_transaction_response(tx)

    def list_transactions(
        self,
        packaging_item_id: int | None = None,
        transaction_type: str | None = None,
        page: int = 1,
        page_size: int = 25,
    ) -> tuple[list[PackagingTransactionResponse], int]:
        query = (
            self.db.query(PackagingTransaction)
            .options(
                joinedload(PackagingTransaction.item),
                joinedload(PackagingTransaction.performed_by),
            )
        )

        if packaging_item_id:
            query = query.filter(PackagingTransaction.packaging_item_id == packaging_item_id)

        if transaction_type and transaction_type.upper() != "ALL":
            query = query.filter(PackagingTransaction.transaction_type == transaction_type.upper())

        total = query.count()
        offset = (page - 1) * page_size
        txs = query.order_by(PackagingTransaction.created_at.desc()).offset(offset).limit(page_size).all()
        return [self._format_transaction_response(tx) for tx in txs], total

    def list_consumption_rules(self) -> list[PackagingConsumptionRuleResponse]:
        rules = (
            self.db.query(PackagingConsumptionRule)
            .options(joinedload(PackagingConsumptionRule.packaging_item))
            .filter(PackagingConsumptionRule.is_active == True)
            .order_by(PackagingConsumptionRule.dish_category, PackagingConsumptionRule.portion_size)
            .all()
        )
        return [self._format_rule_response(r) for r in rules]

    def create_consumption_rule(self, payload: PackagingConsumptionRuleCreate) -> PackagingConsumptionRuleResponse:
        item = self.db.query(PackagingItem).filter(PackagingItem.id == payload.packaging_item_id, PackagingItem.is_active == True).first()
        if not item:
            raise NotFoundException("Packaging item")

        rule = PackagingConsumptionRule(
            dish_category=payload.dish_category.strip() if payload.dish_category else None,
            portion_size=payload.portion_size.strip() if payload.portion_size else None,
            packaging_item_id=payload.packaging_item_id,
            quantity_per_order_unit=payload.quantity_per_order_unit,
            description=payload.description.strip() if payload.description else None,
            is_active=True,
        )
        self.db.add(rule)
        self.db.commit()
        self.db.refresh(rule)
        return self._format_rule_response(rule)

    def delete_consumption_rule(self, rule_id: int) -> bool:
        rule = self.db.query(PackagingConsumptionRule).filter(PackagingConsumptionRule.id == rule_id).first()
        if not rule:
            raise NotFoundException("Packaging rule")
        rule.is_active = False
        self.db.commit()
        return True

    def simulate_order_consumption(
        self, items: list[PackagingOrderSimulationItem]
    ) -> PackagingOrderSimulationResponse:
        rules = (
            self.db.query(PackagingConsumptionRule)
            .options(joinedload(PackagingConsumptionRule.packaging_item))
            .filter(PackagingConsumptionRule.is_active == True)
            .all()
        )

        consumed_map: dict[int, dict] = {}

        for ordered in items:
            cat_norm = ordered.dish_category.strip().lower()
            portion_norm = ordered.portion_size.strip().lower() if ordered.portion_size else None
            qty = ordered.quantity

            for rule in rules:
                rule_cat = rule.dish_category.strip().lower() if rule.dish_category else "all_orders"
                rule_portion = rule.portion_size.strip().lower() if rule.portion_size else "all"

                cat_match = rule_cat in ["all_orders", "all", cat_norm]
                portion_match = rule_portion in ["all", portion_norm] if portion_norm else True

                if cat_match and portion_match:
                    pkg_item = rule.packaging_item
                    if not pkg_item or not pkg_item.is_active:
                        continue

                    pkg_id = pkg_item.id
                    units_needed = rule.quantity_per_order_unit * qty

                    if pkg_id not in consumed_map:
                        consumed_map[pkg_id] = {
                            "packaging_item_id": pkg_id,
                            "item_name": pkg_item.name,
                            "item_sku": pkg_item.sku,
                            "category": pkg_item.category,
                            "unit": pkg_item.unit,
                            "units_consumed": 0.0,
                            "unit_cost": pkg_item.purchase_cost,
                            "total_cost": 0.0,
                        }
                    consumed_map[pkg_id]["units_consumed"] += units_needed
                    consumed_map[pkg_id]["total_cost"] = round(
                        consumed_map[pkg_id]["units_consumed"] * consumed_map[pkg_id]["unit_cost"], 2
                    )

        estimates = [
            PackagingItemConsumptionEstimate(
                packaging_item_id=d["packaging_item_id"],
                item_name=d["item_name"],
                item_sku=d["item_sku"],
                category=d["category"],
                unit=d["unit"],
                units_consumed=round(d["units_consumed"], 2),
                unit_cost=round(d["unit_cost"], 2),
                total_cost=round(d["total_cost"], 2),
            )
            for d in consumed_map.values()
        ]

        total_units = round(sum(e.units_consumed for e in estimates), 2)
        total_cost = round(sum(e.total_cost for e in estimates), 2)

        return PackagingOrderSimulationResponse(
            consumed_items=estimates,
            total_packaging_units=total_units,
            total_packaging_cost_inr=total_cost,
        )
