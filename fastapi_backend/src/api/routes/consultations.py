from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from fastapi.security import OAuth2PasswordBearer
from motor.motor_asyncio import AsyncIOMotorDatabase

from src.api.auth import decode_token
from src.api.db import get_db
from src.api.models import (
    ConsultationCreate,
    ConsultationOut,
    ConsultationUpdate,
    convert_object_ids,
    to_object_id,
)

router = APIRouter(
    prefix="/consultations",
    tags=["Consultations"],
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", scheme_name="JWT")


# PUBLIC_INTERFACE
async def get_current_user(token: str = Depends(oauth2_scheme)) -> Dict[str, Any]:
    """Decode JWT and return claims or 401."""
    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")
    return payload


async def _consultations(db: AsyncIOMotorDatabase):
    return db["consultations"]


async def _patients(db: AsyncIOMotorDatabase):
    return db["patients"]


async def _doctors(db: AsyncIOMotorDatabase):
    return db["doctors"]


@router.post(
    "",
    response_model=ConsultationOut,
    status_code=status.HTTP_201_CREATED,
    summary="Schedule a consultation",
    description="Patients schedule a consultation with a doctor. Validates references.",
)
async def create_consultation(
    payload: ConsultationCreate,
    user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> Any:
    if user.get("role") != "patient":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only patients can schedule consultations")
    # Ensure patient_id matches current user's patient profile
    patients = await _patients(db)
    my_patient = await patients.find_one({"user_id": user.get("sub")})
    if not my_patient:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient profile not found")
    if str(my_patient["_id"]) != payload.patient_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot schedule for another patient")

    # Validate doctor exists
    doctors = await _doctors(db)
    try:
        did = to_object_id(payload.doctor_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid doctor_id")
    doctor = await doctors.find_one({"_id": did})
    if not doctor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Doctor not found")

    coll = await _consultations(db)
    doc = payload.model_dump()
    result = await coll.insert_one(doc)
    created = await coll.find_one({"_id": result.inserted_id})
    return convert_object_ids(created)


@router.get(
    "",
    response_model=List[ConsultationOut],
    summary="List consultations by role",
    description="Patients see their consultations; doctors see their consultations.",
)
async def list_consultations(
    user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
) -> Any:
    role = user.get("role")
    coll = await _consultations(db)
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
        query = {"doctor_id": str(my_doctor["_id"])}
    else:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    cursor = coll.find(query).skip(skip).limit(limit).sort([("_id", -1)])
    return [convert_object_ids(doc) async for doc in cursor]


@router.get(
    "/{id}",
    response_model=ConsultationOut,
    summary="Get consultation by id",
    description="Accessible to the patient or doctor involved.",
)
async def get_consultation(
    id: str = Path(..., description="Consultation id"),
    user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> Any:
    try:
        oid = to_object_id(id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid id format")
    coll = await _consultations(db)
    cons = await coll.find_one({"_id": oid})
    if not cons:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Consultation not found")

    # Access control
    role = user.get("role")
    if role == "patient":
        patients = await _patients(db)
        my_patient = await patients.find_one({"user_id": user.get("sub")})
        if not my_patient or str(my_patient["_id"]) != cons.get("patient_id"):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    elif role == "doctor":
        doctors = await _doctors(db)
        my_doctor = await doctors.find_one({"user_id": user.get("sub")})
        if not my_doctor or str(my_doctor["_id"]) != cons.get("doctor_id"):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    else:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    return convert_object_ids(cons)


@router.patch(
    "/{id}",
    response_model=ConsultationOut,
    summary="Update consultation (doctor)",
    description="Doctor can update status/notes/schedule for their consultation.",
)
async def update_consultation(
    id: str,
    payload: ConsultationUpdate,
    user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> Any:
    if user.get("role") != "doctor":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only doctors can update consultations")
    try:
        oid = to_object_id(id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid id format")
    coll = await _consultations(db)
    cons = await coll.find_one({"_id": oid})
    if not cons:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Consultation not found")

    doctors = await _doctors(db)
    my_doctor = await doctors.find_one({"user_id": user.get("sub")})
    if not my_doctor or str(my_doctor["_id"]) != cons.get("doctor_id"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    update_doc = {k: v for k, v in payload.model_dump(exclude_none=True).items()}
    res = await coll.find_one_and_update({"_id": oid}, {"$set": update_doc}, return_document=True)
    return convert_object_ids(res)
