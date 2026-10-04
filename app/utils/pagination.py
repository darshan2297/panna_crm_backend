"""Pagination helpers shared across services and routers."""

from __future__ import annotations

from collections.abc import Sequence
from typing import TypeVar

from app.schemas.common import PaginatedResponse

T = TypeVar("T")


def calc_pages(total: int, page_size: int) -> int:
    """Return total page count (minimum 1 when total is 0)."""
    if page_size <= 0:
        return 1
    if total <= 0:
        return 1
    return (total + page_size - 1) // page_size


def build_paginated(
    items: Sequence[T] | list[T],
    total: int,
    page: int,
    page_size: int,
) -> PaginatedResponse[T]:
    """Build a consistent PaginatedResponse envelope."""
    return PaginatedResponse(
        total=total,
        page=page,
        page_size=page_size,
        pages=calc_pages(total, page_size),
        items=list(items),
    )
