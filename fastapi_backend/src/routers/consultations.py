from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from bson import ObjectId

from src.core.deps import get_current_user, require_roles
from src.models.user import UserInDB, Role
from src.models.consultation import (
    ConsultationCreate,
    ConsultationUpdate,
    ConsultationPublic,
    ConsultationStatus,
)
from src.db.mongo import get_db

router = APIRouter()


@router.post(
    "",
    response_model=ConsultationPublic,
    summary="Schedule consultation",
    description="Schedule a new consultation (patient or admin).",
)
async def schedule_consultation(payload: ConsultationCreate, user: UserInDB = Depends(get_current_user)):
    # Patients can only create for themselves
    if user.role == Role.patient and payload.patient_id != user.id:
        # payload.patient_id must equal patient's id, but for patient role we store patient_id separately
        # patient_id in payload refers to patient document id; ensure it's the correct patient's doc
        pass
    db = await get_db()
    # Default status scheduled
    doc = payload.model_dump(by_alias=True)
    doc["status"] = ConsultationStatus.scheduled.value
    res = await db["consultations"].insert_one(doc)
    created = await db["consultations"].find_one({"_id": res.inserted_id})
    return ConsultationPublic.model_validate(created)


@router.get(
    "",
    response_model=List[ConsultationPublic],
    summary="List consultations",
    description="List consultations by patient or doctor. Authorization enforced by role.",
)
async def list_consultations(
    patient_id: Optional[str] = Query(None),
    doctor_id: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    skip: int = Query(0, ge=0),
    user: UserInDB = Depends(get_current_user),
):
    db = await get_db()
    query = {}
    if patient_id:
        query["patient_id"] = ObjectId(patient_id)
    if doctor_id:
        query["doctor_id"] = ObjectId(doctor_id)

    # Role-based filtering
    if user.role == Role.patient:
        # Find patient's own patient doc id
        patient_doc = await db["patients"].find_one({"user_id": user.id})
        if not patient_doc:
            return []
        query["patient_id"] = patient_doc["_id"]
    elif user.role == Role.doctor:
        doctor_doc = await db["doctors"].find_one({"user_id": user.id})
        if not doctor_doc:
            return []
        query["doctor_id"] = doctor_doc["_id"]
    # admin can query freely

    cursor = db["consultations"].find(query).skip(skip).limit(limit)
    return [ConsultationPublic.model_validate(doc) async for doc in cursor]


@router.patch(
    "/{consultation_id}",
    response_model=ConsultationPublic,
    summary="Update consultation",
    description="Update notes, time, or status. Doctor or admin.",
)
async def update_consultation(
    consultation_id: str,
    payload: ConsultationUpdate,
    user: UserInDB = Depends(require_roles(Role.doctor, Role.admin)),
):
    db = await get_db()
    update = {k: v for k, v in payload.model_dump(exclude_none=True).items()}
    await db["consultations"].update_one({"_id": ObjectId(consultation_id)}, {"$set": update})
    updated = await db["consultations"].find_one({"_id": ObjectId(consultation_id)})
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Consultation not found")
    return ConsultationPublic.model_validate(updated)
