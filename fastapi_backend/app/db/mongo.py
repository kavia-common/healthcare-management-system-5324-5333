from typing import AsyncGenerator, Optional
import logging

from fastapi import FastAPI, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from app.core.config import get_settings

_client: Optional[AsyncIOMotorClient] = None
_db: Optional[AsyncIOMotorDatabase] = None


def _init_client() -> None:
    """Initialize global Motor client and DB reference."""
    global _client, _db
    if _client is None or _db is None:
        settings = get_settings()
        _client = AsyncIOMotorClient(settings["mongodb_url"])
        _db = _client[settings["mongodb_db"]]


def _close_client() -> None:
    """Close Motor client on shutdown."""
    global _client, _db
    if _client is not None:
        _client.close()
    _client = None
    _db = None


# PUBLIC_INTERFACE
async def get_db() -> AsyncGenerator[AsyncIOMotorDatabase, None]:
    """Yield the Motor database handle for request-scoped usage.

    Raises 503 if database is not configured or unavailable.
    """
    if _db is None:
        try:
            _init_client()
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database is not configured or unavailable. Ensure MONGODB_URL and MONGODB_DB are set.",
            ) from exc

    if _db is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database is not configured or unavailable.",
        )

    try:
        yield _db
    finally:
        # Shared client, do not close per request.
        pass


# PUBLIC_INTERFACE
async def ping_db() -> bool:
    """Ping the MongoDB server to verify connectivity."""
    try:
        if _db is None:
            _init_client()
        if _client is None:
            return False
        await _client.admin.command("ping")
        return True
    except Exception:
        return False


# PUBLIC_INTERFACE
def register_db_events(app: FastAPI) -> None:
    """Register FastAPI startup/shutdown DB lifecycle."""

    @app.on_event("startup")
    async def _on_startup() -> None:
        try:
            _init_client()
        except Exception as exc:
            logging.getLogger("uvicorn.error").warning("Skipping DB initialization at startup: %s", str(exc))

    @app.on_event("shutdown")
    async def _on_shutdown() -> None:
        _close_client()
