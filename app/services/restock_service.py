import random
from datetime import UTC, datetime

from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundException
from app.models.inventory import InventoryItem, InventoryTransaction, InventoryTransactionType
from app.models.notification import (
    Notification,
    NotificationChannel,
    NotificationChannelStatus,
    NotificationSeverity,
    NotificationType,
)
from app.models.packaging import PackagingItem, PackagingTransaction, PackagingTransactionType
from app.models.restock_order import (
    RestockOrder,
    RestockOrderItem,
    RestockOrderStatus,
)
from app.schemas.restock_order import (
    RestockOrderCreate,
    RestockSuggestionItem,
    RestockSummary,
)
from app.utils.stock import STATUS_PRIORITY, classify_stock, needs_restock, suggest_reorder_qty


class RestockService:
    @staticmethod
    def get_deficit_suggestions(
        db: Session,
        target_type: str | None = None,
    ) -> list[RestockSuggestionItem]:
        """
        Gathers all ingredients and packaging items requiring replenishment.
        Ranks by urgency: OUT_OF_STOCK > CRITICAL > LOW_STOCK.
        """
        suggestions: list[RestockSuggestionItem] = []

        # 1. Ingredients
        if not target_type or target_type.upper() in ["INVENTORY", "MIXED"]:
            ingredients = db.query(InventoryItem).filter(InventoryItem.is_active == True).all()
            for item in ingredients:
                if needs_restock(item.current_stock, item.reorder_level):
                    status = classify_stock(item.current_stock, item.minimum_stock, item.reorder_level)
                    suggested_qty = suggest_reorder_qty(item.current_stock, item.reorder_level, min_qty=1.0)
                    est_cost = round(suggested_qty * item.purchase_price, 2)

                    suggestions.append(
                        RestockSuggestionItem(
                            item_type="INVENTORY",
                            item_id=item.id,
                            name=item.name,
                            sku=item.sku,
                            category=item.category,
                            unit=item.unit,
                            current_stock=item.current_stock,
                            minimum_stock=item.minimum_stock,
                            reorder_level=item.reorder_level,
                            purchase_cost=item.purchase_price,
                            suggested_order_qty=suggested_qty,
                            estimated_cost=est_cost,
                            supplier=item.supplier or "Local Mandi / Agro Vendor",
                            status=status,
                        )
                    )

        # 2. Packaging Materials
        if not target_type or target_type.upper() in ["PACKAGING", "MIXED"]:
            packagings = db.query(PackagingItem).filter(PackagingItem.is_active == True).all()
            for item in packagings:
                if needs_restock(item.current_stock, item.reorder_level):
                    status = classify_stock(item.current_stock, item.minimum_stock, item.reorder_level)
                    suggested_qty = suggest_reorder_qty(
                        item.current_stock, item.reorder_level, min_qty=10.0, whole_units=True
                    )
                    est_cost = round(suggested_qty * item.purchase_cost, 2)

                    suggestions.append(
                        RestockSuggestionItem(
                            item_type="PACKAGING",
                            item_id=item.id,
                            name=item.name,
                            sku=item.sku,
                            category=item.category,
                            unit=item.unit,
                            current_stock=item.current_stock,
                            minimum_stock=item.minimum_stock,
                            reorder_level=item.reorder_level,
                            purchase_cost=item.purchase_cost,
                            suggested_order_qty=suggested_qty,
                            estimated_cost=est_cost,
                            supplier=item.supplier or "EcoPackaging India",
                            status=status,
                        )
                    )

        # Sort: OUT_OF_STOCK first, then CRITICAL, then LOW_STOCK
        suggestions.sort(key=lambda s: (STATUS_PRIORITY.get(s.status, 3), -s.estimated_cost))
        return suggestions

    @staticmethod
    def get_restock_summary(db: Session) -> RestockSummary:
        suggestions = RestockService.get_deficit_suggestions(db)
        critical_count = sum(1 for s in suggestions if s.status in ["OUT_OF_STOCK", "CRITICAL"])
        low_count = sum(1 for s in suggestions if s.status == "LOW_STOCK")
        total_inv = sum(s.estimated_cost for s in suggestions)

        open_pos = db.query(func.count(RestockOrder.id)).filter(
            RestockOrder.status.in_([RestockOrderStatus.DRAFT.value, RestockOrderStatus.ORDERED.value])
        ).scalar() or 0

        received_pos = db.query(func.count(RestockOrder.id)).filter(
            RestockOrder.status == RestockOrderStatus.RECEIVED.value
        ).scalar() or 0

        return RestockSummary(
            total_deficit_items=len(suggestions),
            critical_items_count=critical_count,
            low_stock_items_count=low_count,
            estimated_restock_investment_inr=round(total_inv, 2),
            open_pos_count=open_pos,
            received_pos_count=received_pos,
        )

    @staticmethod
    def create_restock_order(
        db: Session,
        payload: RestockOrderCreate,
        user_name: str = "Kitchen Manager",
    ) -> RestockOrder:
        # Generate PO number: PO-YYYYMMDD-XXXX
        today_str = datetime.now(UTC).strftime("%Y%m%d")
        rand_suffix = random.randint(1000, 9999)
        po_number = f"PO-{today_str}-{rand_suffix}"

        # Calculate items and total cost
        total_cost = 0.0
        po_items: list[RestockOrderItem] = []

        for item_in in payload.items:
            # Resolve item details
            if item_in.item_type.upper() == "INVENTORY":
                inv = db.query(InventoryItem).filter(InventoryItem.id == item_in.item_id).first()
                if not inv:
                    raise NotFoundException("Inventory item", item_in.item_id)
                name = inv.name
                sku = inv.sku
                unit = inv.unit
                curr_stock = inv.current_stock
                reorder_thresh = inv.reorder_level
                suggested_qty = suggest_reorder_qty(inv.current_stock, inv.reorder_level, min_qty=1.0)
                cost_per_unit = item_in.unit_cost if item_in.unit_cost is not None else inv.purchase_price
            else:
                pkg = db.query(PackagingItem).filter(PackagingItem.id == item_in.item_id).first()
                if not pkg:
                    raise NotFoundException("Packaging item", item_in.item_id)
                name = pkg.name
                sku = pkg.sku
                unit = pkg.unit
                curr_stock = pkg.current_stock
                reorder_thresh = pkg.reorder_level
                suggested_qty = suggest_reorder_qty(pkg.current_stock, pkg.reorder_level, min_qty=10.0, whole_units=True)
                cost_per_unit = item_in.unit_cost if item_in.unit_cost is not None else pkg.purchase_cost

            line_cost = round(item_in.ordered_quantity * cost_per_unit, 2)
            total_cost += line_cost

            po_item = RestockOrderItem(
                item_type=item_in.item_type.upper(),
                item_id=item_in.item_id,
                item_name=name,
                item_sku=sku,
                unit=unit,
                current_stock=curr_stock,
                reorder_threshold=reorder_thresh,
                suggested_quantity=suggested_qty,
                ordered_quantity=item_in.ordered_quantity,
                unit_cost=cost_per_unit,
                total_cost=line_cost,
                is_received=False,
            )
            po_items.append(po_item)

        order = RestockOrder(
            po_number=po_number,
            supplier_name=payload.supplier_name,
            supplier_contact=payload.supplier_contact,
            status=RestockOrderStatus.DRAFT.value,
            target_type=payload.target_type.upper(),
            total_estimated_cost=round(total_cost, 2),
            notes=payload.notes,
            created_by_name=user_name or payload.created_by_name or "Kitchen Manager",
            items=po_items,
        )

        db.add(order)
        db.commit()
        db.refresh(order)

        # Create system notification for PO generation
        notif = Notification(
            title=f"Restock PO Drafted: {po_number}",
            message=f"Purchase Order {po_number} generated for {payload.supplier_name} with {len(po_items)} items (Est. ₹{total_cost:,.2f}).",
            type=NotificationType.RESTOCK_PO.value,
            severity=NotificationSeverity.INFO.value,
            entity_type="RESTOCK_PO",
            entity_id=order.id,
            is_read=False,
            channel=NotificationChannel.IN_APP.value,
            channel_status=NotificationChannelStatus.SENT.value,
        )
        db.add(notif)
        db.commit()

        return order

    @staticmethod
    def list_orders(
        db: Session,
        status: str | None = None,
        page: int = 1,
        page_size: int = 10,
    ) -> tuple[int, list[RestockOrder]]:
        query = db.query(RestockOrder)
        if status and status.upper() != "ALL":
            query = query.filter(RestockOrder.status == status.upper())

        total = query.count()
        offset = (page - 1) * page_size
        items = query.order_by(desc(RestockOrder.created_at)).offset(offset).limit(page_size).all()
        return total, items

    @staticmethod
    def get_order_details(db: Session, po_id: int) -> RestockOrder | None:
        return db.query(RestockOrder).filter(RestockOrder.id == po_id).first()

    @staticmethod
    def update_order_status(db: Session, po_id: int, new_status: str) -> RestockOrder | None:
        order = db.query(RestockOrder).filter(RestockOrder.id == po_id).first()
        if not order:
            return None

        upper_status = new_status.upper()
        order.status = upper_status
        if upper_status == RestockOrderStatus.ORDERED.value and not order.ordered_at:
            order.ordered_at = datetime.now(UTC)

        db.commit()
        db.refresh(order)
        return order

    @staticmethod
    def receive_restock_order(
        db: Session,
        po_id: int,
        received_by: str = "Kitchen Store Manager",
    ) -> RestockOrder:
        order = db.query(RestockOrder).filter(RestockOrder.id == po_id).first()
        if not order:
            raise NotFoundException("Restock Order", po_id)

        if order.status == RestockOrderStatus.RECEIVED.value:
            return order  # Already received

        # Process each item: increment inventory and log STOCK_IN transaction
        for po_item in order.items:
            if not po_item.is_received:
                if po_item.item_type.upper() == "INVENTORY":
                    inv = db.query(InventoryItem).filter(InventoryItem.id == po_item.item_id).first()
                    if inv:
                        prev_stock = inv.current_stock
                        new_stock = round(prev_stock + po_item.ordered_quantity, 2)
                        inv.current_stock = new_stock

                        # Log inventory transaction
                        tx = InventoryTransaction(
                            inventory_item_id=inv.id,
                            transaction_type=InventoryTransactionType.STOCK_IN.value,
                            quantity=po_item.ordered_quantity,
                            stock_before=prev_stock,
                            stock_after=new_stock,
                            unit_price=po_item.unit_cost,
                            total_cost=po_item.total_cost,
                            reference_no=order.po_number,
                            notes=f"Restock PO {order.po_number} received from {order.supplier_name}",
                        )
                        db.add(tx)

                elif po_item.item_type.upper() == "PACKAGING":
                    pkg = db.query(PackagingItem).filter(PackagingItem.id == po_item.item_id).first()
                    if pkg:
                        prev_stock = pkg.current_stock
                        new_stock = round(prev_stock + po_item.ordered_quantity, 2)
                        pkg.current_stock = new_stock

                        # Log packaging transaction
                        tx = PackagingTransaction(
                            packaging_item_id=pkg.id,
                            transaction_type=PackagingTransactionType.STOCK_IN.value,
                            quantity=po_item.ordered_quantity,
                            stock_before=prev_stock,
                            stock_after=new_stock,
                            unit_cost=po_item.unit_cost,
                            total_cost=po_item.total_cost,
                            reference_no=order.po_number,
                            notes=f"Restock PO {order.po_number} received from {order.supplier_name}",
                        )
                        db.add(tx)

                po_item.is_received = True

        order.status = RestockOrderStatus.RECEIVED.value
        order.received_at = datetime.now(UTC)

        # Notify kitchen of successful stock receipt
        notif = Notification(
            title=f"Goods Received: {order.po_number}",
            message=f"Purchase order {order.po_number} ({len(order.items)} items, ₹{order.total_estimated_cost:,.2f}) successfully received and added to active kitchen stock.",
            type=NotificationType.RESTOCK_PO.value,
            severity=NotificationSeverity.SUCCESS.value,
            entity_type="RESTOCK_PO",
            entity_id=order.id,
            is_read=False,
            channel=NotificationChannel.IN_APP.value,
            channel_status=NotificationChannelStatus.SENT.value,
        )
        db.add(notif)
        db.commit()
        db.refresh(order)
        return order
