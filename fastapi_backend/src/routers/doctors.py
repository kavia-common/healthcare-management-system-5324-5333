from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from bson import ObjectId

from src.core.deps import require_roles
from src.models.user import UserInDB, Role
from src.models.doctor import DoctorCreate, DoctorUpdate, DoctorPublic
from src.db.mongo import get_db

router = APIRouter()


@router.get(
    "",
    response_model=List[DoctorPublic],
    summary="List/search doctors",
    description="List or search doctors by name or specialty. Public endpoint.",
)
async def list_doctors(
    q: Optional[str] = Query(None, description="Search by name or specialty"),
    limit: int = Query(50, ge=1, le=200),
    skip: int = Query(0, ge=0),
):
    db = await get_db()
    query = {}
    if q:
        query = {"$or": [{"full_name": {"$regex": q, "$options": "i"}}, {"specialty": {"$regex": q, "$options": "i"}}]}
    cursor = db["doctors"].find(query).skip(skip).limit(limit)
    return [DoctorPublic.model_validate(doc) async for doc in cursor]


@router.get(
    "/me",
    response_model=DoctorPublic,
    summary="Get my doctor profile",
    description="Get doctor profile linked to current user (doctor role).",
)
async def get_my_doctor_profile(user: UserInDB = Depends(require_roles(Role.doctor))):
    db = await get_db()
    doc = await db["doctors"].find_one({"user_id": user.id})
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Doctor profile not found")
    return DoctorPublic.model_validate(doc)


@router.get(
    "/{doctor_id}",
    response_model=DoctorPublic,
    summary="Get doctor by id",
    description="Get doctor profile by id. Public endpoint.",
)
async def get_doctor(doctor_id: str):
    db = await get_db()
    doc = await db["doctors"].find_one({"_id": ObjectId(doctor_id)})
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Doctor not found")
    return DoctorPublic.model_validate(doc)


@router.post(
    "",
    response_model=DoctorPublic,
    summary="Create doctor",
    description="Create a doctor profile linked to a user. Admin only.",
)
async def create_doctor(payload: DoctorCreate, _: UserInDB = Depends(require_roles(Role.admin))):
    db = await get_db()
    result = await db["doctors"].insert_one(payload.model_dump(by_alias=True))
    created = await db["doctors"].find_one({"_id": result.inserted_id})
    return DoctorPublic.model_validate(created)


@router.patch(
    "/{doctor_id}",
    response_model=DoctorPublic,
    summary="Update doctor",
    description="Update doctor details. Admin only.",
)
async def update_doctor(doctor_id: str, payload: DoctorUpdate, _: UserInDB = Depends(require_roles(Role.admin))):
    db = await get_db()
    update = {k: v for k, v in payload.model_dump(exclude_none=True).items()}
    await db["doctors"].update_one({"_id": ObjectId(doctor_id)}, {"$set": update})
    updated = await db["doctors"].find_one({"_id": ObjectId(doctor_id)})
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Doctor not found")
    return DoctorPublic.model_validate(updated)


@router.delete(
    "/{doctor_id}",
    summary="Delete doctor",
    description="Delete doctor profile. Admin only.",
)
async def delete_doctor(doctor_id: str, _: UserInDB = Depends(require_roles(Role.admin))):
    db = await get_db()
    res = await db["doctors"].delete_one({"_id": ObjectId(doctor_id)})
    if res.deleted_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Doctor not found")
    return {"deleted": True}
