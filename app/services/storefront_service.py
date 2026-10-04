import json
import os
import uuid

from fastapi import Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session

from app.models.menu import MenuCategory, MenuItem
from app.models.storefront import PaymentMethodConfig, PromoCode, StorefrontConfig
from app.schemas.storefront import (
    PaymentMethodCreate,
    PaymentMethodUpdate,
    PromoCodeCreate,
    PromoCodeUpdate,
    StorefrontConfigUpdate,
)

DEFAULT_STOREFRONT_CONFIG = {
    "logo_url": "/brand/panna-logo.png",
    "banner_url": "/hero/panna-hero-banner.jpg",
    "banner_mobile_url": "/hero/panna-hero-mobile.jpg",
    "gift_section_enabled": True,
    "gift_bg_url": "/offers/first-order-gift-banner.jpg",
    "bulk_bg_url": "/bulk/bulk-banner-bg.webp",
    "delivery_enabled": True,
    "pickup_enabled": True,
    "delivery_fee": 49.0,
    "free_delivery_enabled": True,
    "free_delivery_threshold": 800.0,
    "brand_name": "PANNA BIRYANI",
    "brand_tagline": "Biryani Made For Sharing",
    "address_line": "Shop 14, Royal Heritage Arcade, Near VIP Circle, Vesu",
    "area": "Vesu",
    "city": "Surat",
    "pincode": "395007",
    "google_maps_url": "https://maps.google.com/?q=Surat+Gujarat",
    "phone": "+919876543210",
    "whatsapp": "919876543210",
    "email": "hello@pannabiryani.in",
    "operating_hours": "Mon–Fri 5:00 PM – 11:00 PM, Sat–Sun 11:00 AM – 11:00 PM",
}


class StorefrontService:
    def __init__(self, db: Session):
        self.db = db

    # --- Storefront config (singleton) ---
    def get_config(self) -> StorefrontConfig:
        cfg = self.db.query(StorefrontConfig).first()
        if cfg is None:
            cfg = StorefrontConfig(**DEFAULT_STOREFRONT_CONFIG)
            self.db.add(cfg)
            self.db.commit()
            self.db.refresh(cfg)
        return cfg

    def update_config(self, payload: StorefrontConfigUpdate) -> StorefrontConfig:
        cfg = self.get_config()
        for key, value in payload.model_dump(exclude_unset=True).items():
            setattr(cfg, key, value)
        self.db.commit()
        self.db.refresh(cfg)
        return cfg

    # --- Payment methods ---
    def list_payment_methods(self) -> list[PaymentMethodConfig]:
        return (
            self.db.query(PaymentMethodConfig)
            .order_by(PaymentMethodConfig.display_order, PaymentMethodConfig.id)
            .all()
        )

    def create_payment_method(self, payload: PaymentMethodCreate) -> PaymentMethodConfig:
        if self.db.query(PaymentMethodConfig).filter_by(key=payload.key).first():
            raise HTTPException(status_code=400, detail="Payment method key already exists")
        pm = PaymentMethodConfig(**payload.model_dump())
        self.db.add(pm)
        self.db.commit()
        self.db.refresh(pm)
        return pm

    def update_payment_method(self, pm_id: int, payload: PaymentMethodUpdate) -> PaymentMethodConfig:
        pm = self.db.query(PaymentMethodConfig).filter_by(id=pm_id).first()
        if pm is None:
            raise HTTPException(status_code=404, detail="Payment method not found")
        for key, value in payload.model_dump(exclude_unset=True).items():
            setattr(pm, key, value)
        self.db.commit()
        self.db.refresh(pm)
        return pm

    def delete_payment_method(self, pm_id: int) -> None:
        pm = self.db.query(PaymentMethodConfig).filter_by(id=pm_id).first()
        if pm is None:
            raise HTTPException(status_code=404, detail="Payment method not found")
        self.db.delete(pm)
        self.db.commit()

    # --- Promo codes ---
    def list_promocodes(self) -> list[PromoCode]:
        return self.db.query(PromoCode).order_by(PromoCode.created_at.desc()).all()

    def create_promocode(self, payload: PromoCodeCreate) -> PromoCode:
        code = payload.code.strip().upper()
        if self.db.query(PromoCode).filter_by(code=code).first():
            raise HTTPException(status_code=400, detail="Promo code already exists")
        data = payload.model_dump()
        data["code"] = code
        pc = PromoCode(**data)
        self.db.add(pc)
        self.db.commit()
        self.db.refresh(pc)
        return pc

    def update_promocode(self, pc_id: int, payload: PromoCodeUpdate) -> PromoCode:
        pc = self.db.query(PromoCode).filter_by(id=pc_id).first()
        if pc is None:
            raise HTTPException(status_code=404, detail="Promo code not found")
        for key, value in payload.model_dump(exclude_unset=True).items():
            if key == "code" and value:
                value = value.strip().upper()
            setattr(pc, key, value)
        self.db.commit()
        self.db.refresh(pc)
        return pc

    def delete_promocode(self, pc_id: int) -> None:
        pc = self.db.query(PromoCode).filter_by(id=pc_id).first()
        if pc is None:
            raise HTTPException(status_code=404, detail="Promo code not found")
        self.db.delete(pc)
        self.db.commit()

    # --- Public menu data (website shape) ---
    def get_public_menu_data(self) -> dict:
        categories = (
            self.db.query(MenuCategory)
            .filter(MenuCategory.is_active == True)  # noqa: E712
            .order_by(MenuCategory.display_order)
            .all()
        )
        products, combos, extras = [], [], []
        for cat in categories:
            cat_kind = (cat.slug or "").lower()
            for item in cat.items:
                if not (item.is_active and item.is_available):
                    continue
                try:
                    meta = json.loads(item.metadata_json) if item.metadata_json else {}
                except Exception:
                    meta = {}
                portions = [p for p in item.portions if p.is_available]
                if cat_kind in ("combos", "combo-packs", "combos-family-sharing-packs") or meta.get("kind") == "combo":
                    if not portions:
                        continue
                    p = portions[0]
                    original = p.original_price or p.base_price
                    discount = meta.get("discount_percent")
                    if discount is None and original > p.base_price:
                        discount = round((original - p.base_price) / original * 100)
                    combos.append({
                        "id": item.slug,
                        "slug": item.slug.replace("combo-", ""),
                        "name": item.name,
                        "tagline": meta.get("tagline", ""),
                        "description": item.description or "",
                        "itemsSummary": meta.get("items_summary", ""),
                        "price": p.base_price,
                        "originalPrice": original,
                        "discountPercent": discount or 0,
                        "image": item.image_url or "",
                        "servesText": p.serves_persons or "",
                        "badge": item.badge or "",
                        "includedItems": meta.get("included_items", []),
                    })
                elif cat_kind in ("extras", "sides-accompaniments", "raitas-chutneys-sweets") or meta.get("kind") == "extra":
                    if not portions:
                        continue
                    p = portions[0]
                    extras.append({
                        "id": item.slug,
                        "name": item.name,
                        "description": item.description or "",
                        "price": p.base_price,
                        "image": item.image_url or "",
                        "category": meta.get("extra_category", "sides"),
                        "isPopular": bool(meta.get("is_popular", False)),
                    })
                else:
                    products.append({
                        "id": item.slug,
                        "slug": item.slug,
                        "name": item.name,
                        "tagline": meta.get("tagline", ""),
                        "shortDescription": meta.get("short_description", item.description or ""),
                        "description": item.description or "",
                        "image": item.image_url or "",
                        "category": meta.get("category", cat.slug),
                        "categoryLabel": meta.get("category_label", cat.name),
                        "vegetarian": bool(item.is_veg),
                        "available": bool(item.is_available),
                        "badge": item.badge or None,
                        "sizes": [
                            {
                                "id": p.portion_size,
                                "label": p.portion_size,
                                "weightGrams": p.weight_grams or 0,
                                "price": p.base_price,
                                "servesText": p.serves_persons or "",
                                "originalPrice": p.original_price,
                                "isPopular": bool(meta.get(f"popular_{p.portion_size}")),
                            }
                            for p in portions
                        ],
                        "ingredients": meta.get("ingredients", []),
                        "allergens": meta.get("allergens", []),
                        "spiceLevel": meta.get("spice_level", "Medium"),
                        "preparationNotes": meta.get("preparation_notes", ""),
                        "servingSuggestions": meta.get("serving_suggestions", ""),
                        "reheatingTips": meta.get("reheating_tips", ""),
                        "nutritionInfo": meta.get("nutrition_info"),
                    })
        return {"products": products, "combos": combos, "extras": extras}
