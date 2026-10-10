"""Permission catalogue and role seeding.

Kept separate from the models so the module list, display labels and default
role bundles are defined in one place and shared by the API, the seeder and the
frontend roles matrix.
"""

from __future__ import annotations

from app.models.role import Module, PermissionAction, Role, RolePermission

# (module, label, actions that make sense for it)
# Modules that only hold configuration expose UPDATE rather than CREATE/DELETE,
# because "creating" a setting is just editing it.
MODULE_CATALOGUE: list[tuple[Module, str, list[PermissionAction]]] = [
    (Module.DASHBOARD, "Dashboard", [PermissionAction.VIEW]),
    (Module.ORDERS, "Orders", list(PermissionAction)),
    (Module.LIVE_ORDERS, "Live Kitchen Orders", [PermissionAction.VIEW, PermissionAction.UPDATE]),
    (Module.CUSTOMERS, "Customers", list(PermissionAction)),
    (Module.ENQUIRIES, "Enquiries", list(PermissionAction)),
    (Module.STAFF, "Staff", list(PermissionAction)),
    (Module.ROLES, "Roles & Permissions", list(PermissionAction)),
    (Module.MENU, "Menu", list(PermissionAction)),
    (Module.INVENTORY, "Inventory", list(PermissionAction)),
    (Module.PACKAGING, "Packaging", list(PermissionAction)),
    (Module.RESTOCK, "Restock", list(PermissionAction)),
    (Module.ANALYTICS, "Analytics", [PermissionAction.VIEW]),
    (Module.INTEGRATIONS, "Integrations", [PermissionAction.VIEW, PermissionAction.UPDATE]),
    (Module.BUSINESS_HOURS, "Business Hours", [PermissionAction.VIEW, PermissionAction.UPDATE]),
    (Module.WEBSITE_CONFIG, "Website Config", [PermissionAction.VIEW, PermissionAction.UPDATE]),
    (Module.PROMO_CODES, "Promo Codes", list(PermissionAction)),
    (Module.DELIVERY_AREAS, "Delivery Areas", list(PermissionAction)),
    (Module.REVIEWS, "Reviews", list(PermissionAction)),
    (Module.FAQS, "FAQs", list(PermissionAction)),
    (Module.SETTINGS, "Settings", [PermissionAction.VIEW, PermissionAction.UPDATE]),
]

ALL_ACTIONS = list(PermissionAction)
VIEW_ONLY = [PermissionAction.VIEW]


def grants_for(
    modules: list[Module],
    actions: list[PermissionAction] | None = None,
) -> list[RolePermission]:
    """Expand a module/action selection into concrete grant rows.

    `actions=None` means every action that module supports.
    """
    out: list[RolePermission] = []
    catalogue = {m: (label, acts) for m, label, acts in MODULE_CATALOGUE}
    for module in modules:
        supported = catalogue.get(module, (module.value, ALL_ACTIONS))[1]
        for action in actions or supported:
            if action in supported:
                out.append(RolePermission(module=module.value, action=action.value))
    return out


# Default bundles seeded on startup. `is_superuser` on Administrator is the
# lockout escape hatch; Manager and Staff carry ordinary grants.
DEFAULT_ROLES: list[dict] = [
    {
        "name": "Administrator",
        "description": "Full access to every module, including staff and roles.",
        "is_system": True,
        "is_superuser": True,
        "modules": [m for m, _, _ in MODULE_CATALOGUE],
        "actions": ALL_ACTIONS,
    },
    {
        "name": "Manager",
        "description": "Runs day-to-day operations; no staff or role administration.",
        "is_system": True,
        "is_superuser": False,
        "modules": [
            Module.DASHBOARD,
            Module.ORDERS,
            Module.LIVE_ORDERS,
            Module.CUSTOMERS,
            Module.ENQUIRIES,
            Module.MENU,
            Module.INVENTORY,
            Module.PACKAGING,
            Module.RESTOCK,
            Module.ANALYTICS,
            Module.INTEGRATIONS,
            Module.BUSINESS_HOURS,
            Module.WEBSITE_CONFIG,
            Module.PROMO_CODES,
            Module.DELIVERY_AREAS,
            Module.REVIEWS,
            Module.FAQS,
        ],
        # Managers may edit and remove operational records but not delete menus
        # or configuration, which would break the storefront.
        "actions": [PermissionAction.VIEW, PermissionAction.CREATE, PermissionAction.UPDATE],
    },
    {
        "name": "Staff",
        "description": "Kitchen and delivery floor: view orders, update their status.",
        "is_system": True,
        "is_superuser": False,
        "modules": [
            Module.DASHBOARD,
            Module.ORDERS,
            Module.LIVE_ORDERS,
            Module.INVENTORY,
            Module.PACKAGING,
            Module.CUSTOMERS,
        ],
        "actions": [PermissionAction.VIEW, PermissionAction.UPDATE],
    },
]

# Maps the legacy users.role value onto a seeded role name.
LEGACY_ROLE_TO_ROLE_NAME = {
    "ADMIN": "Administrator",
    "MANAGER": "Manager",
    "STAFF": "Staff",
}


def build_role_object(spec: dict) -> Role:
    """Create an unsaved Role (with its permission rows) from a bundle spec."""
    role = Role(
        name=spec["name"],
        description=spec.get("description"),
        is_system=spec.get("is_system", False),
        is_superuser=spec.get("is_superuser", False),
    )
    role.permissions = grants_for(spec["modules"], spec.get("actions"))
    return role
