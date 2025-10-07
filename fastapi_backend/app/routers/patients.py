from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from fastapi.security import OAuth2PasswordBearer
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, Field

from app.core.security import decode_token
from app.db.mongo import get_db
from app.models.schemas import PatientCreate, PatientOut, PatientUpdate, convert_object_ids

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


class PaginatedPatients(BaseModel):
    items: List[PatientOut] = Field(..., description="Patients")
    total: int = Field(..., description="Total count")


@router.get(
    "",
    response_model=PaginatedPatients,
    summary="List patients",
    description="List patients with pagination.",
)
async def list_patients(
    user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
    skip: int = Query(0, ge=0, description="Number of items to skip"),
    limit: int = Query(20, ge=1, le=100, description="Max items to return"),
) -> Any:
    coll = await _patients(db)
    total = await coll.count_documents({})
    cursor = coll.find({}).skip(skip).limit(limit).sort([("_id", 1)])
    items: List[Dict[str, Any]] = [convert_object_ids(doc) async for doc in cursor]
    return {"items": items, "total": total}


@router.post(
    "",
    response_model=PatientOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a patient",
    description="Create a patient profile document.",
)
async def create_patient(
    payload: PatientCreate,
    user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> Any:
    coll = await _patients(db)
    doc: Dict[str, Any] = payload.model_dump(exclude_none=True)
    result = await coll.insert_one(doc)
    created = await coll.find_one({"_id": result.inserted_id})
    return convert_object_ids(created)


@router.get(
    "/{id}",
    response_model=PatientOut,
    summary="Get patient by id",
    description="Get a patient profile by document id.",
)
async def get_patient_by_id(
    id: str = Path(..., description="Patient document id"),
    user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> Any:
    # Accept string ObjectId; Motor can handle string lookup, but safer to direct match
    doc = await (await _patients(db)).find_one({"_id": id}) or await (await _patients(db)).find_one({"_id": id})
    if not doc:
        # try fallback with bson if available
        try:
            from bson import ObjectId  # type: ignore
            oid = ObjectId(id)
            doc = await (await _patients(db)).find_one({"_id": oid})
        except Exception:
            doc = None
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")
    return convert_object_ids(doc)


@router.patch(
    "/{id}",
    response_model=PatientOut,
    summary="Update patient by id",
    description="Update patient fields by document id.",
)
async def update_patient(
    id: str,
    payload: PatientUpdate,
    user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> Any:
    update_doc: Dict[str, Any] = {k: v for k, v in payload.model_dump(exclude_none=True).items()}
    coll = await _patients(db)
    # Try string and bson updates
    res = await coll.find_one_and_update({"_id": id}, {"$set": update_doc}, return_document=True)
    if not res:
        try:
            from bson import ObjectId  # type: ignore
            res = await coll.find_one_and_update({"_id": ObjectId(id)}, {"$set": update_doc}, return_document=True)
        except Exception:
            res = None
    if not res:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")
    return convert_object_ids(res)


@router.delete(
    "/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete patient by id",
    description="Delete a patient document by id.",
)
async def delete_patient(
    id: str,
    user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> None:
    coll = await _patients(db)
    # Try delete by string, then ObjectId
    result = await coll.delete_one({"_id": id})
    if result.deleted_count == 0:
        try:
            from bson import ObjectId  # type: ignore
            result = await coll.delete_one({"_id": ObjectId(id)})
        except Exception:
            result = None
    if not result or result.deleted_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")
