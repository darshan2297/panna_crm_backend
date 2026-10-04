from contextlib import asynccontextmanager

import socketio
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

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
    except Exception as e:
        logger.error(f"Auto-migration check failed: {e}", exc_info=True)

    # Initialize default admin & staff users, and seed initial operational data
    db = SessionLocal()
    try:
        auth_service = AuthService(db)
        auth_service.init_default_users()
        seed_dashboard_data(db)
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
