"""Seed website storefront data (config, payment methods, promocodes, website menu)."""
import json

from sqlalchemy.orm import Session

from app.core.logging import logger
from app.models.menu import MenuCategory, MenuItem, MenuItemPortion
from app.models.storefront import PaymentMethodConfig, PromoCode, StorefrontConfig
from app.services.storefront_service import DEFAULT_STOREFRONT_CONFIG


def _portion(size, grams, serves, base, original=None):
    return {
        "portion_size": size,
        "weight_grams": grams,
        "serves_persons": serves,
        "cost_price": round(base * 0.55),
        "base_price": base,
        "original_price": original,
        "zomato_price": round(base * 1.22),
        "swiggy_price": round(base * 1.20),
    }


def seed_storefront_config(db: Session) -> None:
    if db.query(StorefrontConfig).count() == 0:
        db.add(StorefrontConfig(**DEFAULT_STOREFRONT_CONFIG))
        logger.info("Seeded default storefront config")
    if db.query(PaymentMethodConfig).count() == 0:
        db.add(PaymentMethodConfig(key="online", label="Online Payment (UPI, Cards, Netbanking)",
                                   description="Instant confirmation via Google Pay, PhonePe, Paytm or Cards",
                                   enabled=True, display_order=1))
        db.add(PaymentMethodConfig(key="cash_on_delivery", label="Cash on Delivery (COD)",
                                   description="Pay cash or UPI upon handover", enabled=True, display_order=2))
        logger.info("Seeded default payment methods")
    if db.query(PromoCode).count() == 0:
        db.add_all([
            PromoCode(code="FIRSTPANNA", title="First Order Special Gift",
                      subtitle="A Little Extra Love for Your First Celebration",
                      description="Order directly from our website and get a complimentary Shahi Dessert on your first order of ₹299 or more.",
                      discount_type="free_item", discount_value=89,
                      free_item_name="Complimentary Shahi Brownie Sweet",
                      min_order_value=299, badge="Special Welcome Gift", active=True),
            PromoCode(code="FAMILY100", title="Family Pack Savings", subtitle="More Food, More Happiness",
                      description="Get flat ₹100 instant discount on Family & Saver Packs when ordering for gatherings.",
                      discount_type="fixed", discount_value=100, min_order_value=999, badge="Save ₹100", active=True),
            PromoCode(code="FREEDEL", title="Free Doorstep Delivery", subtitle="Complimentary Delivery in Surat",
                      description="Enjoy zero delivery fee on all orders of ₹800 and above anywhere within our Surat delivery network.",
                      discount_type="free_delivery", discount_value=49, min_order_value=800, badge="Free Delivery", active=True),
        ])
        logger.info("Seeded default promo codes")
    db.commit()


def _item_meta(**kwargs) -> str:
    return json.dumps(kwargs)


def _biryani_meta(tagline, short, category, category_label, spice_level, ingredients, allergens, prep, serving, reheat, nutrition):
    return _item_meta(
        tagline=tagline, short_description=short, category=category, category_label=category_label,
        spice_level=spice_level, ingredients=ingredients, allergens=allergens,
        preparation_notes=prep, serving_suggestions=serving, reheating_tips=reheat,
        nutrition_info=nutrition, popular_500g=True,
    )


WEBSITE_MENU = [
    {
        "category": "Signature Dum Biryanis", "slug": "signature-dum-biryanis",
        "description": "4 varieties of authentic dum biryani", "display_order": 1,
        "items": [
            {
                "name": "Panna Veg Dum Biryani", "slug": "panna-veg-dum-biryani",
                "description": "Classic dum-cooked basmati rice layered with garden-fresh vegetables, whole Indian spices, and golden caramelized onions. Slow-cooked under seal for hours to lock in natural aromas and delicate flavours. 100% pure vegetarian.",
                "is_veg": True, "spice_level": "MEDIUM", "prep_minutes": 45, "badge": "Best Seller",
                "image_url": "/products/veg-dum.jpg", "display_order": 1,
                "metadata": _biryani_meta(
                    "Classic Dum Cooking with Handpicked Vegetables",
                    "Fresh vegetables, aromatic spices & authentic taste.",
                    "veg-dum", "Veg Dum", "Medium",
                    ["Aged Royal Basmati Rice", "Fresh French Beans", "Green Peas", "Carrots & Potatoes", "Pure Desi Ghee", "Caramelized Fried Onions (Birista)", "Green Cardamom & Star Anise", "Fresh Mint & Coriander", "Kashmiri Saffron Infusion"],
                    ["Milk (Ghee)"],
                    "Slow cooked under sealed dum for 45 minutes with dough seal to trap steam.",
                    "Enjoy piping hot with our chilled Boondi Raita and Mint Chutney.",
                    "Warm in a microwave with 1 tsp of water or steam gently in a covered pan for 3 minutes.",
                    {"calories": "460 kcal / 250g", "protein": "9g", "carbs": "72g", "fat": "14g"},
                ),
                "portions": [
                    _portion("250g", 250, "Serves 1 person", 149),
                    _portion("500g", 500, "Serves 1-2 people", 249),
                    _portion("750g", 750, "Serves 2-3 people", 349),
                    _portion("1kg", 1000, "Serves 3-4 people", 499),
                ],
            },
            {
                "name": "Panna Paneer Dum Biryani", "slug": "panna-paneer-dum-biryani",
                "description": "Fragrant dum rice layered with rich paneer preparation and aromatic spices. Fresh malai paneer cubes marinated in spiced curd and herbs, layered with long-grain basmati, and dum-cooked to melting perfection.",
                "is_veg": True, "spice_level": "MEDIUM", "prep_minutes": 45, "badge": "Best Seller",
                "image_url": "/products/paneer-dum.jpg", "display_order": 2,
                "metadata": _biryani_meta(
                    "Succulent Malai Paneer Infused with Rich Royal Spices",
                    "Soft paneer, rich spices, royal flavour.",
                    "paneer", "Paneer Dum", "Medium",
                    ["Fresh Farm Malai Paneer Cubes", "Extra-long Basmati Rice", "Pure Desi Cow Ghee", "Hung Curd Marinade", "Caramelized Onion Birista", "Whole Roasted Spices", "Fresh Mint Leaves", "Coriander & Saffron Milk"],
                    ["Milk / Dairy (Paneer & Ghee)"],
                    "Paneer is marinated in thick spice blend before dum layering to keep it moist and soft.",
                    "Pairs wonderfully with seasoned onion salad and creamy cucumber raita.",
                    "Warm gently in microwave for 90 seconds. Avoid overheating to keep paneer tender.",
                    {"calories": "530 kcal / 250g", "protein": "16g", "carbs": "68g", "fat": "21g"},
                ),
                "portions": [
                    _portion("250g", 250, "Serves 1 person", 169),
                    _portion("500g", 500, "Serves 1-2 people", 279),
                    _portion("750g", 750, "Serves 2-3 people", 399),
                    _portion("1kg", 1000, "Serves 3-4 people", 549),
                ],
            },
            {
                "name": "Panna Hyderabadi Dum Biryani", "slug": "panna-hyderabadi-dum-biryani",
                "description": "Green-style Hyderabadi veg dum biryani with aromatic herbs and a rich green gravy. Prepared with a signature mint, green chili, and coriander marinade that coats the vegetables and basmati rice with distinctive zest and warmth.",
                "is_veg": True, "spice_level": "MEDIUM", "prep_minutes": 45, "badge": "New",
                "image_url": "/products/hyderabadi-dum.jpg", "display_order": 3,
                "metadata": _biryani_meta(
                    "Green Herb Masala Infusion with Hyderabadi Elegance",
                    "Green gravy, green vegetables, rich & aromatic.",
                    "hyderabadi", "Hyderabadi", "Medium-Spicy",
                    ["Select Aged Basmati Rice", "Green Herb Paste (Fresh Mint, Coriander, Green Chilies)", "Cauliflower Florets & Potatoes", "French Beans & Green Peas", "Pure Ghee & Cold-pressed Oil", "Clove, Cinnamon & Black Cardamom", "Fried Brown Onions"],
                    ["Milk (Ghee)"],
                    "Infused with cold-ground green herb reduction for authentic nizami aroma.",
                    "Serve with cool Boondi Raita to balance the fragrant spices.",
                    "Cover and steam or microwave for 2 minutes with lid slightly ajar.",
                    {"calories": "475 kcal / 250g", "protein": "10g", "carbs": "70g", "fat": "15g"},
                ),
                "portions": [
                    _portion("250g", 250, "Serves 1 person", 159),
                    _portion("500g", 500, "Serves 1-2 people", 269),
                    _portion("750g", 750, "Serves 2-3 people", 379),
                    _portion("1kg", 1000, "Serves 3-4 people", 529),
                ],
            },
            {
                "name": "Panna Royal Dum Biryani", "slug": "panna-royal-dum-biryani",
                "description": "Smoky, rich and finished with cashews. Our master chef special biryani combines rich layered spices with gentle dhungar smoke, topped lavishly with ghee-roasted whole cashews and toasted almonds.",
                "is_veg": True, "spice_level": "MEDIUM", "prep_minutes": 60, "badge": "Premium",
                "image_url": "/products/royal-dum.jpg", "display_order": 4,
                "metadata": _biryani_meta(
                    "Smoky Dum Infusion Finished with Golden Roasted Cashews",
                    "Smoky flavour, premium cashew, truly royal.",
                    "royal", "Royal Dum", "Medium",
                    ["Premium Daawat Super Basmati", "Roasted Whole Cashews in Desi Ghee", "Slivered Almonds", "Golden Brown Onions", "Natural Wood Charcoal Smoke Infusion (Dhungar)", "Selected Royal Vegetables & Saffron", "Mace, Nutmeg, Rose Petals"],
                    ["Tree Nuts (Cashews, Almonds)", "Milk (Ghee)"],
                    "Smoked with pure cow ghee over lit charcoal to impart subtle royal aroma.",
                    "Best enjoyed with cold pomegranate raita and spicy sliced red onions.",
                    "Warm in a preheated oven at 160°C for 5 minutes or microwave gently for 2 minutes.",
                    {"calories": "560 kcal / 250g", "protein": "14g", "carbs": "69g", "fat": "24g"},
                ),
                "portions": [
                    _portion("250g", 250, "Serves 1 person", 189),
                    _portion("500g", 500, "Serves 1-2 people", 319),
                    _portion("750g", 750, "Serves 2-3 people", 449),
                    _portion("1kg", 1000, "Serves 3-4 people", 629),
                ],
            },
        ],
    },
    {
        "category": "Combos & Family Packs", "slug": "combos",
        "description": "Combo packs for gatherings", "display_order": 2,
        "items": [
            {
                "name": "Family Pack", "slug": "combo-family-pack",
                "description": "2 x 500g Handi Biryani of your choice + 2 Fresh Raita Bowls + 2 Mint Chutney. Feeds 3 to 4 people comfortably with great savings.",
                "is_veg": True, "spice_level": "MEDIUM", "prep_minutes": 45, "badge": "Save 17%",
                "image_url": "/combos/family-pack.jpg", "display_order": 1,
                "metadata": _item_meta(kind="combo", tagline="The perfect celebration feast for family dinners",
                                       items_summary="2 × 500g Biryani + 2 Raita + 2 Chutney", discount_percent=17,
                                       included_items=["2 × 500g Dum Biryani (Veg Dum / Paneer / Hyderabadi)", "2 × Fresh Spiced Raita Bowls", "2 × Tangy Mint Chutney", "Seasoned Onion Salad & Cutlery"]),
                "portions": [_portion("Serves 3-4 People", None, "Serves 3-4 People", 999, original=1200)],
            },
            {
                "name": "Saver Pack", "slug": "combo-saver-pack",
                "description": "3 x 250g Handi Biryanis allowing you to taste different styles + 3 Fresh Raita Bowls + 3 Mint Chutney.",
                "is_veg": True, "spice_level": "MEDIUM", "prep_minutes": 45, "badge": "Save 21%",
                "image_url": "/combos/saver-pack.jpg", "display_order": 2,
                "metadata": _item_meta(kind="combo", tagline="Variety tasting pack for biryani enthusiasts",
                                       items_summary="3 × 250g Biryani + 3 Raita + 3 Chutney", discount_percent=21,
                                       included_items=["3 × 250g Dum Biryani (Taste 3 different flavours)", "3 × Chilled Raita Bowls", "3 × Fresh Mint Chutney", "2 × Fresh Onion Salads"]),
                "portions": [_portion("Serves 4-5 People", None, "Serves 4-5 People", 1299, original=1650)],
            },
        ],
    },
    {
        "category": "Raitas, Chutneys & Sweets", "slug": "extras",
        "description": "Sides & accompaniments", "display_order": 3,
        "items": [
            {"name": "Raita (Bowl)", "slug": "extra-raita-bowl",
             "description": "Creamy fresh curd with boondi, roasted cumin & pomegranate.",
             "is_veg": True, "image_url": "/extras/raita.jpg", "display_order": 1, "badge": None,
             "metadata": _item_meta(kind="extra", extra_category="raita", is_popular=True),
             "portions": [_portion("Bowl", None, "1 Bowl", 49)]},
            {"name": "Mint Chutney (Bowl)", "slug": "extra-mint-chutney",
             "description": "Freshly ground mint, fresh coriander, green chilies & lemon.",
             "is_veg": True, "image_url": "/extras/mint-chutney.jpg", "display_order": 2, "badge": None,
             "metadata": _item_meta(kind="extra", extra_category="chutney", is_popular=True),
             "portions": [_portion("Bowl", None, "1 Bowl", 29)]},
            {"name": "Extra Onion", "slug": "extra-onion",
             "description": "Spiced crunchy red onion rings tossed in lemon & masala.",
             "is_veg": True, "image_url": "/extras/extra-onion.jpg", "display_order": 3, "badge": None,
             "metadata": _item_meta(kind="extra", extra_category="sides"),
             "portions": [_portion("Bowl", None, "1 Bowl", 19)]},
            {"name": "Extra Cashew (Royal)", "slug": "extra-cashew",
             "description": "Generous bowl of whole cashews roasted in pure desi ghee.",
             "is_veg": True, "image_url": "/extras/extra-cashew.jpg", "display_order": 4, "badge": None,
             "metadata": _item_meta(kind="extra", extra_category="sides"),
             "portions": [_portion("Bowl", None, "1 Bowl", 39)]},
            {"name": "Shahi Brownie Sweet", "slug": "extra-shahi-dessert",
             "description": "Decadent rich dark chocolate walnut fudge brownie with silver leaf.",
             "is_veg": True, "image_url": "/offers/dessert.jpg", "display_order": 5, "badge": None,
             "metadata": _item_meta(kind="extra", extra_category="sweet", is_popular=True),
             "portions": [_portion("Single", None, "1 Piece", 89)]},
        ],
    },
]


def seed_website_menu(db: Session) -> None:
    """Insert the real website menu into the CRM if its categories are missing."""
    seeded_any = False
    for cat_data in WEBSITE_MENU:
        existing = db.query(MenuCategory).filter_by(slug=cat_data["slug"]).first()
        if existing is not None:
            continue
        cat = MenuCategory(
            name=cat_data["category"], slug=cat_data["slug"],
            description=cat_data["description"], display_order=cat_data["display_order"], is_active=True,
        )
        db.add(cat)
        db.flush()
        for itm in cat_data["items"]:
            item = MenuItem(
                category_id=cat.id, name=itm["name"], slug=itm["slug"],
                description=itm["description"], is_veg=itm.get("is_veg", True),
                spice_level=itm.get("spice_level", "MEDIUM"),
                preparation_time_minutes=itm.get("prep_minutes", 30),
                image_url=itm.get("image_url"), badge=itm.get("badge"),
                metadata_json=itm.get("metadata"),
                is_available=True, is_active=True, display_order=itm.get("display_order", 0),
            )
            db.add(item)
            db.flush()
            for p in itm["portions"]:
                db.add(MenuItemPortion(
                    menu_item_id=item.id, portion_size=p["portion_size"],
                    weight_grams=p.get("weight_grams"), serves_persons=p.get("serves_persons"),
                    cost_price=p["cost_price"], base_price=p["base_price"],
                    original_price=p.get("original_price"),
                    zomato_price=p["zomato_price"], swiggy_price=p["swiggy_price"],
                    is_available=True,
                ))
        seeded_any = True
    if seeded_any:
        db.commit()
        logger.info("Seeded website menu categories into CRM menu catalog")
