from typing import Optional

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo import ASCENDING, TEXT

from src.core.config import settings

_client: Optional[AsyncIOMotorClient] = None


# PUBLIC_INTERFACE
async def init_mongo() -> None:
    """Initialize the global MongoDB motor client."""
    global _client
    if _client is None:
        _client = AsyncIOMotorClient(settings.MONGODB_URL)


# PUBLIC_INTERFACE
async def close_mongo() -> None:
    """Close MongoDB client if initialized."""
    global _client
    if _client is not None:
        _client.close()
        _client = None


# PUBLIC_INTERFACE
async def get_db() -> AsyncIOMotorDatabase:
    """Return application's database instance."""
    if _client is None:
        await init_mongo()
    assert _client is not None
    return _client[settings.MONGODB_DB]


# PUBLIC_INTERFACE
async def ensure_critical_indexes() -> None:
    """Ensure critical indexes exist for collections, idempotent on startup."""
    db = await get_db()
    await db["users"].create_index([("email", ASCENDING)], name="u_email", unique=True)
    await db["patients"].create_index([("user_id", ASCENDING)], name="u_patient_user", unique=True)
    await db["doctors"].create_index([("user_id", ASCENDING)], name="u_doctor_user", unique=True)
    await db["consultations"].create_index([("patient_id", ASCENDING)], name="i_consult_patient")
    await db["consultations"].create_index([("doctor_id", ASCENDING)], name="i_consult_doctor")
    await db["consultations"].create_index([("scheduled_at", ASCENDING)], name="i_consult_time")
    await db["doctors"].create_index([("specialty", TEXT), ("full_name", TEXT)], name="t_doctor_search")
    await db["patients"].create_index([("full_name", TEXT)], name="t_patient_search")
    await db["medical_records"].create_index([("patient_id", ASCENDING)], name="i_medrec_patient")
