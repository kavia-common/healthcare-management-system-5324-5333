from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.db import register_db_events
from src.api.routes.auth import router as auth_router
# Optional imports for type checking and future router inclusion
# Note: Actual include_router calls may be added in a later step as per plan.
from src.api.routes.patients import router as patients_router  # noqa: F401
from src.api.routes.doctors import router as doctors_router  # noqa: F401
from src.api.routes.consultations import router as consultations_router  # noqa: F401
from src.api.routes.medical_records import router as medical_records_router  # noqa: F401

app = FastAPI(
    title="Healthcare Management System API",
    description="FastAPI backend for authentication, consultations, and medical records.",
    version="0.1.0",
    openapi_tags=[
        {"name": "Authentication", "description": "User registration and login"},
    ],
)

# Register DB lifecycle events
register_db_events(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Consider restricting in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/", summary="Health Check", tags=["Misc"])
def health_check():
    """Basic health check endpoint."""
    return {"message": "Healthy"}

# Mount Routers
app.include_router(auth_router)
