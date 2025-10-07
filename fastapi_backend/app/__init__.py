"""
FastAPI application package for the Healthcare Management System.

This package organizes:
- core: configuration and security utilities
- db: MongoDB Motor client and lifecycle helpers
- models: Pydantic request/response schemas
- routers: Feature routers (auth, patients)

Entrypoint:
- app.main: FastAPI app instance
"""
__all__ = ["core", "db", "models", "routers"]
