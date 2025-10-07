"""API package for the Healthcare Management System backend.

This package contains:
- config: Environment settings utilities
- db: MongoDB (Motor) client lifecycle and dependency
- auth: JWT utilities and password hashing helpers
- routes: FastAPI route modules
"""
# Intentionally minimal exports to avoid heavy imports at package import time.

__all__ = ["config", "db", "auth"]
