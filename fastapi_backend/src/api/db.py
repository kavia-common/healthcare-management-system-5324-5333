from typing import AsyncGenerator, Optional

from fastapi import FastAPI
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from src.api.config import get_settings

_client: Optional[AsyncIOMotorClient] = None
_db: Optional[AsyncIOMotorDatabase] = None


def _init_client() -> None:
    """Initialize the global Motor client and database handle."""
    global _client, _db
    if _client is None or _db is None:
        settings = get_settings()
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
    """
    if _db is None:
        _init_client()
    # mypy hint: _db is set by _init_client
    assert _db is not None
    try:
        yield _db
    finally:
        # Keep a single shared client for the app lifetime; do not close per request.
        # Connection pooling is managed internally by Motor.
        pass


# PUBLIC_INTERFACE
def register_db_events(app: FastAPI) -> None:
    """Register FastAPI startup and shutdown events for DB lifecycle.

    Args:
        app: FastAPI application instance.
    """

    @app.on_event("startup")
    async def _on_startup() -> None:
        # Initialize client and DB at startup for early failure discovery.
        _init_client()

    @app.on_event("shutdown")
    async def _on_shutdown() -> None:
        # Gracefully close the client on app shutdown.
        _close_client()
