from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from bson import ObjectId

from src.core.deps import get_current_user, require_roles
from src.models.user import UserInDB, Role
from src.models.medical_record import MedicalRecordCreate, MedicalRecordPublic
from src.db.mongo import get_db

router = APIRouter()


@router.post(
    "",
    response_model=MedicalRecordPublic,
    summary="Create medical record",
    description="Create a medical record metadata entry. Doctor or admin.",
)
async def create_record(payload: MedicalRecordCreate, _: UserInDB = Depends(require_roles(Role.doctor, Role.admin))):
    db = await get_db()
    doc = payload.model_dump(by_alias=True)
    res = await db["medical_records"].insert_one(doc)
    created = await db["medical_records"].find_one({"_id": res.inserted_id})
    return MedicalRecordPublic.model_validate(created)


@router.get(
    "",
    response_model=List[MedicalRecordPublic],
    summary="List medical records",
    description="List records for a patient. Patients only see their own.",
)
async def list_records(
    patient_id: Optional[str] = Query(None, description="Patient id (required for doctor/admin)"),
    user: UserInDB = Depends(get_current_user),
    limit: int = Query(50, ge=1, le=200),
    skip: int = Query(0, ge=0),
):
    db = await get_db()
    query = {}
    if user.role == Role.patient:
        # map user to patient
        my_patient = await db["patients"].find_one({"user_id": user.id})
        if not my_patient:
            return []
        query["patient_id"] = my_patient["_id"]
    else:
        if not patient_id:
            raise HTTPException(status_code=400, detail="patient_id required")
        query["patient_id"] = ObjectId(patient_id)
    cursor = db["medical_records"].find(query).skip(skip).limit(limit)
    return [MedicalRecordPublic.model_validate(doc) async for doc in cursor]


@router.get(
    "/{record_id}",
    response_model=MedicalRecordPublic,
    summary="Get medical record",
    description="Get a single medical record by id. Patients can only access their own.",
)
async def get_record(record_id: str, user: UserInDB = Depends(get_current_user)):
    db = await get_db()
    doc = await db["medical_records"].find_one({"_id": ObjectId(record_id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Record not found")
    if user.role == Role.patient:
        my_patient = await db["patients"].find_one({"user_id": user.id})
        if not my_patient or doc["patient_id"] != my_patient["_id"]:
            raise HTTPException(status_code=403, detail="Forbidden")
    return MedicalRecordPublic.model_validate(doc)
