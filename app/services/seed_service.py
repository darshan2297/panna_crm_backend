from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.core.logging import logger
from app.models.customer import Customer
from app.models.inventory import InventoryItem, InventoryTransaction
from app.models.menu import MenuCategory, MenuItem, MenuItemPortion
from app.models.order import Order, OrderItem, OrderPlatform, OrderStatus, PaymentStatus
from app.models.order_history import OrderStatusHistory


def seed_dashboard_data(db: Session) -> None:
    """Seed sample realistic operational data for Panna Biryani if empty."""
    # Check if inventory items already seeded
    if db.query(InventoryItem).count() == 0:
        logger.info("Seeding initial inventory items...")
        inventory_samples = [
            {
                "name": "Daawat Basmati Biryani Rice",
                "sku": "ING-RICE-01",
                "category": "GRAIN",
                "unit": "kg",
                "current_stock": 14.5,
                "minimum_stock": 15.0,
                "reorder_level": 25.0,
                "purchase_price": 140.0,
                "supplier": "Royal Agro Traders",
            },
            {
                "name": "Fresh Malai Paneer",
                "sku": "ING-PAN-01",
                "category": "DAIRY",
                "unit": "kg",
                "current_stock": 6.0,
                "minimum_stock": 8.0,
                "reorder_level": 14.0,
                "purchase_price": 380.0,
                "supplier": "Amul Dairy Distributor",
            },
            {
                "name": "Panna Special Shahi Masala",
                "sku": "ING-SPICE-01",
                "category": "SPICE",
                "unit": "kg",
                "current_stock": 3.2,
                "minimum_stock": 5.0,
                "reorder_level": 8.0,
                "purchase_price": 650.0,
                "supplier": "Old City Spice House",
            },
            {
                "name": "Desi Pure Cow Ghee",
                "sku": "ING-GHEE-01",
                "category": "DAIRY",
                "unit": "kg",
                "current_stock": 26.0,
                "minimum_stock": 10.0,
                "reorder_level": 15.0,
                "purchase_price": 550.0,
                "supplier": "Brij Dairy Farm",
            },
            {
                "name": "Fresh Mint Leaves (Pudina)",
                "sku": "ING-MINT-01",
                "category": "VEGETABLE",
                "unit": "kg",
                "current_stock": 4.5,
                "minimum_stock": 5.0,
                "reorder_level": 8.0,
                "purchase_price": 80.0,
                "supplier": "Local Mandi Vendor",
            },
            {
                "name": "Red Sliced Onions (Birista)",
                "sku": "ING-ONION-01",
                "category": "VEGETABLE",
                "unit": "kg",
                "current_stock": 45.0,
                "minimum_stock": 20.0,
                "reorder_level": 30.0,
                "purchase_price": 35.0,
                "supplier": "Kisan Sabzi Mandi",
            },
            {
                "name": "Eco 500g Round Biryani Container",
                "sku": "PKG-500G-01",
                "category": "PACKAGING",
                "unit": "pcs",
                "current_stock": 380.0,
                "minimum_stock": 100.0,
                "reorder_level": 200.0,
                "purchase_price": 8.5,
                "supplier": "EcoPack India Ltd",
            },
            {
                "name": "Eco 1kg Large Biryani Container",
                "sku": "PKG-1KG-01",
                "category": "PACKAGING",
                "unit": "pcs",
                "current_stock": 190.0,
                "minimum_stock": 80.0,
                "reorder_level": 120.0,
                "purchase_price": 12.0,
                "supplier": "EcoPack India Ltd",
            },
            {
                "name": "Panna Kraft Paper Carry Bags",
                "sku": "PKG-BAG-01",
                "category": "PACKAGING",
                "unit": "pcs",
                "current_stock": 450.0,
                "minimum_stock": 150.0,
                "reorder_level": 250.0,
                "purchase_price": 6.0,
                "supplier": "PaperCraft Packaging",
            },
        ]

        for item in inventory_samples:
            db.add(InventoryItem(**item))
        db.commit()

    # Seed extra signature Biryani kitchen ingredients if missing
    extra_inventory = [
        {
            "name": "Fresh Farm Chicken (Curry & Biryani Cut)",
            "sku": "ING-CHK-01",
            "category": "MEAT",
            "unit": "kg",
            "current_stock": 18.5,
            "minimum_stock": 12.0,
            "reorder_level": 20.0,
            "purchase_price": 220.0,
            "supplier": "Venkateshwara Poultry",
            "storage_location": "Cold Room Freezer 1",
            "description": "Cleaned tender broiler cuts for Dum Biryani",
        },
        {
            "name": "Prime Mutton Cuts (Nalli & Boti)",
            "sku": "ING-MUT-01",
            "category": "MEAT",
            "unit": "kg",
            "current_stock": 8.0,
            "minimum_stock": 10.0,
            "reorder_level": 15.0,
            "purchase_price": 750.0,
            "supplier": "Delhi Quality Meats",
            "storage_location": "Cold Room Freezer 2",
            "description": "Selected bone-in baby goat cuts for Shahi Mutton Dum Biryani",
        },
        {
            "name": "Kashmiri Pure Mongra Saffron (Kesar)",
            "sku": "ING-SAF-01",
            "category": "SPICE",
            "unit": "g",
            "current_stock": 45.0,
            "minimum_stock": 20.0,
            "reorder_level": 50.0,
            "purchase_price": 320.0,
            "supplier": "Pampore Saffron Cooperative",
            "storage_location": "Spice Vault Shelf A",
            "description": "Aromatic saffron strands steeped in warm milk for biryani aromatics",
        },
        {
            "name": "Fresh Thick Curd (Dahi)",
            "sku": "ING-DAHI-01",
            "category": "DAIRY",
            "unit": "kg",
            "current_stock": 15.0,
            "minimum_stock": 10.0,
            "reorder_level": 20.0,
            "purchase_price": 60.0,
            "supplier": "Mother Dairy",
            "storage_location": "Chiller B2",
            "description": "Set curd for marinating meat and preparing fresh burani raita",
        },
        {
            "name": "Cold Pressed Mustard Oil (Sarson)",
            "sku": "ING-OIL-01",
            "category": "OIL",
            "unit": "l",
            "current_stock": 35.0,
            "minimum_stock": 15.0,
            "reorder_level": 25.0,
            "purchase_price": 160.0,
            "supplier": "Kachhi Ghani Mills",
            "storage_location": "Dry Store Section 3",
            "description": "Pungent mustard oil used in Kolkata style marination",
        },
        {
            "name": "Fresh Ginger Garlic Paste (Chef's Blend)",
            "sku": "ING-GGP-01",
            "category": "VEGETABLE",
            "unit": "kg",
            "current_stock": 6.5,
            "minimum_stock": 5.0,
            "reorder_level": 10.0,
            "purchase_price": 120.0,
            "supplier": "In-house Kitchen Prep",
            "storage_location": "Walk-in Chiller",
            "description": "Freshly ground 60:40 garlic-ginger ratio for marinade base",
        },
    ]
    for extra in extra_inventory:
        if not db.query(InventoryItem).filter(InventoryItem.sku == extra["sku"]).first():
            db.add(InventoryItem(**extra))
    db.commit()

    # Seed initial inventory transactions if empty
    if db.query(InventoryTransaction).count() == 0:
        logger.info("Seeding initial inventory movement transactions...")
        now = datetime.now(UTC)
        items_by_sku = {it.sku: it for it in db.query(InventoryItem).all()}

        tx_specs = [
            (
                "ING-RICE-01",
                "STOCK_IN",
                50.0,
                0.0,
                50.0,
                140.0,
                "PO-2026-081",
                "Received 50kg Daawat Biryani Rice from Royal Agro",
                5,
            ),
            (
                "ING-RICE-01",
                "STOCK_OUT",
                25.0,
                50.0,
                25.0,
                140.0,
                "BATCH-DUM-01",
                "Issued for lunch service Dum Biryani preparation",
                3,
            ),
            (
                "ING-RICE-01",
                "STOCK_OUT",
                10.5,
                25.0,
                14.5,
                140.0,
                "BATCH-DUM-02",
                "Issued for dinner rush Dum Biryani handis",
                1,
            ),
            (
                "ING-PAN-01",
                "STOCK_IN",
                20.0,
                0.0,
                20.0,
                380.0,
                "PO-2026-084",
                "Morning delivery from Amul Distributor",
                4,
            ),
            (
                "ING-PAN-01",
                "STOCK_OUT",
                13.0,
                20.0,
                7.0,
                380.0,
                "KITCHEN-PREP",
                "Portioned for Paneer Dum & Tikka orders",
                2,
            ),
            (
                "ING-PAN-01",
                "WASTAGE",
                1.0,
                7.0,
                6.0,
                380.0,
                "WASTE-019",
                "Trimmings & broken paneer cubes unfit for service",
                1,
            ),
            ("ING-GHEE-01", "STOCK_IN", 30.0, 0.0, 30.0, 550.0, "PO-2026-079", "Restocked 30kg Desi Cow Ghee tins", 6),
            (
                "ING-GHEE-01",
                "STOCK_OUT",
                4.0,
                30.0,
                26.0,
                550.0,
                "DUM-SEAL",
                "Layering and sealing handis for dum cooking",
                2,
            ),
            (
                "ING-CHK-01",
                "STOCK_IN",
                35.0,
                0.0,
                35.0,
                220.0,
                "PO-2026-092",
                "Morning poultry delivery cleaned and prepped",
                3,
            ),
            (
                "ING-CHK-01",
                "STOCK_OUT",
                16.5,
                35.0,
                18.5,
                220.0,
                "BATCH-CHK-01",
                "Issued for Chicken Biryani & Chicken Tikka batches",
                1,
            ),
            (
                "ING-MUT-01",
                "STOCK_IN",
                15.0,
                0.0,
                15.0,
                750.0,
                "PO-2026-089",
                "Received 15kg Prime Mutton cuts from Delhi Quality Meats",
                4,
            ),
            ("ING-MUT-01", "STOCK_OUT", 7.0, 15.0, 8.0, 750.0, "BATCH-MUT-01", "Slow dum cooking Shahi Mutton degh", 2),
            (
                "ING-MINT-01",
                "STOCK_IN",
                10.0,
                0.0,
                10.0,
                80.0,
                "PO-2026-088",
                "Fresh mint bunch received from local mandi",
                2,
            ),
            (
                "ING-MINT-01",
                "STOCK_OUT",
                5.0,
                10.0,
                5.0,
                80.0,
                "RAITA-PREP",
                "Burani Raita & Biryani garnish preparation",
                1,
            ),
            ("ING-MINT-01", "WASTAGE", 0.5, 5.0, 4.5, 80.0, "WASTE-021", "Wilted leaves during evening sort", 1),
            (
                "PKG-500G-01",
                "STOCK_IN",
                500.0,
                0.0,
                500.0,
                8.5,
                "PO-PKG-102",
                "Carton of 500g round food-grade biryani bowls",
                6,
            ),
            (
                "PKG-500G-01",
                "STOCK_OUT",
                120.0,
                500.0,
                380.0,
                8.5,
                "PACK-DISPATCH",
                "Packaging consumed for online orders",
                2,
            ),
        ]

        for sku, t_type, qty, s_before, s_after, price, ref, notes, days_ago in tx_specs:
            target_item = items_by_sku.get(sku)
            if target_item:
                tx = InventoryTransaction(
                    inventory_item_id=target_item.id,
                    transaction_type=t_type,
                    quantity=qty,
                    stock_before=s_before,
                    stock_after=s_after,
                    unit_price=price,
                    total_cost=round(qty * price, 2),
                    reference_no=ref,
                    notes=notes,
                    created_at=now - timedelta(days=days_ago, hours=3),
                )
                db.add(tx)
        db.commit()

    # Check if orders already seeded
    if db.query(Order).count() == 0:
        logger.info("Seeding initial orders and order items...")
        now = datetime.now(UTC)

        order_specs = [
            # Today's active / recent orders
            {
                "number": "PB-1024",
                "platform": OrderPlatform.ZOMATO.value,
                "customer": "Rahul Sharma",
                "phone": "+91 9876543210",
                "items_summary": "1x Panna Paneer Dum Biryani (500g), 1x Raita (Included)",
                "amount": 320.0,
                "status": OrderStatus.PREPARING.value,
                "minutes_ago": 15,
                "items": [
                    ("Panna Paneer Dum Biryani", "500g", 1, 320.0),
                ],
            },
            {
                "number": "PB-1023",
                "platform": OrderPlatform.SWIGGY.value,
                "customer": "Priya Patel",
                "phone": "+91 9822011223",
                "items_summary": "1x Panna Veg Dum Biryani (1kg)",
                "amount": 480.0,
                "status": OrderStatus.CONFIRMED.value,
                "minutes_ago": 28,
                "items": [
                    ("Panna Veg Dum Biryani", "1kg", 1, 480.0),
                ],
            },
            {
                "number": "PB-1022",
                "platform": OrderPlatform.WEBSITE.value,
                "customer": "Vikram Malhotra",
                "phone": "+91 9911223344",
                "items_summary": "1x Panna Veg Dum Biryani (500g)",
                "amount": 260.0,
                "status": OrderStatus.READY.value,
                "minutes_ago": 45,
                "items": [
                    ("Panna Veg Dum Biryani", "500g", 1, 260.0),
                ],
            },
            {
                "number": "PB-1021",
                "platform": OrderPlatform.ZOMATO.value,
                "customer": "Amit Verma",
                "phone": "+91 9765432109",
                "items_summary": "1x Panna Hyderabadi Dum Biryani (500g)",
                "amount": 350.0,
                "status": OrderStatus.DELIVERED.value,
                "minutes_ago": 72,
                "items": [
                    ("Panna Hyderabadi Dum Biryani", "500g", 1, 350.0),
                ],
            },
            {
                "number": "PB-1020",
                "platform": OrderPlatform.SWIGGY.value,
                "customer": "Sneha Roy",
                "phone": "+91 9654321987",
                "items_summary": "1x Panna Royal Dum Biryani (750g)",
                "amount": 420.0,
                "status": OrderStatus.PREPARING.value,
                "minutes_ago": 90,
                "items": [
                    ("Panna Royal Dum Biryani", "750g", 1, 420.0),
                ],
            },
            {
                "number": "PB-1019",
                "platform": OrderPlatform.WEBSITE.value,
                "customer": "Karan Mehta",
                "phone": "+91 9543219876",
                "items_summary": "2x Panna Paneer Dum Biryani (500g)",
                "amount": 640.0,
                "status": OrderStatus.DELIVERED.value,
                "minutes_ago": 120,
                "items": [
                    ("Panna Paneer Dum Biryani", "500g", 2, 320.0),
                ],
            },
            {
                "number": "PB-1018",
                "platform": OrderPlatform.ZOMATO.value,
                "customer": "Ananya Singh",
                "phone": "+91 9432198765",
                "items_summary": "1x Panna Paneer Dum Biryani (1kg)",
                "amount": 580.0,
                "status": OrderStatus.DELIVERED.value,
                "minutes_ago": 150,
                "items": [
                    ("Panna Paneer Dum Biryani", "1kg", 1, 580.0),
                ],
            },
            {
                "number": "PB-1017",
                "platform": OrderPlatform.SWIGGY.value,
                "customer": "Rohan Joshi",
                "phone": "+91 9321987654",
                "items_summary": "1x Panna Veg Dum Biryani (500g)",
                "amount": 260.0,
                "status": OrderStatus.DELIVERED.value,
                "minutes_ago": 180,
                "items": [
                    ("Panna Veg Dum Biryani", "500g", 1, 260.0),
                ],
            },
            {
                "number": "PB-1016",
                "platform": OrderPlatform.WEBSITE.value,
                "customer": "Deepak Gupta",
                "phone": "+91 9219876543",
                "items_summary": "1x Panna Royal Dum Biryani (1kg)",
                "amount": 650.0,
                "status": OrderStatus.DELIVERED.value,
                "minutes_ago": 220,
                "items": [
                    ("Panna Royal Dum Biryani", "1kg", 1, 650.0),
                ],
            },
            {
                "number": "PB-1015",
                "platform": OrderPlatform.ZOMATO.value,
                "customer": "Meera Nair",
                "phone": "+91 9109876543",
                "items_summary": "1x Panna Hyderabadi Dum Biryani (750g)",
                "amount": 450.0,
                "status": OrderStatus.CANCELLED.value,
                "minutes_ago": 260,
                "items": [
                    ("Panna Hyderabadi Dum Biryani", "750g", 1, 450.0),
                ],
            },
        ]

        # Add 10 today orders
        for s in order_specs:
            created_time = now - timedelta(minutes=s["minutes_ago"])

            # Find or create customer
            customer = db.query(Customer).filter(Customer.phone == s["phone"]).first()
            if not customer:
                customer = Customer(
                    name=s["customer"],
                    phone=s["phone"],
                    default_address="Indiranagar, Stage 2, Bangalore",
                    total_orders=1,
                    total_spent=s["amount"],
                )
                db.add(customer)
                db.flush()
            else:
                customer.total_orders += 1
                customer.total_spent += s["amount"]

            order = Order(
                order_number=s["number"],
                platform=s["platform"],
                customer_id=customer.id,
                customer_name=s["customer"],
                customer_phone=s["phone"],
                delivery_address="Indiranagar, Stage 2, Bangalore",
                subtotal=s["amount"],
                total_amount=s["amount"],
                order_status=s["status"],
                payment_status=PaymentStatus.PAID.value
                if s["status"] != OrderStatus.CANCELLED.value
                else PaymentStatus.REFUNDED.value,
                items_summary=s["items_summary"],
                created_at=created_time,
                updated_at=created_time,
            )
            db.add(order)
            db.flush()

            # Seed status history
            db.add(
                OrderStatusHistory(
                    order_id=order.id,
                    previous_status=None,
                    new_status=OrderStatus.NEW.value,
                    changed_by_name="System",
                    notes=f"Order received via {s['platform']}",
                    created_at=created_time,
                )
            )
            if s["status"] != OrderStatus.NEW.value:
                db.add(
                    OrderStatusHistory(
                        order_id=order.id,
                        previous_status=OrderStatus.NEW.value,
                        new_status=s["status"],
                        changed_by_name="Panna Staff",
                        notes=f"Order marked {s['status']}",
                        created_at=created_time + timedelta(minutes=3),
                    )
                )

            for item_name, portion, qty, price in s["items"]:
                db.add(
                    OrderItem(
                        order_id=order.id,
                        item_name=item_name,
                        portion_size=portion,
                        quantity=qty,
                        unit_price=price,
                        total_price=price * qty,
                        created_at=created_time,
                        updated_at=created_time,
                    )
                )

        # Add historical orders across past 6 days to populate realistic 7-day trend charts
        platforms = [OrderPlatform.ZOMATO.value, OrderPlatform.SWIGGY.value, OrderPlatform.WEBSITE.value]
        biryani_pool = [
            ("Panna Paneer Dum Biryani", "500g", 320.0),
            ("Panna Veg Dum Biryani", "500g", 260.0),
            ("Panna Royal Dum Biryani", "750g", 420.0),
            ("Panna Hyderabadi Dum Biryani", "1kg", 550.0),
        ]

        order_seq = 1014
        for days_back in range(1, 7):
            day_orders_count = 6 + (days_back % 3)
            for i in range(day_orders_count):
                order_time = now - timedelta(days=days_back, hours=2 + i * 2)
                plat = platforms[(i + days_back) % 3]
                item_name, portion, price = biryani_pool[(i * days_back) % len(biryani_pool)]
                total = price

                order = Order(
                    order_number=f"PB-{order_seq}",
                    platform=plat,
                    customer_name=f"Customer {order_seq}",
                    customer_phone="+91 9800011122",
                    delivery_address="Bangalore Delivery Area",
                    subtotal=total,
                    total_amount=total,
                    order_status=OrderStatus.DELIVERED.value,
                    payment_status=PaymentStatus.PAID.value,
                    items_summary=f"1x {item_name} ({portion})",
                    created_at=order_time,
                    updated_at=order_time,
                )
                db.add(order)
                db.flush()

                db.add(
                    OrderItem(
                        order_id=order.id,
                        item_name=item_name,
                        portion_size=portion,
                        quantity=1,
                        unit_price=price,
                        total_price=total,
                        created_at=order_time,
                        updated_at=order_time,
                    )
                )
                order_seq -= 1

        db.commit()
        logger.info("Successfully seeded historical and current operational orders.")

    # Seed initial menu categories and items if empty
    # Menu catalog is seeded with the real website menu by website_seed.seed_website_menu(db)

    # Seed initial packaging items, stocks, and rules if empty
    seed_packaging_data(db)


def seed_menu_data(db: Session) -> None:
    """Seed comprehensive authentic Panna Biryani menu with categories, dishes, portions and platform pricing."""
    if db.query(MenuCategory).count() > 0:
        return

    logger.info("Seeding initial authentic Panna Biryani menu catalog...")

    menu_dataset = [
        {
            "category": "Dum Biryani",
            "slug": "dum-biryani",
            "description": "Slow cooked authentic royal biryanis sealed with dough in copper handis.",
            "display_order": 1,
            "items": [
                {
                    "name": "Panna Special Chicken Dum Biryani",
                    "slug": "panna-special-chicken-dum-biryani",
                    "description": "Tender bone-in chicken marinated in secret 21-spice pot, layered with aged Daawat basmati rice and saffron ghee.",
                    "is_veg": False,
                    "spice_level": "MEDIUM",
                    "preparation_time_minutes": 25,
                    "display_order": 1,
                    "portions": [
                        {
                            "portion_size": "Single",
                            "weight_grams": 250,
                            "serves_persons": "1 Person",
                            "cost_price": 90.0,
                            "base_price": 199.0,
                            "zomato_price": 249.0,
                            "swiggy_price": 239.0,
                        },
                        {
                            "portion_size": "500g",
                            "weight_grams": 500,
                            "serves_persons": "1-2 Persons",
                            "cost_price": 150.0,
                            "base_price": 349.0,
                            "zomato_price": 429.0,
                            "swiggy_price": 419.0,
                        },
                        {
                            "portion_size": "1kg",
                            "weight_grams": 1000,
                            "serves_persons": "3-4 Persons",
                            "cost_price": 260.0,
                            "base_price": 599.0,
                            "zomato_price": 729.0,
                            "swiggy_price": 719.0,
                        },
                    ],
                },
                {
                    "name": "Royal Mutton Dum Biryani",
                    "slug": "royal-mutton-dum-biryani",
                    "description": "Succulent chunks of young goat meat slow-cooked for 4 hours with fragrant long-grain basmati and kewra essence.",
                    "is_veg": False,
                    "spice_level": "MEDIUM",
                    "preparation_time_minutes": 30,
                    "display_order": 2,
                    "portions": [
                        {
                            "portion_size": "Single",
                            "weight_grams": 250,
                            "serves_persons": "1 Person",
                            "cost_price": 140.0,
                            "base_price": 279.0,
                            "zomato_price": 339.0,
                            "swiggy_price": 329.0,
                        },
                        {
                            "portion_size": "500g",
                            "weight_grams": 500,
                            "serves_persons": "1-2 Persons",
                            "cost_price": 220.0,
                            "base_price": 449.0,
                            "zomato_price": 549.0,
                            "swiggy_price": 539.0,
                        },
                        {
                            "portion_size": "1kg",
                            "weight_grams": 1000,
                            "serves_persons": "3-4 Persons",
                            "cost_price": 410.0,
                            "base_price": 849.0,
                            "zomato_price": 1039.0,
                            "swiggy_price": 1019.0,
                        },
                    ],
                },
                {
                    "name": "Panna Paneer Dum Biryani",
                    "slug": "panna-paneer-dum-biryani",
                    "description": "Rich cubes of fresh malai paneer steeped in roasted coriander, mint leaves, and mild aromatic saffron rice.",
                    "is_veg": True,
                    "spice_level": "MILD",
                    "preparation_time_minutes": 20,
                    "display_order": 3,
                    "portions": [
                        {
                            "portion_size": "Single",
                            "weight_grams": 250,
                            "serves_persons": "1 Person",
                            "cost_price": 80.0,
                            "base_price": 179.0,
                            "zomato_price": 219.0,
                            "swiggy_price": 215.0,
                        },
                        {
                            "portion_size": "500g",
                            "weight_grams": 500,
                            "serves_persons": "1-2 Persons",
                            "cost_price": 130.0,
                            "base_price": 299.0,
                            "zomato_price": 365.0,
                            "swiggy_price": 359.0,
                        },
                        {
                            "portion_size": "1kg",
                            "weight_grams": 1000,
                            "serves_persons": "3-4 Persons",
                            "cost_price": 230.0,
                            "base_price": 529.0,
                            "zomato_price": 645.0,
                            "swiggy_price": 635.0,
                        },
                    ],
                },
                {
                    "name": "Lucknowi Handi Veg Biryani",
                    "slug": "lucknowi-handi-veg-biryani",
                    "description": "Assorted garden veggies, baby potatoes, green peas and golden fried onions infused with Awadhi cardamoms.",
                    "is_veg": True,
                    "spice_level": "MILD",
                    "preparation_time_minutes": 20,
                    "display_order": 4,
                    "portions": [
                        {
                            "portion_size": "500g",
                            "weight_grams": 500,
                            "serves_persons": "1-2 Persons",
                            "cost_price": 110.0,
                            "base_price": 269.0,
                            "zomato_price": 329.0,
                            "swiggy_price": 325.0,
                        },
                        {
                            "portion_size": "1kg",
                            "weight_grams": 1000,
                            "serves_persons": "3-4 Persons",
                            "cost_price": 200.0,
                            "base_price": 479.0,
                            "zomato_price": 585.0,
                            "swiggy_price": 575.0,
                        },
                    ],
                },
                {
                    "name": "Special Hyderabadi Egg Dum Biryani",
                    "slug": "special-hyderabadi-egg-dum-biryani",
                    "description": "Boiled eggs shallow fried in Kashmiri red chili masala and tossed with spicy Nizami biryani rice.",
                    "is_veg": False,
                    "spice_level": "SPICY",
                    "preparation_time_minutes": 20,
                    "display_order": 5,
                    "portions": [
                        {
                            "portion_size": "500g",
                            "weight_grams": 500,
                            "serves_persons": "1-2 Persons",
                            "cost_price": 100.0,
                            "base_price": 249.0,
                            "zomato_price": 305.0,
                            "swiggy_price": 299.0,
                        },
                        {
                            "portion_size": "1kg",
                            "weight_grams": 1000,
                            "serves_persons": "3-4 Persons",
                            "cost_price": 180.0,
                            "base_price": 439.0,
                            "zomato_price": 535.0,
                            "swiggy_price": 525.0,
                        },
                    ],
                },
                {
                    "name": "Coastal Prawns Dum Biryani",
                    "slug": "coastal-prawns-dum-biryani",
                    "description": "Juicy ocean prawns spiced with star anise, curry leaves and coconut milk infused fragrant biryani rice.",
                    "is_veg": False,
                    "spice_level": "SPICY",
                    "preparation_time_minutes": 25,
                    "display_order": 6,
                    "portions": [
                        {
                            "portion_size": "500g",
                            "weight_grams": 500,
                            "serves_persons": "1-2 Persons",
                            "cost_price": 260.0,
                            "base_price": 499.0,
                            "zomato_price": 609.0,
                            "swiggy_price": 599.0,
                        },
                    ],
                },
            ],
        },
        {
            "category": "Starters & Kebabs",
            "slug": "starters-kebabs",
            "description": "Charcoal grilled tandoori skewers and crispy spiced appetizers.",
            "display_order": 2,
            "items": [
                {
                    "name": "Hyderabadi Chicken 65 (Boneless)",
                    "slug": "hyderabadi-chicken-65-boneless",
                    "description": "Crispy fried tender chicken bites tossed in fiery yogurt, green chilies, garlic slivers and crispy curry leaves.",
                    "is_veg": False,
                    "spice_level": "SPICY",
                    "preparation_time_minutes": 15,
                    "display_order": 1,
                    "portions": [
                        {
                            "portion_size": "250g",
                            "weight_grams": 250,
                            "serves_persons": "1-2 Persons",
                            "cost_price": 110.0,
                            "base_price": 249.0,
                            "zomato_price": 305.0,
                            "swiggy_price": 299.0,
                        },
                        {
                            "portion_size": "500g",
                            "weight_grams": 500,
                            "serves_persons": "2-3 Persons",
                            "cost_price": 200.0,
                            "base_price": 449.0,
                            "zomato_price": 549.0,
                            "swiggy_price": 539.0,
                        },
                    ],
                },
                {
                    "name": "Mutton Galouti Kebab (4 pcs)",
                    "slug": "mutton-galouti-kebab-4-pcs",
                    "description": "Mouth-melting smoked lamb patties with papaya marinade and roasted gram flour.",
                    "is_veg": False,
                    "spice_level": "MEDIUM",
                    "preparation_time_minutes": 20,
                    "display_order": 2,
                    "portions": [
                        {
                            "portion_size": "Regular",
                            "weight_grams": 200,
                            "serves_persons": "1-2 Persons",
                            "cost_price": 160.0,
                            "base_price": 329.0,
                            "zomato_price": 400.0,
                            "swiggy_price": 395.0,
                        },
                    ],
                },
                {
                    "name": "Shahi Paneer Tikka (6 pcs)",
                    "slug": "shahi-paneer-tikka-6-pcs",
                    "description": "Cottage cheese marinated in carom seeds, hung curd, and mustard oil, roasted golden in clay tandoor.",
                    "is_veg": True,
                    "spice_level": "MEDIUM",
                    "preparation_time_minutes": 15,
                    "display_order": 3,
                    "portions": [
                        {
                            "portion_size": "Regular",
                            "weight_grams": 250,
                            "serves_persons": "1-2 Persons",
                            "cost_price": 100.0,
                            "base_price": 239.0,
                            "zomato_price": 290.0,
                            "swiggy_price": 285.0,
                        },
                    ],
                },
                {
                    "name": "Dahi Ke Kebab (4 pcs)",
                    "slug": "dahi-ke-kebab-4-pcs",
                    "description": "Crispy golden patties of hung curd, cottage cheese, fresh coriander and cracked black pepper.",
                    "is_veg": True,
                    "spice_level": "MILD",
                    "preparation_time_minutes": 15,
                    "display_order": 4,
                    "portions": [
                        {
                            "portion_size": "Regular",
                            "weight_grams": 200,
                            "serves_persons": "1-2 Persons",
                            "cost_price": 85.0,
                            "base_price": 199.0,
                            "zomato_price": 245.0,
                            "swiggy_price": 239.0,
                        },
                    ],
                },
            ],
        },
        {
            "category": "Curries & Gravies",
            "slug": "curries-gravies",
            "description": "Slow simmered rich gravies and Nawabi specialty curries.",
            "display_order": 3,
            "items": [
                {
                    "name": "Old City Dum Ka Murgh",
                    "slug": "old-city-dum-ka-murgh",
                    "description": "Whole chicken portions slow cooked on dum in almond, cashew and brown onion velvet gravy.",
                    "is_veg": False,
                    "spice_level": "MEDIUM",
                    "preparation_time_minutes": 20,
                    "display_order": 1,
                    "portions": [
                        {
                            "portion_size": "400ml",
                            "weight_grams": 400,
                            "serves_persons": "1-2 Persons",
                            "cost_price": 140.0,
                            "base_price": 319.0,
                            "zomato_price": 389.0,
                            "swiggy_price": 385.0,
                        },
                    ],
                },
                {
                    "name": "Paneer Butter Masala Handi",
                    "slug": "paneer-butter-masala-handi",
                    "description": "Silky tomato-butter gravy with fresh malai paneer cubes, dried fenugreek leaves and fresh cream.",
                    "is_veg": True,
                    "spice_level": "MILD",
                    "preparation_time_minutes": 15,
                    "display_order": 2,
                    "portions": [
                        {
                            "portion_size": "400ml",
                            "weight_grams": 400,
                            "serves_persons": "1-2 Persons",
                            "cost_price": 115.0,
                            "base_price": 259.0,
                            "zomato_price": 315.0,
                            "swiggy_price": 310.0,
                        },
                    ],
                },
                {
                    "name": "Authentic Hyderabadi Mirchi Ka Salan",
                    "slug": "authentic-hyderabadi-mirchi-ka-salan",
                    "description": "Large bhavnagri green chilies simmered in roasted peanut, sesame, and tamarind gravy. The classic biryani companion.",
                    "is_veg": True,
                    "spice_level": "SPICY",
                    "preparation_time_minutes": 15,
                    "display_order": 3,
                    "portions": [
                        {
                            "portion_size": "250ml",
                            "weight_grams": 250,
                            "serves_persons": "1-2 Persons",
                            "cost_price": 45.0,
                            "base_price": 119.0,
                            "zomato_price": 145.0,
                            "swiggy_price": 140.0,
                        },
                    ],
                },
            ],
        },
        {
            "category": "Breads & Rice",
            "slug": "breads-rice",
            "description": "Hand tossed tandoori flatbreads and aromatic plain rice.",
            "display_order": 4,
            "items": [
                {
                    "name": "Roomali Roti (Pack of 2)",
                    "slug": "roomali-roti-pack-of-2",
                    "description": "Handkerchief-thin soft Indian bread baked on inverted domed kadai.",
                    "is_veg": True,
                    "spice_level": "MILD",
                    "preparation_time_minutes": 10,
                    "display_order": 1,
                    "portions": [
                        {
                            "portion_size": "2 pcs",
                            "weight_grams": 100,
                            "serves_persons": "1 Person",
                            "cost_price": 20.0,
                            "base_price": 59.0,
                            "zomato_price": 72.0,
                            "swiggy_price": 70.0,
                        },
                    ],
                },
                {
                    "name": "Garlic Butter Naan (2 pcs)",
                    "slug": "garlic-butter-naan-2-pcs",
                    "description": "Crispy leavened flatbread brushed with garlic butter and fresh coriander.",
                    "is_veg": True,
                    "spice_level": "MILD",
                    "preparation_time_minutes": 10,
                    "display_order": 2,
                    "portions": [
                        {
                            "portion_size": "2 pcs",
                            "weight_grams": 150,
                            "serves_persons": "1 Person",
                            "cost_price": 30.0,
                            "base_price": 89.0,
                            "zomato_price": 109.0,
                            "swiggy_price": 105.0,
                        },
                    ],
                },
            ],
        },
        {
            "category": "Desserts",
            "slug": "desserts",
            "description": "Royal Nizami sweets and traditional Indian mithai.",
            "display_order": 5,
            "items": [
                {
                    "name": "Gulab Jamun with Kesari Rabdi (2 pcs)",
                    "slug": "gulab-jamun-with-kesari-rabdi-2-pcs",
                    "description": "Warm khoya dumplings soaked in rose syrup served atop chilled saffron rabdi.",
                    "is_veg": True,
                    "spice_level": "MILD",
                    "preparation_time_minutes": 5,
                    "display_order": 1,
                    "portions": [
                        {
                            "portion_size": "Single",
                            "weight_grams": 150,
                            "serves_persons": "1 Person",
                            "cost_price": 45.0,
                            "base_price": 119.0,
                            "zomato_price": 145.0,
                            "swiggy_price": 140.0,
                        },
                    ],
                },
                {
                    "name": "Matka Kesar Phirni",
                    "slug": "matka-kesar-phirni",
                    "description": "Slow cooked ground rice pudding in earthenware pot scented with cardamom, saffron and pistachios.",
                    "is_veg": True,
                    "spice_level": "MILD",
                    "preparation_time_minutes": 5,
                    "display_order": 2,
                    "portions": [
                        {
                            "portion_size": "150ml",
                            "weight_grams": 150,
                            "serves_persons": "1 Person",
                            "cost_price": 40.0,
                            "base_price": 99.0,
                            "zomato_price": 120.0,
                            "swiggy_price": 119.0,
                        },
                    ],
                },
            ],
        },
        {
            "category": "Accompaniments & Beverages",
            "slug": "beverages-raita",
            "description": "Refreshing coolers, buttermilk and seasoned raitas.",
            "display_order": 6,
            "items": [
                {
                    "name": "Burani Garlic Raita",
                    "slug": "burani-garlic-raita",
                    "description": "Velvety spiced thick yogurt whipped with roasted garlic and crushed cumin.",
                    "is_veg": True,
                    "spice_level": "MILD",
                    "preparation_time_minutes": 5,
                    "display_order": 1,
                    "portions": [
                        {
                            "portion_size": "250ml",
                            "weight_grams": 250,
                            "serves_persons": "1-2 Persons",
                            "cost_price": 25.0,
                            "base_price": 69.0,
                            "zomato_price": 84.0,
                            "swiggy_price": 82.0,
                        },
                    ],
                },
                {
                    "name": "Panna Special Masala Chaas (300ml)",
                    "slug": "panna-special-masala-chaas-300ml",
                    "description": "Chilled spiced buttermilk with roasted jeera, ginger, mint and black salt.",
                    "is_veg": True,
                    "spice_level": "MILD",
                    "preparation_time_minutes": 5,
                    "display_order": 2,
                    "portions": [
                        {
                            "portion_size": "Single",
                            "weight_grams": 300,
                            "serves_persons": "1 Person",
                            "cost_price": 18.0,
                            "base_price": 59.0,
                            "zomato_price": 72.0,
                            "swiggy_price": 70.0,
                        },
                    ],
                },
            ],
        },
    ]

    for cat_data in menu_dataset:
        cat = MenuCategory(
            name=cat_data["category"],
            slug=cat_data["slug"],
            description=cat_data["description"],
            display_order=cat_data["display_order"],
            is_active=True,
        )
        db.add(cat)
        db.flush()

        for itm_data in cat_data["items"]:
            item = MenuItem(
                category_id=cat.id,
                name=itm_data["name"],
                slug=itm_data["slug"],
                description=itm_data["description"],
                is_veg=itm_data["is_veg"],
                spice_level=itm_data["spice_level"],
                preparation_time_minutes=itm_data["preparation_time_minutes"],
                is_available=True,
                is_active=True,
                display_order=itm_data["display_order"],
            )
            db.add(item)
            db.flush()

            for p_data in itm_data["portions"]:
                portion = MenuItemPortion(
                    menu_item_id=item.id,
                    portion_size=p_data["portion_size"],
                    weight_grams=p_data.get("weight_grams"),
                    serves_persons=p_data.get("serves_persons"),
                    cost_price=p_data["cost_price"],
                    base_price=p_data["base_price"],
                    zomato_price=p_data["zomato_price"],
                    swiggy_price=p_data["swiggy_price"],
                    is_available=True,
                )
                db.add(portion)

    db.commit()
    logger.info("Successfully seeded authentic Panna Biryani menu categories, items and portions.")

    # Phase 8: Packaging
    seed_packaging_data(db)

    # Phase 9: Notifications & Restock
    seed_notifications_and_restock_data(db)


def seed_packaging_data(db: Session) -> None:
    """Seed authentic Panna Biryani packaging items, initial transactions, and consumption rules if empty."""
    from app.models.packaging import PackagingConsumptionRule, PackagingItem, PackagingTransaction

    if db.query(PackagingItem).count() > 0:
        return

    logger.info("Seeding initial packaging inventory and rules...")
    packaging_samples = [
        {
            "name": "500ml Microwavable Biryani Bowl with Snap Lid",
            "sku": "PKG-CON-001",
            "category": "CONTAINER",
            "material": "Food Grade PP",
            "capacity": "500ml",
            "unit": "pcs",
            "current_stock": 280.0,
            "minimum_stock": 100.0,
            "reorder_level": 200.0,
            "purchase_cost": 6.50,
            "supplier": "PlastoPack Industries",
            "storage_location": "Aisle P-1, Shelf A",
            "description": "Premium round black PP container with transparent leakproof lid, suitable for microwave reheat.",
        },
        {
            "name": "1000ml Microwavable Biryani Bowl with Snap Lid",
            "sku": "PKG-CON-002",
            "category": "CONTAINER",
            "material": "Food Grade PP",
            "capacity": "1000ml",
            "unit": "pcs",
            "current_stock": 190.0,
            "minimum_stock": 80.0,
            "reorder_level": 150.0,
            "purchase_cost": 9.80,
            "supplier": "PlastoPack Industries",
            "storage_location": "Aisle P-1, Shelf B",
            "description": "Large round bowl with vent hole lid for 1kg family feast biryani orders.",
        },
        {
            "name": "Authentic Earthen Terracotta Handi (500g)",
            "sku": "PKG-CON-003",
            "category": "CONTAINER",
            "material": "Terracotta Clay",
            "capacity": "500g",
            "unit": "pcs",
            "current_stock": 85.0,
            "minimum_stock": 50.0,
            "reorder_level": 80.0,
            "purchase_cost": 28.00,
            "supplier": "Kumbhar Clay Crafts",
            "storage_location": "Clay Vault, Rack 1",
            "description": "Kiln-baked traditional unglazed mud pot for authentic Dum cooking and Royal Handi delivery.",
        },
        {
            "name": "Authentic Earthen Terracotta Handi (1kg)",
            "sku": "PKG-CON-004",
            "category": "CONTAINER",
            "material": "Terracotta Clay",
            "capacity": "1kg",
            "unit": "pcs",
            "current_stock": 42.0,
            "minimum_stock": 40.0,
            "reorder_level": 60.0,
            "purchase_cost": 42.00,
            "supplier": "Kumbhar Clay Crafts",
            "storage_location": "Clay Vault, Rack 2",
            "description": "Heavy clay pot for large royal party dum biryani handis.",
        },
        {
            "name": "Heavy-Duty Brown Kraft Biryani Carry Bag (Large)",
            "sku": "PKG-BAG-001",
            "category": "BAG",
            "material": "Virgin Kraft Paper",
            "capacity": "Standard",
            "unit": "pcs",
            "current_stock": 340.0,
            "minimum_stock": 150.0,
            "reorder_level": 300.0,
            "purchase_cost": 7.20,
            "supplier": "GreenEarth EcoPack",
            "storage_location": "Dispatch Station, Rack D",
            "description": "140 GSM reinforced paper bag with flat twisted handles, holds up to 2 large handis.",
        },
        {
            "name": "Medium Brown Kraft Paper Delivery Bag",
            "sku": "PKG-BAG-002",
            "category": "BAG",
            "material": "Virgin Kraft Paper",
            "capacity": "Medium",
            "unit": "pcs",
            "current_stock": 420.0,
            "minimum_stock": 150.0,
            "reorder_level": 250.0,
            "purchase_cost": 5.50,
            "supplier": "GreenEarth EcoPack",
            "storage_location": "Dispatch Station, Rack D",
            "description": "Standard delivery bag for 1 portion biryani + accompaniments.",
        },
        {
            "name": "50ml Round Raita Cup with Leakproof Lid",
            "sku": "PKG-ACC-001",
            "category": "ACCOMPANIMENT",
            "material": "Food Grade PP",
            "capacity": "50ml",
            "unit": "pcs",
            "current_stock": 650.0,
            "minimum_stock": 200.0,
            "reorder_level": 400.0,
            "purchase_cost": 1.40,
            "supplier": "PlastoPack Industries",
            "storage_location": "Aisle P-2, Bin 1",
            "description": "Snap-on tamper-proof container for boondi & cucumber raita.",
        },
        {
            "name": "60ml Salan Gravy Spout Pouch",
            "sku": "PKG-ACC-002",
            "category": "ACCOMPANIMENT",
            "material": "Aluminum Multi-layer Foil",
            "capacity": "60ml",
            "unit": "pcs",
            "current_stock": 590.0,
            "minimum_stock": 200.0,
            "reorder_level": 350.0,
            "purchase_cost": 2.10,
            "supplier": "FlexiPack Solutions",
            "storage_location": "Aisle P-2, Bin 2",
            "description": "Heat-sealed leakproof pouch for Mirchi Ka Salan gravy.",
        },
        {
            "name": "100ml Sweet Gulab Jamun Dessert Cup",
            "sku": "PKG-ACC-003",
            "category": "ACCOMPANIMENT",
            "material": "Food Grade PP",
            "capacity": "100ml",
            "unit": "pcs",
            "current_stock": 260.0,
            "minimum_stock": 100.0,
            "reorder_level": 180.0,
            "purchase_cost": 2.20,
            "supplier": "PlastoPack Industries",
            "storage_location": "Aisle P-2, Bin 3",
            "description": "Clear round cup with snap lid for syrupy Shahi Gulab Jamun and desserts.",
        },
        {
            "name": "Eco Wooden Biryani Cutlery Kit",
            "sku": "PKG-CUT-001",
            "category": "CUTLERY",
            "material": "Birch Wood",
            "capacity": "Standard",
            "unit": "pack",
            "current_stock": 780.0,
            "minimum_stock": 250.0,
            "reorder_level": 500.0,
            "purchase_cost": 3.80,
            "supplier": "BioSpoon India",
            "storage_location": "Aisle P-3, Shelf A",
            "description": "Individually wrapped kit: 1 wooden fork, 1 wooden spoon, 1 napkin, 1 toothpick.",
        },
        {
            "name": "Embossed 2-Ply Panna Paper Napkins (Pack of 50)",
            "sku": "PKG-CUT-002",
            "category": "CUTLERY",
            "material": "Virgin Pulp",
            "capacity": "50 pcs/pack",
            "unit": "pack",
            "current_stock": 38.0,
            "minimum_stock": 20.0,
            "reorder_level": 40.0,
            "purchase_cost": 22.00,
            "supplier": "CleanSoft Paper",
            "storage_location": "Aisle P-3, Shelf B",
            "description": "Gold printed brand logo napkins for counter and takeaway packings.",
        },
        {
            "name": "Tamper-Evident Holographic Security Tape (500m)",
            "sku": "PKG-SEA-001",
            "category": "SEALING_LABEL",
            "material": "BOPP Adhesive",
            "capacity": "500m",
            "unit": "roll",
            "current_stock": 12.0,
            "minimum_stock": 5.0,
            "reorder_level": 10.0,
            "purchase_cost": 240.00,
            "supplier": "SafeTape Security",
            "storage_location": "Packing Counter Top",
            "description": "Leaves 'VOID' residue if peeled, guarantees zero food tampering during delivery.",
        },
        {
            "name": "Heavy Aluminum Foil Sealing Wrap (100m Roll)",
            "sku": "PKG-SEA-002",
            "category": "SEALING_LABEL",
            "material": "Food Grade Aluminum",
            "capacity": "100m",
            "unit": "roll",
            "current_stock": 6.0,
            "minimum_stock": 5.0,
            "reorder_level": 10.0,
            "purchase_cost": 350.00,
            "supplier": "HindAlum Foils",
            "storage_location": "Packing Counter Top",
            "description": "18-micron heavy aluminum foil for heat retention during transport.",
        },
    ]

    item_map = {}
    for data in packaging_samples:
        item = PackagingItem(**data, is_active=True)
        db.add(item)
        db.flush()
        item_map[item.sku] = item

        tx = PackagingTransaction(
            packaging_item_id=item.id,
            transaction_type="STOCK_IN",
            quantity=item.current_stock,
            stock_before=0.0,
            stock_after=item.current_stock,
            unit_cost=item.purchase_cost,
            total_cost=round(item.current_stock * item.purchase_cost, 2),
            reference_no="OPENING_STOCK",
            notes="Opening inventory balance for packaging items",
        )
        db.add(tx)

    rules_data = [
        {
            "dish_category": "Dum Biryani",
            "portion_size": "500g",
            "sku": "PKG-CON-001",
            "qty": 1.0,
            "desc": "1x 500ml Bowl for 500g Biryani",
        },
        {
            "dish_category": "Dum Biryani",
            "portion_size": "1kg",
            "sku": "PKG-CON-002",
            "qty": 1.0,
            "desc": "1x 1000ml Bowl for 1kg Biryani",
        },
        {
            "dish_category": "Dum Biryani",
            "portion_size": "ALL",
            "sku": "PKG-ACC-001",
            "qty": 1.0,
            "desc": "1x Raita Cup per Biryani",
        },
        {
            "dish_category": "Dum Biryani",
            "portion_size": "ALL",
            "sku": "PKG-ACC-002",
            "qty": 1.0,
            "desc": "1x Salan Pouch per Biryani",
        },
        {
            "dish_category": "Starters & Kebabs",
            "portion_size": "ALL",
            "sku": "PKG-CON-001",
            "qty": 1.0,
            "desc": "1x 500ml Container for Starters",
        },
        {
            "dish_category": "Desserts",
            "portion_size": "ALL",
            "sku": "PKG-ACC-003",
            "qty": 1.0,
            "desc": "1x Dessert Cup for Sweets",
        },
        {
            "dish_category": "ALL_ORDERS",
            "portion_size": "ALL",
            "sku": "PKG-CUT-001",
            "qty": 1.0,
            "desc": "1x Wooden Cutlery Kit per Order",
        },
        {
            "dish_category": "ALL_ORDERS",
            "portion_size": "ALL",
            "sku": "PKG-BAG-002",
            "qty": 1.0,
            "desc": "1x Kraft Delivery Bag per Order",
        },
    ]

    for r in rules_data:
        target_item = item_map.get(r["sku"])
        if target_item:
            rule = PackagingConsumptionRule(
                dish_category=r["dish_category"],
                portion_size=r["portion_size"],
                packaging_item_id=target_item.id,
                quantity_per_order_unit=r["qty"],
                description=r["desc"],
                is_active=True,
            )
            db.add(rule)

    db.commit()
    logger.info("Successfully seeded authentic Panna Biryani packaging items, stock, and rules.")


def seed_notifications_and_restock_data(db: Session) -> None:
    """Seed initial stock breach alerts and sample restock purchase orders if empty (Phase 9)."""
    from app.models.restock_order import RestockOrder, RestockOrderItem, RestockOrderStatus, RestockOrderTarget
    from app.services.notification_service import NotificationService

    # 1. Run live stock breach scan to generate notifications for current inventory/packaging
    NotificationService.scan_and_generate_stock_alerts(db)

    # 2. Seed sample restock purchase orders if empty
    if db.query(RestockOrder).count() == 0:
        logger.info("Seeding initial Restock Purchase Orders...")

        po1 = RestockOrder(
            po_number="PO-20261001-1042",
            supplier_name="Royal Agro Traders",
            supplier_contact="+91 98220 12345",
            status=RestockOrderStatus.ORDERED.value,
            target_type=RestockOrderTarget.INVENTORY.value,
            total_estimated_cost=13500.0,
            notes="Weekly replenishment for Daawat Basmati Rice and Shahi Masala stock deficit.",
            created_by_name="Ramesh Sharma (Head Chef)",
            ordered_at=datetime.now(UTC) - timedelta(days=2),
            items=[
                RestockOrderItem(
                    item_type="INVENTORY",
                    item_id=1,
                    item_name="Daawat Basmati Biryani Rice",
                    item_sku="ING-RICE-01",
                    unit="kg",
                    current_stock=14.5,
                    reorder_threshold=25.0,
                    suggested_quantity=50.0,
                    ordered_quantity=50.0,
                    unit_cost=140.0,
                    total_cost=7000.0,
                    is_received=False,
                ),
                RestockOrderItem(
                    item_type="INVENTORY",
                    item_id=3,
                    item_name="Panna Special Shahi Masala",
                    item_sku="ING-SPICE-01",
                    unit="kg",
                    current_stock=3.2,
                    reorder_threshold=8.0,
                    suggested_quantity=10.0,
                    ordered_quantity=10.0,
                    unit_cost=650.0,
                    total_cost=6500.0,
                    is_received=False,
                ),
            ],
        )
        db.add(po1)

        po2 = RestockOrder(
            po_number="PO-20260928-8921",
            supplier_name="EcoPackaging India",
            supplier_contact="+91 94450 67890",
            status=RestockOrderStatus.RECEIVED.value,
            target_type=RestockOrderTarget.PACKAGING.value,
            total_estimated_cost=5410.0,
            notes="Weekend bulk order for 500ml biryani bowls and kraft delivery carry bags.",
            created_by_name="Sunil Rao (Kitchen Store Manager)",
            ordered_at=datetime.now(UTC) - timedelta(days=6),
            received_at=datetime.now(UTC) - timedelta(days=4),
            items=[
                RestockOrderItem(
                    item_type="PACKAGING",
                    item_id=1,
                    item_name="500ml Microwavable Biryani Bowl with Snap Lid",
                    item_sku="PKG-CON-001",
                    unit="pcs",
                    current_stock=280.0,
                    reorder_threshold=200.0,
                    suggested_quantity=500.0,
                    ordered_quantity=500.0,
                    unit_cost=6.50,
                    total_cost=3250.0,
                    is_received=True,
                ),
                RestockOrderItem(
                    item_type="PACKAGING",
                    item_id=5,
                    item_name="Heavy-Duty Brown Kraft Biryani Carry Bag (Large)",
                    item_sku="PKG-BAG-001",
                    unit="pcs",
                    current_stock=340.0,
                    reorder_threshold=300.0,
                    suggested_quantity=300.0,
                    ordered_quantity=300.0,
                    unit_cost=7.20,
                    total_cost=2160.0,
                    is_received=True,
                ),
            ],
        )
        db.add(po2)
        db.commit()
        logger.info("Successfully seeded Restock Purchase Orders and stock alerts.")
