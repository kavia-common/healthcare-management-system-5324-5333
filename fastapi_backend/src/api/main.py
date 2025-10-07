import os
from typing import List

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.db import register_db_events
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

# Configure CORS
# Allow explicit localhost origins and optional environment-provided origins for Flutter preview.
# FRONTEND_ORIGINS can be a comma-separated list, e.g.:
# "http://localhost:3000,https://localhost:3000,https://appetize.io,https://*.appetize.io"
default_origins: List[str] = [
    "http://localhost:3000",
    "https://localhost:3000",
]
# Common Flutter web preview domains (may vary). Include known preview host if provided via env.
# During development, we allow wildcard if FRONTEND_ORIGINS is not set to avoid CORS issues.
frontend_origins_env = os.getenv("FRONTEND_ORIGINS", "").strip()
if frontend_origins_env:
    # split by comma and strip spaces
    extra = [o.strip() for o in frontend_origins_env.split(",") if o.strip()]
    allow_origins = list({*default_origins, *extra})
else:
    # Fallback: permissive for local development; consider tightening in production
    allow_origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/", summary="Health Check", tags=["Misc"])
def health_check():
    """Basic health check endpoint."""
    return {"message": "Healthy"}

# Mount Routers: ensure each router has proper prefix and tags within its own module
# Routers already define their prefixes and tags internally.
app.include_router(auth_router)
app.include_router(patients_router)
app.include_router(doctors_router)
app.include_router(consultations_router)
app.include_router(medical_records_router)
