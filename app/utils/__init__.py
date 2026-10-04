"""Shared utilities for pagination, stock classification, SKU generation, and text helpers."""

from app.utils.pagination import build_paginated, calc_pages
from app.utils.sku import generate_sku
from app.utils.stock import StockStatus, classify_stock, suggest_reorder_qty
from app.utils.text import slugify

__all__ = [
    "StockStatus",
    "build_paginated",
    "calc_pages",
    "classify_stock",
    "generate_sku",
    "slugify",
    "suggest_reorder_qty",
]
