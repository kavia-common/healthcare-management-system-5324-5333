from typing import AsyncGenerator, Optional
import logging

from fastapi import FastAPI, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from src.api.config import get_settings

_client: Optional[AsyncIOMotorClient] = None
_db: Optional[AsyncIOMotorDatabase] = None


def _init_client() -> None:
    """Initialize the global Motor client and database handle.

    This is intentionally lightweight and non-blocking. Motor connects lazily,
    so creating the client will not block on connection attempts.
    """
    global _client, _db
    if _client is None or _db is None:
        settings = get_settings()  # may raise if required env vars are missing
        _client = AsyncIOMotorClient(settings["mongodb_url"])
        _db = _client[settings["mongodb_db"]]


def _close_client() -> None:
    """Close the global Motor client."""
    global _client, _db
    if _client is not None:
        _client.close()
    _client = None
    _db = None


# PUBLIC_INTERFACE
async def get_db() -> AsyncGenerator[AsyncIOMotorDatabase, None]:
    """Yield the Motor database handle for request-scoped usage.

    This function is intended to be used as a FastAPI dependency.

    Yields:
        AsyncIOMotorDatabase: The database instance.

    Raises:
        HTTPException 503 if the database is not configured or unavailable.
    """
    if _db is None:
        try:
            _init_client()
        except Exception as exc:
            # Do not expose secrets; provide actionable error and 503 status.
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database is not configured or unavailable. Ensure MONGODB_URL and MONGODB_DB are set."
            ) from exc

    if _db is None:
        # Defensive check in case initialization failed silently.
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database is not configured or unavailable."
        )

    try:
        yield _db
    finally:
        # Keep a single shared client for the app lifetime; do not close per request.
        # Connection pooling is managed internally by Motor.
        pass


# PUBLIC_INTERFACE
async def ping_db() -> bool:
    """Ping the MongoDB server to verify connectivity.

    Returns:
        True if ping succeeds, False otherwise.
    """
    try:
        if _db is None:
            _init_client()
        if _client is None:
            return False
        # Motor exposes 'admin' command on client
        await _client.admin.command("ping")
        return True
    except Exception:
        return False


# PUBLIC_INTERFACE
def register_db_events(app: FastAPI) -> None:
    """Register FastAPI startup and shutdown events for DB lifecycle.

    Args:
        app: FastAPI application instance.
    """

    @app.on_event("startup")
    async def _on_startup() -> None:
        # Initialize client and DB at startup but do not crash if env vars are missing
        # or if the DB is unreachable. This keeps the app booting for health checks
        # and documentation even when the DB is down.
        try:
            _init_client()
        except Exception as exc:
            logging.getLogger("uvicorn.error").warning(
                "Skipping DB initialization at startup: %s", str(exc)
            )

    @app.on_event("shutdown")
    async def _on_shutdown() -> None:
        # Gracefully close the client on app shutdown.
        _close_client()
