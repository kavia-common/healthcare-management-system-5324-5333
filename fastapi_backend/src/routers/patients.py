from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from bson import ObjectId

from src.core.deps import require_roles
from src.models.user import UserInDB, Role
from src.models.patient import PatientCreate, PatientUpdate, PatientPublic
from src.db.mongo import get_db

router = APIRouter()


@router.get(
    "",
    response_model=List[PatientPublic],
    summary="List patients",
    description="List patients with optional search. Admin and doctors only.",
)
async def list_patients(
    q: Optional[str] = Query(None, description="Search by name"),
    limit: int = Query(50, ge=1, le=200),
    skip: int = Query(0, ge=0),
    _: UserInDB = Depends(require_roles(Role.admin, Role.doctor)),
):
    db = await get_db()
    query = {}
    if q:
        query = {"full_name": {"$regex": q, "$options": "i"}}
    cursor = db["patients"].find(query).skip(skip).limit(limit)
    return [PatientPublic.model_validate(doc) async for doc in cursor]


@router.get(
    "/me",
    response_model=PatientPublic,
    summary="Get my patient profile",
    description="Get patient profile linked to current user (patient role).",
)
async def get_my_patient_profile(user: UserInDB = Depends(require_roles(Role.patient))):
    db = await get_db()
    doc = await db["patients"].find_one({"user_id": user.id})
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient profile not found")
    return PatientPublic.model_validate(doc)


@router.get(
    "/{patient_id}",
    response_model=PatientPublic,
    summary="Get patient by id",
    description="Admin or doctor can get any patient by id.",
)
async def get_patient(patient_id: str, _: UserInDB = Depends(require_roles(Role.admin, Role.doctor))):
    db = await get_db()
    doc = await db["patients"].find_one({"_id": ObjectId(patient_id)})
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")
    return PatientPublic.model_validate(doc)


@router.post(
    "",
    response_model=PatientPublic,
    summary="Create patient",
    description="Create a patient profile linked to a user. Admin only.",
)
async def create_patient(payload: PatientCreate, _: UserInDB = Depends(require_roles(Role.admin))):
    db = await get_db()
    result = await db["patients"].insert_one(payload.model_dump(by_alias=True))
    created = await db["patients"].find_one({"_id": result.inserted_id})
    return PatientPublic.model_validate(created)


@router.patch(
    "/{patient_id}",
    response_model=PatientPublic,
    summary="Update patient",
    description="Update patient details. Admin and doctors.",
)
async def update_patient(
    patient_id: str, payload: PatientUpdate, _: UserInDB = Depends(require_roles(Role.admin, Role.doctor))
):
    db = await get_db()
    update = {k: v for k, v in payload.model_dump(exclude_none=True).items()}
    await db["patients"].update_one({"_id": ObjectId(patient_id)}, {"$set": update})
    updated = await db["patients"].find_one({"_id": ObjectId(patient_id)})
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")
    return PatientPublic.model_validate(updated)


@router.delete(
    "/{patient_id}",
    summary="Delete patient",
    description="Delete patient profile. Admin only.",
)
async def delete_patient(patient_id: str, _: UserInDB = Depends(require_roles(Role.admin))):
    db = await get_db()
    res = await db["patients"].delete_one({"_id": ObjectId(patient_id)})
    if res.deleted_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")
    return {"deleted": True}
