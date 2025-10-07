from contextlib import asynccontextmanager
from typing import List

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.core.config import settings, get_cors_origins
from src.db.mongo import init_mongo, close_mongo, get_db, ensure_critical_indexes
from src.utils.errors import register_exception_handlers

from src.routers import auth as auth_router
from src.routers import users as users_router
from src.routers import patients as patients_router
from src.routers import doctors as doctors_router
from src.routers import consultations as consultations_router
from src.routers import medical_records as medical_records_router


# PUBLIC_INTERFACE
def get_openapi_tags() -> List[dict]:
    """Return OpenAPI tags metadata for grouping endpoints."""
    return [
        {"name": "health", "description": "Health check and diagnostics."},
        {"name": "auth", "description": "Authentication, registration, tokens."},
        {"name": "users", "description": "User self-service and admin operations."},
        {"name": "patients", "description": "Patient profile management."},
        {"name": "doctors", "description": "Doctor profile and availability."},
        {"name": "consultations", "description": "Consultation scheduling and updates."},
        {"name": "medical-records", "description": "Medical records metadata management."},
    ]


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize Mongo client
    await init_mongo()
    # Ensure indexes critical to app behavior
    await ensure_critical_indexes()
    yield
    # Close Mongo client
    await close_mongo()


# PUBLIC_INTERFACE
def create_app() -> FastAPI:
    """Create and configure the FastAPI application with middleware, routers, and exception handlers."""
    app = FastAPI(
        title=settings.API_TITLE,
        description="Backend API for Healthcare Management System",
        version="0.1.0",
        lifespan=lifespan,
        openapi_tags=get_openapi_tags(),
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=get_cors_origins(),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register routes
    app.include_router(auth_router.router, prefix="/auth", tags=["auth"])
    app.include_router(users_router.router, prefix="/users", tags=["users"])
    app.include_router(patients_router.router, prefix="/patients", tags=["patients"])
    app.include_router(doctors_router.router, prefix="/doctors", tags=["doctors"])
    app.include_router(consultations_router.router, prefix="/consultations", tags=["consultations"])
    app.include_router(medical_records_router.router, prefix="/medical-records", tags=["medical-records"])

    # Exceptions
    register_exception_handlers(app)

    @app.get("/", tags=["health"], summary="Health Check", description="Check API and database connectivity.")
    async def health_check():
        db = await get_db()
        res = await db.command("ping")
        return {"status": "ok", "db": res.get("ok", 0) == 1}

    return app


# Use a single global app instance for Uvicorn and for OpenAPI generation script
app = create_app()

# Note: Backend expected port: 3001. Example run:
# uvicorn src.api.main:app --host 0.0.0.0 --port 3001 --reload
