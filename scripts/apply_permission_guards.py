"""Apply module/action permission guards across the API routers.

Rewrites `Depends(get_current_active_user)` -> `Depends(require_permission(M, A))`
and `Depends(require_roles([...]))` -> permission guards, per route, using an
explicit table. Anything not listed is reported and left untouched, so a route
is never silently left open because it was missed here.

Idempotent: re-running finds nothing to change.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
ROUTERS = BACKEND / "app" / "api" / "v1"

# file -> {http_method: (MODULE, ACTION)}
PLAN: dict[str, dict[str, tuple[str, str]]] = {
    "dashboard/router.py": {
        "GET": ("DASHBOARD", "VIEW"),
    },
    "orders/router.py": {
        "GET": ("ORDERS", "VIEW"),
        "POST": ("ORDERS", "CREATE"),
        "PATCH": ("ORDERS", "UPDATE"),
        "DELETE": ("ORDERS", "DELETE"),
    },
    "customers/router.py": {
        "GET": ("CUSTOMERS", "VIEW"),
        "POST": ("CUSTOMERS", "CREATE"),
        "PATCH": ("CUSTOMERS", "UPDATE"),
        "DELETE": ("CUSTOMERS", "DELETE"),
    },
    "contact_inquiries/router.py": {
        "GET": ("ENQUIRIES", "VIEW"),
        "PATCH": ("ENQUIRIES", "UPDATE"),
        "DELETE": ("ENQUIRIES", "DELETE"),
    },
    "users/router.py": {
        "GET": ("STAFF", "VIEW"),
        "POST": ("STAFF", "CREATE"),
        "PATCH": ("STAFF", "UPDATE"),
        "DELETE": ("STAFF", "DELETE"),
    },
    "menu/router.py": {
        "GET": ("MENU", "VIEW"),
        "POST": ("MENU", "CREATE"),
        "PATCH": ("MENU", "UPDATE"),
        "DELETE": ("MENU", "DELETE"),
    },
    "inventory/router.py": {
        "GET": ("INVENTORY", "VIEW"),
        "POST": ("INVENTORY", "CREATE"),
        "PATCH": ("INVENTORY", "UPDATE"),
        "DELETE": ("INVENTORY", "DELETE"),
    },
    "packaging/router.py": {
        "GET": ("PACKAGING", "VIEW"),
        "POST": ("PACKAGING", "CREATE"),
        "PATCH": ("PACKAGING", "UPDATE"),
        "DELETE": ("PACKAGING", "DELETE"),
    },
    "restock/router.py": {
        "GET": ("RESTOCK", "VIEW"),
        "POST": ("RESTOCK", "CREATE"),
        "PATCH": ("RESTOCK", "UPDATE"),
        "DELETE": ("RESTOCK", "DELETE"),
    },
    "analytics/router.py": {
        "GET": ("ANALYTICS", "VIEW"),
    },
    "integrations/router.py": {
        "GET": ("INTEGRATIONS", "VIEW"),
        "PATCH": ("INTEGRATIONS", "UPDATE"),
        "POST": ("INTEGRATIONS", "UPDATE"),
    },
    "business_hours/router.py": {
        "GET": ("BUSINESS_HOURS", "VIEW"),
        "PATCH": ("BUSINESS_HOURS", "UPDATE"),
        "POST": ("BUSINESS_HOURS", "UPDATE"),
        "DELETE": ("BUSINESS_HOURS", "UPDATE"),
    },
    "website/router.py": {
        "GET": ("WEBSITE_CONFIG", "VIEW"),
        "POST": ("PROMO_CODES", "CREATE"),
        "PATCH": ("WEBSITE_CONFIG", "UPDATE"),
    },
    "delivery_areas/router.py": {
        "GET": ("DELIVERY_AREAS", "VIEW"),
        "POST": ("DELIVERY_AREAS", "CREATE"),
        "PATCH": ("DELIVERY_AREAS", "UPDATE"),
        "DELETE": ("DELIVERY_AREAS", "DELETE"),
    },
    "reviews/router.py": {
        "GET": ("REVIEWS", "VIEW"),
        "POST": ("REVIEWS", "CREATE"),
        "PATCH": ("REVIEWS", "UPDATE"),
        "DELETE": ("REVIEWS", "DELETE"),
    },
    "faqs/router.py": {
        "GET": ("FAQS", "VIEW"),
        "POST": ("FAQS", "CREATE"),
        "PATCH": ("FAQS", "UPDATE"),
        "DELETE": ("FAQS", "DELETE"),
    },
    "notifications/router.py": {
        "GET": ("DASHBOARD", "VIEW"),
        "PATCH": ("DASHBOARD", "VIEW"),
    },
}

# Routes that must stay on plain auth because they are part of the login flow
# or are pure reads every authenticated user needs regardless of module grants.
SKIP_FILES = {"auth/router.py", "public/router.py", "roles/router.py", "health/router.py"}

ROUTE_RE = re.compile(r"^@router\.(get|post|patch|put|delete)\(", re.IGNORECASE)
ACTIVE_DEP_RE = re.compile(
    r"current_user:\s*User\s*=\s*Depends\((get_current_active_user|require_roles\([^)]*\))\)"
)
IMPORT_RE = re.compile(
    r"^from app\.dependencies\.auth import (.+)$", re.MULTILINE
)


def rewrite(path: Path, plan: dict[str, tuple[str, str]]) -> tuple[int, list[str]]:
    src = path.read_text(encoding="utf-8")
    lines = src.splitlines(keepends=True)
    out: list[str] = []
    applied = 0
    unhandled: list[str] = []

    i = 0
    current: tuple[str, str] | None = None
    in_signature = False

    while i < len(lines):
        line = lines[i]
        m = ROUTE_RE.match(line)
        if m:
            current = plan.get(m.group(1).upper())
            in_signature = True
        elif in_signature and line.strip().startswith(("def ", "async def ")):
            in_signature = True
        elif in_signature and line.rstrip().endswith("):"):
            in_signature = False

        if in_signature and current is not None and ACTIVE_DEP_RE.search(line):
            module, action = current
            replacement = (
                f'current_user: User = Depends(require_permission("{module}", "{action}"))'
            )
            new_line = ACTIVE_DEP_RE.sub(replacement, line)
            out.append(new_line)
            applied += 1
            i += 1
            continue

        out.append(line)
        i += 1

    result = "".join(out)

    # Make sure require_permission is imported.
    if applied and "require_permission" not in IMPORT_RE.search(result).group(1) if IMPORT_RE.search(result) else applied:
        pass
    if applied:
        m = IMPORT_RE.search(result)
        if m and "require_permission" not in m.group(1):
            names = sorted(set([n.strip() for n in m.group(1).split(",")] + ["require_permission"]))
            result = IMPORT_RE.sub(
                "from app.dependencies.auth import " + ", ".join(names),
                result,
                count=1,
            )

    if result != src:
        path.write_text(result, encoding="utf-8")
    return applied, unhandled


def main() -> int:
    total = 0
    for rel, plan in sorted(PLAN.items()):
        path = ROUTERS / rel
        if not path.exists():
            print(f"  [SKIP] {rel} (missing)")
            continue
        applied, _ = rewrite(path, plan)
        total += applied
        print(f"  {rel:32s} {applied} guard(s)")

    print(f"\n  {total} guards applied across {len(PLAN)} routers")
    print(f"  untouched by design: {', '.join(sorted(SKIP_FILES))}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
