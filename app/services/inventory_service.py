
from sqlalchemy import case, func
from sqlalchemy.orm import Session, joinedload

from app.core.exceptions import BadRequestException, ConflictException, NotFoundException
from app.core.logging import logger
from app.models.inventory import (
    InventoryItem,
    InventoryTransaction,
    InventoryTransactionType,
)
from app.schemas.inventory import (
    CategoryValuation,
    InventoryItemCreate,
    InventoryItemDetailResponse,
    InventoryItemResponse,
    InventoryItemUpdate,
    InventorySummaryResponse,
    InventoryTransactionCreate,
    InventoryTransactionResponse,
)
from app.utils.pagination import calc_pages
from app.utils.sku import generate_sku
from app.utils.stock import normalize_status_filter


class InventoryService:
    def __init__(self, db: Session):
        self.db = db

    def _generate_sku(self, name: str, category: str) -> str:
        """Generate a clean unique SKU like ING-GRA-012."""
        return generate_sku(
            self.db,
            prefix="ING",
            category=category,
            model=InventoryItem,
            category_column=InventoryItem.category,
            sku_column=InventoryItem.sku,
        )

    def _format_transaction_response(self, tx: InventoryTransaction) -> InventoryTransactionResponse:
        item = tx.item
        user = tx.performed_by
        return InventoryTransactionResponse(
            id=tx.id,
            inventory_item_id=tx.inventory_item_id,
            item_name=item.name if item else None,
            item_sku=item.sku if item else None,
            item_unit=item.unit if item else None,
            item_category=item.category if item else None,
            transaction_type=tx.transaction_type,
            quantity=tx.quantity,
            stock_before=tx.stock_before,
            stock_after=tx.stock_after,
            unit_price=tx.unit_price,
            total_cost=tx.total_cost,
            reference_no=tx.reference_no,
            notes=tx.notes,
            performed_by_id=tx.performed_by_id,
            performed_by_name=user.full_name if user else None,
            created_at=tx.created_at,
        )

    def _format_item_response(self, item: InventoryItem) -> InventoryItemResponse:
        return InventoryItemResponse(
            id=item.id,
            name=item.name,
            sku=item.sku,
            category=item.category,
            unit=item.unit,
            current_stock=round(item.current_stock, 2),
            minimum_stock=round(item.minimum_stock, 2),
            reorder_level=round(item.reorder_level, 2),
            purchase_price=round(item.purchase_price, 2),
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

    def list_items(
        self,
        category: str | None = None,
        status_filter: str | None = None,
        search: str | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[InventoryItemResponse], int, int]:
        """List inventory items with comprehensive filters, sorting, and pagination."""
        query = self.db.query(InventoryItem).filter(InventoryItem.is_active == True)

        if category and category.upper() != "ALL":
            query = query.filter(InventoryItem.category == category.upper())

        if search and search.strip():
            term = f"%{search.strip()}%"
            query = query.filter(
                (InventoryItem.name.ilike(term)) | (InventoryItem.sku.ilike(term)) | (InventoryItem.supplier.ilike(term))
            )

        if status_filter:
            status_upper = normalize_status_filter(status_filter) or status_filter.upper()
            if status_upper == "OUT_OF_STOCK":
                query = query.filter(InventoryItem.current_stock <= 0.0)
            elif status_upper == "CRITICAL":
                query = query.filter(InventoryItem.current_stock <= InventoryItem.minimum_stock)
            elif status_upper == "LOW_STOCK":
                query = query.filter(
                    InventoryItem.current_stock <= InventoryItem.reorder_level,
                    InventoryItem.current_stock > InventoryItem.minimum_stock,
                )
            elif status_upper == "IN_STOCK":
                query = query.filter(InventoryItem.current_stock > InventoryItem.reorder_level)

        # Ordering priority: critical items first, then low stock, then alphabetical
        query = query.order_by(
            case(
                (InventoryItem.current_stock <= InventoryItem.minimum_stock, 1),
                (InventoryItem.current_stock <= InventoryItem.reorder_level, 2),
                else_=3,
            ),
            InventoryItem.name.asc(),
        )

        total = query.count()
        pages = calc_pages(total, page_size)
        items = query.offset((page - 1) * page_size).limit(page_size).all()

        return [self._format_item_response(it) for it in items], total, pages

    def get_item(self, item_id: int) -> InventoryItemDetailResponse:
        item = (
            self.db.query(InventoryItem)
            .options(joinedload(InventoryItem.transactions).joinedload(InventoryTransaction.performed_by))
            .filter(InventoryItem.id == item_id, InventoryItem.is_active == True)
            .first()
        )
        if not item:
            raise NotFoundException("Inventory item", item_id)

        recent_txs = [self._format_transaction_response(tx) for tx in item.transactions[:15]]
        resp = self._format_item_response(item)
        return InventoryItemDetailResponse(
            **resp.model_dump(),
            recent_transactions=recent_txs,
        )

    def create_item(self, data: InventoryItemCreate, user_id: int | None = None) -> InventoryItemResponse:
        # Check name conflict
        existing_name = (
            self.db.query(InventoryItem)
            .filter(func.lower(InventoryItem.name) == data.name.strip().lower(), InventoryItem.is_active == True)
            .first()
        )
        if existing_name:
            raise ConflictException(f"An active inventory item named '{data.name.strip()}' already exists")

        sku = data.sku.strip() if data.sku and data.sku.strip() else self._generate_sku(data.name, data.category)
        existing_sku = (
            self.db.query(InventoryItem)
            .filter(InventoryItem.sku == sku, InventoryItem.is_active == True)
            .first()
        )
        if existing_sku:
            raise ConflictException(f"SKU '{sku}' is already assigned to another item")

        item = InventoryItem(
            name=data.name.strip(),
            sku=sku,
            category=data.category.upper(),
            unit=data.unit.lower(),
            current_stock=data.current_stock,
            minimum_stock=data.minimum_stock,
            reorder_level=data.reorder_level,
            purchase_price=data.purchase_price,
            supplier=data.supplier.strip() if data.supplier else None,
            storage_location=data.storage_location.strip() if data.storage_location else None,
            description=data.description.strip() if data.description else None,
            is_active=data.is_active,
        )
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)

        # If item was added with initial stock > 0, log an initial stock transaction
        if data.current_stock > 0:
            init_tx = InventoryTransaction(
                inventory_item_id=item.id,
                transaction_type=InventoryTransactionType.STOCK_IN.value,
                quantity=data.current_stock,
                stock_before=0.0,
                stock_after=data.current_stock,
                unit_price=data.purchase_price,
                total_cost=round(data.current_stock * data.purchase_price, 2),
                reference_no="INITIAL-SETUP",
                notes="Initial stock quantity recorded at item creation",
                performed_by_id=user_id,
            )
            self.db.add(init_tx)
            self.db.commit()

        logger.info(f"Created inventory item #{item.id} ({item.name}, SKU: {item.sku})")
        return self._format_item_response(item)

    def update_item(self, item_id: int, data: InventoryItemUpdate, user_id: int | None = None) -> InventoryItemResponse:
        item = self.db.query(InventoryItem).filter(InventoryItem.id == item_id, InventoryItem.is_active == True).first()
        if not item:
            raise NotFoundException("Inventory item", item_id)

        if data.name and data.name.strip().lower() != item.name.lower():
            conflict = (
                self.db.query(InventoryItem)
                .filter(
                    func.lower(InventoryItem.name) == data.name.strip().lower(),
                    InventoryItem.id != item_id,
                    InventoryItem.is_active == True,
                )
                .first()
            )
            if conflict:
                raise ConflictException(f"An active item named '{data.name.strip()}' already exists")
            item.name = data.name.strip()

        if data.sku and data.sku.strip() != item.sku:
            sku_conflict = (
                self.db.query(InventoryItem)
                .filter(InventoryItem.sku == data.sku.strip(), InventoryItem.id != item_id, InventoryItem.is_active == True)
                .first()
            )
            if sku_conflict:
                raise ConflictException(f"SKU '{data.sku.strip()}' is already assigned to another item")
            item.sku = data.sku.strip()

        if data.category is not None:
            item.category = data.category.upper()
        if data.unit is not None:
            item.unit = data.unit.lower()
        if data.minimum_stock is not None:
            item.minimum_stock = data.minimum_stock
        if data.reorder_level is not None:
            item.reorder_level = data.reorder_level
        if data.purchase_price is not None:
            item.purchase_price = data.purchase_price
        if data.supplier is not None:
            item.supplier = data.supplier.strip() or None
        if data.storage_location is not None:
            item.storage_location = data.storage_location.strip() or None
        if data.description is not None:
            item.description = data.description.strip() or None
        if data.is_active is not None:
            item.is_active = data.is_active

        # If current_stock was explicitly changed via item update, record audit trail
        if data.current_stock is not None and abs(data.current_stock - item.current_stock) > 1e-4:
            stock_before = item.current_stock
            stock_after = data.current_stock
            delta = abs(stock_after - stock_before)
            item.current_stock = stock_after

            audit_tx = InventoryTransaction(
                inventory_item_id=item.id,
                transaction_type=InventoryTransactionType.AUDIT_CORRECTION.value,
                quantity=round(delta, 2),
                stock_before=stock_before,
                stock_after=stock_after,
                unit_price=item.purchase_price,
                total_cost=round(delta * item.purchase_price, 2),
                reference_no="MANUAL-EDIT",
                notes=f"Stock updated from {stock_before}{item.unit} to {stock_after}{item.unit} via item edit",
                performed_by_id=user_id,
            )
            self.db.add(audit_tx)

        self.db.commit()
        self.db.refresh(item)
        return self._format_item_response(item)

    def delete_item(self, item_id: int) -> dict[str, str]:
        item = self.db.query(InventoryItem).filter(InventoryItem.id == item_id, InventoryItem.is_active == True).first()
        if not item:
            raise NotFoundException("Inventory item", item_id)

        item.is_active = False
        self.db.commit()
        logger.info(f"Soft-deleted inventory item #{item_id} ({item.name})")
        return {"message": f"Inventory item '{item.name}' has been deactivated successfully"}

    def adjust_stock(
        self, item_id: int, data: InventoryTransactionCreate, user_id: int | None = None
    ) -> InventoryTransactionResponse:
        """Process Stock-In, Stock-Out, Wastage, or Audit Correction."""
        item = self.db.query(InventoryItem).filter(InventoryItem.id == item_id, InventoryItem.is_active == True).first()
        if not item:
            raise NotFoundException("Inventory item", item_id)

        if data.quantity <= 0:
            raise BadRequestException("Transaction quantity must be greater than zero")

        stock_before = item.current_stock
        tx_type = data.transaction_type.value

        if tx_type == InventoryTransactionType.STOCK_IN.value:
            stock_after = stock_before + data.quantity
        elif tx_type in (InventoryTransactionType.STOCK_OUT.value, InventoryTransactionType.WASTAGE.value):
            if data.quantity > stock_before:
                raise BadRequestException(
                    f"Insufficient stock for {item.name}. Available: {stock_before} {item.unit}, "
                    f"requested deduction: {data.quantity} {item.unit}."
                )
            stock_after = stock_before - data.quantity
        elif tx_type == InventoryTransactionType.AUDIT_CORRECTION.value:
            # For audit correction, data.quantity is treated as the new physical stock count
            stock_after = data.quantity
        else:
            raise BadRequestException(f"Unsupported transaction type: {tx_type}")

        unit_price = data.unit_price if data.unit_price is not None else item.purchase_price
        total_cost = round(data.quantity * unit_price, 2)

        # Update item stock
        item.current_stock = round(stock_after, 2)
        # If stock in provided a new unit purchase price, update default purchase price
        if tx_type == InventoryTransactionType.STOCK_IN.value and data.unit_price is not None and data.unit_price > 0:
            item.purchase_price = data.unit_price

        tx = InventoryTransaction(
            inventory_item_id=item.id,
            transaction_type=tx_type,
            quantity=data.quantity,
            stock_before=stock_before,
            stock_after=stock_after,
            unit_price=unit_price,
            total_cost=total_cost,
            reference_no=data.reference_no.strip() if data.reference_no else None,
            notes=data.notes.strip() if data.notes else None,
            performed_by_id=user_id,
        )
        self.db.add(tx)
        self.db.commit()
        self.db.refresh(tx)
        self.db.refresh(item)

        logger.info(
            f"Stock adjustment: {tx_type} of {data.quantity} {item.unit} on Item #{item.id} "
            f"({stock_before} -> {stock_after})"
        )
        return self._format_transaction_response(tx)

    def list_transactions(
        self,
        item_id: int | None = None,
        transaction_type: str | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[InventoryTransactionResponse], int, int]:
        """List paginated inventory transactions across all or specific items."""
        query = (
            self.db.query(InventoryTransaction)
            .options(joinedload(InventoryTransaction.item), joinedload(InventoryTransaction.performed_by))
        )

        if item_id:
            query = query.filter(InventoryTransaction.inventory_item_id == item_id)

        if transaction_type and transaction_type.upper() != "ALL":
            query = query.filter(InventoryTransaction.transaction_type == transaction_type.upper())

        query = query.order_by(InventoryTransaction.created_at.desc())

        total = query.count()
        pages = calc_pages(total, page_size)
        txs = query.offset((page - 1) * page_size).limit(page_size).all()

        return [self._format_transaction_response(tx) for tx in txs], total, pages

    def get_summary(self) -> InventorySummaryResponse:
        """Calculate inventory operational metrics and category valuations."""
        items = self.db.query(InventoryItem).filter(InventoryItem.is_active == True).all()

        total_items = len(items)
        out_of_stock = sum(1 for it in items if it.current_stock <= 0.0)
        critical_stock = sum(1 for it in items if 0.0 < it.current_stock <= it.minimum_stock)
        low_stock = sum(1 for it in items if it.minimum_stock < it.current_stock <= it.reorder_level)
        in_stock = sum(1 for it in items if it.current_stock > it.reorder_level)
        total_value = sum(it.current_stock * it.purchase_price for it in items)

        # Category breakdowns
        cat_map: dict[str, dict[str, float]] = {}
        for it in items:
            cat = it.category or "OTHER"
            if cat not in cat_map:
                cat_map[cat] = {"count": 0, "val": 0.0}
            cat_map[cat]["count"] += 1
            cat_map[cat]["val"] += it.current_stock * it.purchase_price

        category_valuations = [
            CategoryValuation(
                category=cat,
                item_count=int(stats["count"]),
                total_valuation=round(stats["val"], 2),
            )
            for cat, stats in sorted(cat_map.items())
        ]

        return InventorySummaryResponse(
            total_items=total_items,
            in_stock_items=in_stock,
            low_stock_items=low_stock,
            critical_stock_items=critical_stock,
            out_of_stock_items=out_of_stock,
            total_inventory_value_inr=round(total_value, 2),
            category_valuations=category_valuations,
        )
