from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from fastapi.security import OAuth2PasswordBearer
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, Field

from src.api.auth import decode_token
from src.api.db import get_db
from src.api.models import (
    PatientCreate,
    PatientOut,
    PatientUpdate,
    convert_object_ids,
    to_object_id,
)

router = APIRouter(
    prefix="/patients",
    tags=["Patients"],
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", scheme_name="JWT")


# PUBLIC_INTERFACE
async def get_current_user(token: str = Depends(oauth2_scheme)) -> Dict[str, Any]:
    """Decode JWT and return claims or 401."""
    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")
    return payload


async def _patients(db: AsyncIOMotorDatabase):
    return db["patients"]


async def _users(db: AsyncIOMotorDatabase):
    return db["users"]


class PaginatedPatients(BaseModel):
    items: List[PatientOut] = Field(..., description="Patients")
    total: int = Field(..., description="Total count")


@router.get(
    "/me",
    response_model=PatientOut,
    summary="Get my patient profile",
    description="Return the patient profile for the current user (role patient).",
)
async def get_my_profile(
    user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> Any:
    if user.get("role") != "patient":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only patients can access their own profile")
    coll = await _patients(db)
    uid = user.get("sub")
    doc = await coll.find_one({"user_id": uid})
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient profile not found")
    return convert_object_ids(doc)


@router.put(
    "/me",
    response_model=PatientOut,
    summary="Update my patient profile",
    description="Update patient profile fields for the current user (role patient).",
)
async def update_my_profile(
    payload: PatientUpdate,
    user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> Any:
    if user.get("role") != "patient":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only patients can update their profile")
    coll = await _patients(db)
    uid = user.get("sub")
    update_doc: Dict[str, Any] = {k: v for k, v in payload.model_dump(exclude_none=True).items()}
    res = await coll.find_one_and_update(
        {"user_id": uid},
        {"$set": update_doc},
        return_document=True,
    )
    if not res:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient profile not found")
    return convert_object_ids(res)


@router.get(
    "/{id}",
    response_model=PatientOut,
    summary="Get patient by id",
    description="Get a patient profile by document id. Accessible by doctor or admin.",
)
async def get_patient_by_id(
    id: str = Path(..., description="Patient document id"),
    user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> Any:
    role = user.get("role")
    if role not in {"doctor", "admin"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    coll = await _patients(db)
    try:
        oid = to_object_id(id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid id format")
    doc = await coll.find_one({"_id": oid})
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")
    return convert_object_ids(doc)


@router.post(
    "",
    response_model=PatientOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a patient profile",
    description="Admin can create a patient profile (or used internally during register flow).",
)
async def create_patient(
    payload: PatientCreate,
    user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> Any:
    role = user.get("role")
    if role != "admin":
        # Allow patient to create their own profile if missing (optional)
        if not (role == "patient" and payload.user_id == user.get("sub")):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    coll = await _patients(db)
    doc: Dict[str, Any] = payload.model_dump(exclude_none=True)
    # Ensure linkage is consistent if self-creating
    if role == "patient":
        doc["user_id"] = user["sub"]
    # Index considerations (assumes index on user_id)
    existing = await coll.find_one({"user_id": doc.get("user_id")})
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Patient profile already exists")
    result = await coll.insert_one(doc)
    created = await coll.find_one({"_id": result.inserted_id})
    return convert_object_ids(created)


@router.get(
    "",
    response_model=PaginatedPatients,
    summary="List patients (admin/doctor)",
    description="List patients with pagination. Doctors and admins only.",
)
async def list_patients(
    user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
    skip: int = Query(0, ge=0, description="Number of items to skip"),
    limit: int = Query(20, ge=1, le=100, description="Max items to return"),
) -> Any:
    role = user.get("role")
    if role not in {"doctor", "admin"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    coll = await _patients(db)
    total = await coll.count_documents({})
    cursor = coll.find({}).skip(skip).limit(limit).sort([("_id", 1)])
    items: List[Dict[str, Any]] = [convert_object_ids(doc) async for doc in cursor]
    return {"items": items, "total": total}
