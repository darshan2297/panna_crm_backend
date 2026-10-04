"""Text helpers (slugify, etc.)."""

from __future__ import annotations

import re


def slugify(text: str) -> str:
    """Generate a clean URL-friendly slug from text."""
    clean = re.sub(r"[^\w\s-]", "", text).strip().lower()
    return re.sub(r"[-\s]+", "-", clean)
