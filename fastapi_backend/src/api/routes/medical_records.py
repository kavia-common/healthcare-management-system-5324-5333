from datetime import datetime, timezone
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from fastapi.security import OAuth2PasswordBearer
from motor.motor_asyncio import AsyncIOMotorDatabase

from src.api.auth import decode_token
from src.api.db import get_db
from src.api.models import (
    MedicalRecordCreate,
    MedicalRecordOut,
    convert_object_ids,
    to_object_id,
)

router = APIRouter(
    prefix="/medical-records",
    tags=["Medical Records"],
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", scheme_name="JWT")


# PUBLIC_INTERFACE
async def get_current_user(token: str = Depends(oauth2_scheme)) -> Dict[str, Any]:
    """Decode JWT and return claims or 401."""
    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")
    return payload


async def _records(db: AsyncIOMotorDatabase):
    return db["medical_records"]


async def _patients(db: AsyncIOMotorDatabase):
    return db["patients"]


async def _doctors(db: AsyncIOMotorDatabase):
    return db["doctors"]


@router.post(
    "",
    response_model=MedicalRecordOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create medical record (doctor)",
    description="Doctor creates a medical record for a patient. Links to optional consultation.",
)
async def create_medical_record(
    payload: MedicalRecordCreate,
    user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> Any:
    if user.get("role") != "doctor":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only doctors can create medical records")

    # Validate patient exists
    patients = await _patients(db)
    try:
        pid = to_object_id(payload.patient_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid patient_id")
    patient = await patients.find_one({"_id": pid})
    if not patient:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")

    # Ensure doctor_id matches current doctor
    doctors = await _doctors(db)
    my_doctor = await doctors.find_one({"user_id": user.get("sub")})
    if not my_doctor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Doctor profile not found")

    doc = payload.model_dump()
    doc["doctor_id"] = str(my_doctor["_id"])
    doc["created_at"] = doc.get("created_at") or datetime.now(timezone.utc)

    coll = await _records(db)
    result = await coll.insert_one(doc)
    created = await coll.find_one({"_id": result.inserted_id})
    return convert_object_ids(created)


@router.get(
    "",
    response_model=List[MedicalRecordOut],
    summary="List medical records",
    description="Patients see their records; doctors see records they created or for their patients.",
)
async def list_medical_records(
    user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
) -> Any:
    role = user.get("role")
    coll = await _records(db)
    query: Dict[str, Any] = {}

    if role == "patient":
        patients = await _patients(db)
        my_patient = await patients.find_one({"user_id": user.get("sub")})
        if not my_patient:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient profile not found")
        query = {"patient_id": str(my_patient["_id"])}
    elif role == "doctor":
        doctors = await _doctors(db)
        my_doctor = await doctors.find_one({"user_id": user.get("sub")})
        if not my_doctor:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Doctor profile not found")
        # Doctor can see records they created or for their patients (same doctor_id)
        query = {"doctor_id": str(my_doctor["_id"])}
    else:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    cursor = coll.find(query).skip(skip).limit(limit).sort([("created_at", -1), ("_id", -1)])
    return [convert_object_ids(doc) async for doc in cursor]


@router.get(
    "/{id}",
    response_model=MedicalRecordOut,
    summary="Get medical record by id",
    description="Accessible by the patient the record belongs to or the doctor who created it.",
)
async def get_medical_record(
    id: str = Path(..., description="Medical record id"),
    user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> Any:
    try:
        oid = to_object_id(id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid id format")
    coll = await _records(db)
    rec = await coll.find_one({"_id": oid})
    if not rec:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Medical record not found")

    role = user.get("role")
    if role == "patient":
        patients = await _patients(db)
        my_patient = await patients.find_one({"user_id": user.get("sub")})
        if not my_patient or str(my_patient["_id"]) != rec.get("patient_id"):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    elif role == "doctor":
        doctors = await _doctors(db)
        my_doctor = await doctors.find_one({"user_id": user.get("sub")})
        if not my_doctor or str(my_doctor["_id"]) != rec.get("doctor_id"):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    else:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    return convert_object_ids(rec)
