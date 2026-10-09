import json
import os
import uuid
from datetime import datetime

from fastapi import Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session

from app.models.menu import MenuCategory, MenuItem
from app.models.storefront import (
    PaymentMethodConfig,
    PromoCode,
    PromoCodeUsage,
    PromoEvent,
    StorefrontConfig,
)
from app.schemas.storefront import (
    PaymentMethodCreate,
    PaymentMethodUpdate,
    PromoCodeCreate,
    PromoCodeUpdate,
    PromoCodeValidateRequest,
    PromoEventInput,
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
        try:
            return self.db.query(PromoCode).order_by(PromoCode.created_at.desc()).all()
        except Exception:
            # If table doesn't exist or has schema mismatch, return empty list
            return []

    def _apply_events(self, pc: PromoCode, events: list[PromoEventInput] | None) -> None:
        """Replace the promo's campaign windows. `events=None` leaves them untouched."""
        if events is None:
            return
        for ev in pc.events:
            self.db.delete(ev)
        pc.events = [
            PromoEvent(
                event_title=e.event_title.strip(),
                start_date=e.start_date,
                end_date=e.end_date,
            )
            for e in events
        ]

    def create_promocode(self, payload: PromoCodeCreate) -> PromoCode:
        code = payload.code.strip().upper()
        if self.db.query(PromoCode).filter_by(code=code).first():
            raise HTTPException(status_code=400, detail="Promo code already exists")
        data = payload.model_dump(exclude={"events"})
        data["code"] = code
        if isinstance(data.get("applicable_items"), list):
            data["applicable_items"] = json.dumps(data["applicable_items"])
        pc = PromoCode(**data)
        self._apply_events(pc, payload.events)
        self.db.add(pc)
        self.db.commit()
        self.db.refresh(pc)
        return pc

    def update_promocode(self, pc_id: int, payload: PromoCodeUpdate) -> PromoCode:
        pc = self.db.query(PromoCode).filter_by(id=pc_id).first()
        if pc is None:
            raise HTTPException(status_code=404, detail="Promo code not found")
        data = payload.model_dump(exclude_unset=True)
        events = data.pop("events", None)
        for key, value in data.items():
            if key == "code" and value:
                value = value.strip().upper()
            if key == "applicable_items" and isinstance(value, list):
                value = json.dumps(value)
            setattr(pc, key, value)
        if events is not None:
            self._apply_events(pc, payload.events)
        self.db.commit()
        self.db.refresh(pc)
        return pc

    def record_promocode_usage(self, promo_code_id: int, customer_phone: str, order_id: int | None) -> PromoCodeUsage:
        """Log a redemption so `per_user_limit` is enforced from real history.

        A unique index on (promo_code_id, customer_phone) means a second
        redemption for the same customer raises instead of double-counting.
        """
        phone = self._normalise_phone(customer_phone)
        if not phone:
            raise HTTPException(status_code=400, detail="A valid 10-digit phone is required")

        promo = self.db.query(PromoCode).filter_by(id=promo_code_id).first()
        if promo is None:
            raise HTTPException(status_code=404, detail="Promo code not found")

        already = (
            self.db.query(PromoCodeUsage)
            .filter_by(promo_code_id=promo_code_id, customer_phone=phone)
            .first()
        )
        if already is not None:
            raise HTTPException(
                status_code=409,
                detail="This promo code has already been used with this phone number",
            )

        usage = PromoCodeUsage(
            promo_code_id=promo_code_id,
            customer_phone=phone,
            order_id=order_id,
        )
        promo.used_count = (promo.used_count or 0) + 1
        self.db.add(usage)
        self.db.flush()
        self.db.commit()
        return usage

    @staticmethod
    def _normalise_phone(phone: str | None) -> str | None:
        """Reduce any phone format to the last 10 digits."""
        if not phone:
            return None
        digits = "".join(ch for ch in phone if ch.isdigit())
        return digits[-10:] if len(digits) >= 10 else None

    def _has_previous_order(self, phone_last10: str) -> bool:
        from app.models.order import Order

        return (
            self.db.query(Order)
            .filter(Order.customer_phone.like(f"%{phone_last10}"))
            .first()
            is not None
        )

    def _used_count_for_phone(self, promo_id: int, phone_last10: str) -> int:
        return (
            self.db.query(PromoCodeUsage)
            .filter_by(promo_code_id=promo_id, customer_phone=phone_last10)
            .count()
        )

    def validate_promocode(self, code: str, payload: PromoCodeValidateRequest) -> dict:
        pc = self.db.query(PromoCode).filter_by(code=code.strip().upper()).first()
        if pc is None or not pc.active:
            return {"valid": False, "reason": "Invalid or inactive promo code", "code": code}

        now = datetime.utcnow()
        phone = self._normalise_phone(payload.customer_phone)
        is_returning = bool(phone) and self._has_previous_order(phone)

        # --- Event windows ---
        # For single/multiple-event promos the code is live only inside at
        # least one selected campaign window.
        if pc.category in ("single_event", "multiple_event"):
            windows = [
                e
                for e in (pc.events or [])
                if e.start_date <= now <= e.end_date
            ]
            if not windows:
                return {
                    "valid": False,
                    "reason": "This offer is not active in any current event window",
                    "code": pc.code,
                }

        if pc.valid_from and now < pc.valid_from:
            return {"valid": False, "reason": "Promo code is not active yet", "code": pc.code}
        if pc.valid_until and now > pc.valid_until:
            return {"valid": False, "reason": "Promo code has expired", "code": pc.code}
        if pc.max_uses is not None and (pc.used_count or 0) >= pc.max_uses:
            return {"valid": False, "reason": "Promo code usage limit reached", "code": pc.code}

        # --- Customer eligibility (first_order_only / customer_type) ---
        # These need a phone; if none is supplied we cannot confirm, so the
        # caller is told to supply one rather than being waved through.
        needs_identity = pc.first_order_only or pc.customer_type in ("new", "returning")
        if needs_identity and not phone:
            return {
                "valid": False,
                "reason": "PHONE_REQUIRED",
                "code": pc.code,
                "requires_phone": True,
            }

        if pc.customer_type == "new" and is_returning:
            return {
                "valid": False,
                "reason": "This offer is only for first-time customers",
                "code": pc.code,
            }
        if pc.customer_type == "returning" and not is_returning:
            return {
                "valid": False,
                "reason": "This offer is only for returning customers",
                "code": pc.code,
            }
        if pc.first_order_only and is_returning:
            return {
                "valid": False,
                "reason": "This promo code is only valid for first-time customers",
                "code": pc.code,
            }

        # --- Per-user redemption limit, from real usage history ---
        if pc.per_user_limit is not None and phone:
            used_by_user = self._used_count_for_phone(pc.id, phone)
            if used_by_user >= pc.per_user_limit:
                return {
                    "valid": False,
                    "reason": "You have already used this promo code",
                    "code": pc.code,
                }

        # --- Thresholds: interpreted per `discount_on` ---
        # "quantity" => min/max count of units in cart
        # "amount"   => min/max cart value in ₹
        if pc.discount_on == "quantity":
            qty = payload.item_count or 0
            if pc.min_quantity is not None and qty < pc.min_quantity:
                return {
                    "valid": False,
                    "reason": f"Add at least {pc.min_quantity} item(s) to use this code",
                    "code": pc.code,
                }
            if pc.max_quantity is not None and qty > pc.max_quantity:
                return {
                    "valid": False,
                    "reason": f"This code applies to up to {pc.max_quantity} item(s) per order",
                    "code": pc.code,
                }
        else:
            value = payload.order_value or 0
            if value < (pc.min_order_value or 0):
                return {
                    "valid": False,
                    "reason": f"Minimum order value of ₹{pc.min_order_value} required",
                    "code": pc.code,
                }
            if pc.max_order_value is not None and value > pc.max_order_value:
                return {
                    "valid": False,
                    "reason": f"This code applies to orders up to ₹{pc.max_order_value}",
                    "code": pc.code,
                }

        # Legacy minimum_order_items still applies when explicitly set.
        if pc.minimum_order_items is not None and (payload.item_count or 0) < pc.minimum_order_items:
            return {"valid": False, "reason": f"Minimum {pc.minimum_order_items} item(s) required", "code": pc.code}

        if pc.applicable_items:
            try:
                applicable = [str(s).lower() for s in json.loads(pc.applicable_items)]
            except Exception:
                applicable = []
            cart_slugs = [str(s).lower() for s in (payload.cart_item_slugs or [])]
            if applicable and not any(s in applicable for s in cart_slugs):
                return {"valid": False, "reason": "Promo code does not apply to items in your cart", "code": pc.code}

        return {
            "valid": True,
            "reason": None,
            "code": pc.code,
            "discount_type": pc.discount_type,
            "discount_value": pc.discount_value,
            "free_item_name": pc.free_item_name,
            "min_order_value": pc.min_order_value,
        }

    def get_promocode_by_code(self, code: str) -> PromoCode | None:
        return self.db.query(PromoCode).filter_by(code=code.strip().upper()).first()

    def get_promocode_by_id(self, pc_id: int) -> PromoCode | None:
        return self.db.query(PromoCode).filter_by(id=pc_id).first()

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
                if not item.is_active:
                    continue
                try:
                    meta = json.loads(item.metadata_json) if item.metadata_json else {}
                except Exception:
                    meta = {}
                portions = [p for p in item.portions if p.is_available]
                # Include all active items even if unavailable, so frontend can show "Out of Stock"
                if not item.is_available:
                    # Still include in the menu but mark as unavailable
                    if cat_kind in ("combos", "combo-packs", "combos-family-sharing-packs") or meta.get("kind") == "combo":
                        combos.append({
                            "id": item.slug,
                            "slug": item.slug.replace("combo-", ""),
                            "name": item.name,
                            "tagline": meta.get("tagline", ""),
                            "description": item.description or "",
                            "itemsSummary": meta.get("items_summary", ""),
                            "price": 0,
                            "originalPrice": 0,
                            "discountPercent": 0,
                            "image": item.image_url or "",
                            "servesText": "",
                            "badge": "Out of Stock",
                            "includedItems": meta.get("included_items", []),
                            "available": False,
                        })
                    elif cat_kind in ("extras", "sides-accompaniments", "raitas-chutneys-sweets") or meta.get("kind") == "extra":
                        extras.append({
                            "id": item.slug,
                            "name": item.name,
                            "description": item.description or "",
                            "price": 0,
                            "image": item.image_url or "",
                            "category": meta.get("extra_category", "sides"),
                            "isPopular": False,
                            "available": False,
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
                            "available": False,
                            "badge": "Out of Stock",
                            "sizes": [],
                            "ingredients": meta.get("ingredients", []),
                            "allergens": meta.get("allergens", []),
                            "spiceLevel": meta.get("spice_level", "Medium"),
                            "preparationNotes": "",
                            "servingSuggestions": "",
                            "reheatingTips": "",
                            "nutritionInfo": None,
                        })
                    continue
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
