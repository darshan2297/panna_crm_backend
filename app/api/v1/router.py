from fastapi import APIRouter

from app.api.v1.analytics.router import router as analytics_router
from app.api.v1.audit.router import router as audit_router
from app.api.v1.auth.router import router as auth_router
from app.api.v1.business_hours.router import router as business_hours_router
from app.api.v1.contact_inquiries.router import router as contact_inquiries_router
from app.api.v1.customers.router import router as customers_router
from app.api.v1.dashboard.router import router as dashboard_router
from app.api.v1.delivery_areas.router import router as delivery_areas_router
from app.api.v1.faqs.router import router as faqs_router
from app.api.v1.health.router import router as health_router
from app.api.v1.integrations.router import router as integrations_router
from app.api.v1.inventory.router import router as inventory_router
from app.api.v1.menu.router import router as menu_router
from app.api.v1.notifications.router import router as notifications_router
from app.api.v1.orders.router import router as orders_router
from app.api.v1.packaging.router import router as packaging_router
from app.api.v1.public.router import router as public_router
from app.api.v1.restock.router import router as restock_router
from app.api.v1.reviews.router import router as reviews_router
from app.api.v1.roles.router import router as roles_router
from app.api.v1.users.router import router as users_router
from app.api.v1.website.router import router as website_router

api_router = APIRouter()

# Core, Phase 2–9 Modules
api_router.include_router(health_router)
api_router.include_router(auth_router)
api_router.include_router(dashboard_router)
api_router.include_router(users_router)
api_router.include_router(orders_router)
api_router.include_router(public_router)
api_router.include_router(menu_router)
api_router.include_router(inventory_router)
api_router.include_router(packaging_router)
api_router.include_router(notifications_router)
api_router.include_router(restock_router)
# Phase 10: Customer CRM
api_router.include_router(customers_router)
# Phase 11 & 12: Analytics, Reports & Costing
api_router.include_router(analytics_router)
# Phase 13: Zomato & Swiggy Integrations
api_router.include_router(integrations_router)
# Phase 14: Audit, Security & Hardening
api_router.include_router(audit_router)
# Role-Based Access Control: roles, permissions & user role assignment
api_router.include_router(roles_router)
# Phase 15: Business Hours, Holidays & Scheduled Shop Status
api_router.include_router(business_hours_router)
# Phase 16: Website Storefront Config & Promo Codes
api_router.include_router(website_router)
# Storefront Content: Reviews, FAQs & Delivery Areas
api_router.include_router(reviews_router)
api_router.include_router(faqs_router)
api_router.include_router(delivery_areas_router)
# Website Enquiries: Contact & Bulk Order forms
api_router.include_router(contact_inquiries_router)
