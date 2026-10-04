from contextlib import asynccontextmanager

import socketio
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

import app.models  # noqa: F401  # ensure every SQLAlchemy model is registered on Base
from app.api.v1.router import api_router
from app.core.config import settings
from app.core.database import Base, SessionLocal, engine
from app.core.exceptions import AppException
from app.core.logging import logger
from app.services.auth_service import AuthService
from app.services.seed_service import seed_dashboard_data
from app.socket_manager import capture_loop, sio


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan event handler for startup and shutdown routines."""
    logger.info("Initializing Panna Biryani CRM Backend...")
    capture_loop()

    # Ensure database tables exist (SQLite dev fallback / quickstart)
    Base.metadata.create_all(bind=engine)

    # Lightweight auto-migration: ensure shop_open column exists
    try:
        from sqlalchemy import inspect as _inspect
        from sqlalchemy import text as _text

        _insp = _inspect(engine)
        if "integration_configs" in _insp.get_table_names():
            _cols = [c["name"] for c in _insp.get_columns("integration_configs")]
            if "shop_open" not in _cols:
                with engine.begin() as _conn:
                    _conn.execute(_text("ALTER TABLE integration_configs ADD COLUMN shop_open BOOLEAN DEFAULT TRUE"))
                logger.info("Auto-migration: added shop_open column to integration_configs")

        if "business_hours_config" in _insp.get_table_names():
            _bh_cols = [c["name"] for c in _insp.get_columns("business_hours_config")]
            if "force_open_now" not in _bh_cols:
                with engine.begin() as _conn:
                    _conn.execute(_text("ALTER TABLE business_hours_config ADD COLUMN force_open_now BOOLEAN DEFAULT FALSE"))
                logger.info("Auto-migration: added force_open_now column to business_hours_config")

        if "menu_items" in _insp.get_table_names():
            _mi_cols = [c["name"] for c in _insp.get_columns("menu_items")]
            if "badge" not in _mi_cols:
                with engine.begin() as _conn:
                    _conn.execute(_text("ALTER TABLE menu_items ADD COLUMN badge VARCHAR(50)"))
                logger.info("Auto-migration: added badge column to menu_items")
            if "metadata_json" not in _mi_cols:
                with engine.begin() as _conn:
                    _conn.execute(_text("ALTER TABLE menu_items ADD COLUMN metadata_json TEXT"))
                logger.info("Auto-migration: added metadata_json column to menu_items")

        if "menu_item_portions" in _insp.get_table_names():
            _mp_cols = [c["name"] for c in _insp.get_columns("menu_item_portions")]
            if "original_price" not in _mp_cols:
                with engine.begin() as _conn:
                    _conn.execute(_text("ALTER TABLE menu_item_portions ADD COLUMN original_price FLOAT"))
                logger.info("Auto-migration: added original_price column to menu_item_portions")
    except Exception as e:
        logger.error(f"Auto-migration check failed: {e}", exc_info=True)

    # Initialize default admin & staff users, and seed initial operational data
    db = SessionLocal()
    try:
        auth_service = AuthService(db)
        auth_service.init_default_users()
        seed_dashboard_data(db)
        from app.services.website_seed import seed_storefront_config, seed_website_menu

        seed_storefront_config(db)
        seed_website_menu(db)
    except Exception as e:
        logger.error(f"Error during database initialization: {e}", exc_info=True)
    finally:
        db.close()

    logger.info("Startup complete. Panna CRM API is ready.")
    yield
    logger.info("Shutting down Panna Biryani CRM Backend...")


app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Internal operational CRM and business management system for Panna Biryani cloud kitchen.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan,
)

# CORS Setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS if isinstance(settings.BACKEND_CORS_ORIGINS, list) else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Centralized Exception Handlers
@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    return JSONResponse(
        status_code=exc.status_code,
        content=exc.detail if isinstance(exc.detail, dict) else {"success": False, "message": str(exc.detail)},
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = []
    for err in exc.errors():
        field = " -> ".join([str(loc) for loc in err.get("loc", [])])
        msg = err.get("msg", "Invalid value")
        errors.append(f"{field}: {msg}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "success": False,
            "message": "Validation error",
            "errors": errors,
        },
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled server error on {request.method} {request.url}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "message": "An unexpected internal server error occurred. Please contact the administrator.",
        },
    )


# Register API v1 Router
app.include_router(api_router, prefix=settings.API_V1_STR)

# Static media (uploaded images for the public website)
import os as _os

from fastapi.staticfiles import StaticFiles

_os.makedirs(_os.path.join(_os.getcwd(), "media", "uploads"), exist_ok=True)
app.mount("/media", StaticFiles(directory=_os.path.join(_os.getcwd(), "media")), name="media")


@app.get("/", tags=["Root"])
def root():
    return {
        "message": "Welcome to Panna Biryani CRM API",
        "documentation": "/docs",
        "health": f"{settings.API_V1_STR}/health",
        "version": "1.0.0",
    }


# ASGI wrapper: Socket.IO realtime (live orders screen) + existing REST app.
# Run with: uvicorn app.main:application
application = socketio.ASGIApp(sio, other_asgi_app=app)
