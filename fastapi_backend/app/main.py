from typing import List

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.db.mongo import register_db_events, ping_db
from app.routers.auth import router as auth_router
from app.routers.patients import router as patients_router

app = FastAPI(
    title="Healthcare Management System API",
    description="FastAPI backend for authentication and patient management.",
    version="0.1.0",
    openapi_tags=[
        {"name": "Authentication", "description": "User registration and login"},
        {"name": "Patients", "description": "Patient profile and management endpoints"},
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

@app.get("/health", summary="Health Check", tags=["Misc"])
async def health_check():
    """Health endpoint reporting API and DB status."""
    db_ok = await ping_db()
    return {"status": "ok", "db": "ok" if db_ok else "down"}

# Include routers
app.include_router(auth_router)
app.include_router(patients_router)
