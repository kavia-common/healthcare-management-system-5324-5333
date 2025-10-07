from typing import List

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.config import get_settings
from src.api.db import register_db_events, ping_db
from src.api.routes.auth import router as auth_router
from src.api.routes.patients import router as patients_router
from src.api.routes.doctors import router as doctors_router
from src.api.routes.consultations import router as consultations_router
from src.api.routes.medical_records import router as medical_records_router

# Initialize FastAPI application with metadata and tags
app = FastAPI(
    title="Healthcare Management System API",
    description="FastAPI backend for authentication, consultations, and medical records.",
    version="0.1.0",
    openapi_tags=[
        {"name": "Authentication", "description": "User registration and login"},
        {"name": "Patients", "description": "Patient profile and management endpoints"},
        {"name": "Doctors", "description": "Doctor profile and management endpoints"},
        {"name": "Consultations", "description": "Consultation scheduling and management"},
        {"name": "Medical Records", "description": "Medical record creation and retrieval"},
        {"name": "Misc", "description": "Miscellaneous endpoints"},
    ],
)

# Register DB lifecycle events
register_db_events(app)

# Configure CORS using env settings
settings = get_settings()
frontend_origins = settings.get("frontend_origins") or ["http://localhost:3000"]
allow_origins: List[str] = frontend_origins if len(frontend_origins) > 0 else ["http://localhost:3000"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/", summary="Health Check", tags=["Misc"])
async def health_check():
    """Basic health check endpoint with DB connectivity status.

    Returns:
        JSON with status 'ok' and db 'ok' or 'down'.
    """
    db_ok = await ping_db()
    return {"status": "ok", "db": "ok" if db_ok else "down"}

# Mount Routers: ensure each router has proper prefix and tags within its own module
# Routers already define their prefixes and tags internally.
app.include_router(auth_router)
app.include_router(patients_router)
app.include_router(doctors_router)
app.include_router(consultations_router)
app.include_router(medical_records_router)
