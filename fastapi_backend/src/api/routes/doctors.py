from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from fastapi.security import OAuth2PasswordBearer
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, Field

from src.api.auth import decode_token
from src.api.db import get_db
from src.api.models import (
    DoctorOut,
    DoctorUpdate,
    convert_object_ids,
    to_object_id,
)

router = APIRouter(
    prefix="/doctors",
    tags=["Doctors"],
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", scheme_name="JWT")


# PUBLIC_INTERFACE
async def get_current_user(token: str = Depends(oauth2_scheme)) -> Dict[str, Any]:
    """Decode JWT and return claims or 401."""
    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")
    return payload


async def _doctors(db: AsyncIOMotorDatabase):
    return db["doctors"]


class PaginatedDoctors(BaseModel):
    items: List[DoctorOut] = Field(..., description="Doctors")
    total: int = Field(..., description="Total count")


@router.get(
    "/me",
    response_model=DoctorOut,
    summary="Get my doctor profile",
    description="Return the doctor profile for current user (role doctor).",
)
async def get_my_doctor_profile(
    user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> Any:
    if user.get("role") != "doctor":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only doctors can access this")
    coll = await _doctors(db)
    uid = user.get("sub")
    doc = await coll.find_one({"user_id": uid})
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Doctor profile not found")
    return convert_object_ids(doc)


@router.put(
    "/me",
    response_model=DoctorOut,
    summary="Update my doctor profile",
    description="Update doctor profile fields for the current user (role doctor).",
)
async def update_my_doctor_profile(
    payload: DoctorUpdate,
    user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> Any:
    if user.get("role") != "doctor":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only doctors can update their profile")
    coll = await _doctors(db)
    uid = user.get("sub")
    update_doc = {k: v for k, v in payload.model_dump(exclude_none=True).items()}
    res = await coll.find_one_and_update(
        {"user_id": uid},
        {"$set": update_doc},
        return_document=True,
    )
    if not res:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Doctor profile not found")
    return convert_object_ids(res)


@router.get(
    "/{id}",
    response_model=DoctorOut,
    summary="Get doctor by id",
    description="Get a doctor profile by document id.",
)
async def get_doctor_by_id(
    id: str = Path(..., description="Doctor document id"),
    user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> Any:
    # Any authenticated user can view doctors
    coll = await _doctors(db)
    try:
        oid = to_object_id(id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid id format")
    doc = await coll.find_one({"_id": oid})
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Doctor not found")
    return convert_object_ids(doc)


@router.get(
    "",
    response_model=PaginatedDoctors,
    summary="List doctors",
    description="Browse doctors with pagination.",
)
async def list_doctors(
    user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    q: str = Query("", description="Optional text search on full_name or specialization"),
) -> Any:
    coll = await _doctors(db)
    query: Dict[str, Any] = {}
    if q:
        # Simple case-insensitive regex search on fields
        query = {"$or": [{"full_name": {"$regex": q, "$options": "i"}}, {"specialization": {"$regex": q, "$options": "i"}}]}
    total = await coll.count_documents(query)
    cursor = coll.find(query).skip(skip).limit(limit).sort([("_id", 1)])
    items = [convert_object_ids(doc) async for doc in cursor]
    return {"items": items, "total": total}
