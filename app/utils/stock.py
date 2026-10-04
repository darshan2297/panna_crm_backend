"""Shared stock urgency classification used by inventory, packaging, restock, and notifications."""

from __future__ import annotations

from enum import StrEnum


class StockStatus(StrEnum):
    IN_STOCK = "IN_STOCK"
    LOW_STOCK = "LOW_STOCK"
    CRITICAL = "CRITICAL"
    OUT_OF_STOCK = "OUT_OF_STOCK"

    # Alias kept for inventory filter compatibility
    CRITICAL_STOCK = "CRITICAL_STOCK"


STATUS_PRIORITY = {
    StockStatus.OUT_OF_STOCK.value: 0,
    StockStatus.CRITICAL.value: 1,
    StockStatus.CRITICAL_STOCK.value: 1,
    StockStatus.LOW_STOCK.value: 2,
    StockStatus.IN_STOCK.value: 3,
}


def classify_stock(
    current: float,
    minimum: float,
    reorder_level: float | None = None,
) -> str:
    """
    Classify stock urgency.

    Returns one of: OUT_OF_STOCK, CRITICAL, LOW_STOCK, IN_STOCK.
    When reorder_level is provided and current is above reorder, returns IN_STOCK
    even if below other thresholds would not apply (caller typically filters first).
    """
    if current <= 0:
        return StockStatus.OUT_OF_STOCK.value
    if current <= minimum:
        return StockStatus.CRITICAL.value
    if reorder_level is not None and current <= reorder_level:
        return StockStatus.LOW_STOCK.value
    if reorder_level is None and current <= minimum * 1.5:
        return StockStatus.LOW_STOCK.value
    return StockStatus.IN_STOCK.value


def needs_restock(current: float, reorder_level: float) -> bool:
    """True when current stock is at or below the reorder threshold."""
    return current <= reorder_level


def suggest_reorder_qty(
    current: float,
    reorder_level: float,
    *,
    min_qty: float = 1.0,
    whole_units: bool = False,
) -> float:
    """
    Suggest a replenishment quantity targeting ~2x reorder level.

    Packaging often uses whole_units=True with a higher min_qty floor.
    """
    raw = max(reorder_level * 2 - current, min_qty)
    if whole_units:
        return float(round(raw, 0))
    return round(raw, 2)


def normalize_status_filter(status_filter: str | None) -> str | None:
    """Normalize CRITICAL_STOCK / CRITICAL aliases for query filters."""
    if not status_filter:
        return None
    upper = status_filter.strip().upper()
    if upper in ("CRITICAL", "CRITICAL_STOCK"):
        return "CRITICAL"
    return upper
