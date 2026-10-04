"""SKU generation helpers shared by inventory and packaging services."""

from __future__ import annotations

from collections.abc import Callable

from sqlalchemy.orm import Session

PACKAGING_CATEGORY_CODES = {
    "CONTAINER": "CON",
    "BAG": "BAG",
    "ACCOMPANIMENT": "ACC",
    "CUTLERY": "CUT",
    "SEALING_LABEL": "SEA",
    "OTHER": "OTH",
}


def category_code(category: str, *, mapped: bool = False) -> str:
    """Return a 3-letter category code for SKU generation."""
    if not category:
        return "GEN"
    if mapped:
        return PACKAGING_CATEGORY_CODES.get(category.upper(), "GEN")
    return category[:3].upper()


def generate_sku(
    db: Session,
    *,
    prefix: str,
    category: str,
    model,
    category_column,
    sku_column,
    use_category_map: bool = False,
    exists_check: Callable[[str], bool] | None = None,
) -> str:
    """
    Generate a unique SKU like ING-GRA-012 or PKG-CON-001.

    Falls back to total_count + 10 when the candidate already exists.
    """
    code = category_code(category, mapped=use_category_map)
    count = db.query(model).filter(category_column == category).count()
    candidate = f"{prefix}-{code}-{count + 1:03d}"

    if exists_check:
        exists = exists_check(candidate)
    else:
        exists = db.query(model).filter(sku_column == candidate).first() is not None

    if exists:
        total_count = db.query(model).count()
        candidate = f"{prefix}-{code}-{total_count + 10:03d}"
    return candidate
