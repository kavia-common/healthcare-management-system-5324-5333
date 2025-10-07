"""Pydantic models and enums for the Healthcare Management System backend.

This module centralizes request/response models for authentication, users,
patients, doctors, consultations, and medical records.

Key features:
- MongoDB ObjectId compatibility and JSON serialization as string
- Shared BaseModel for outputs with id field aliased from _id
- Enums for user roles and consultation status
- Role-aware schemas for user registration and public output
- Models designed to be compatible with Motor (async MongoDB driver)
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, EmailStr, Field, field_validator

try:
    # Prefer bson ObjectId for real MongoDB/Motor environments
    from bson import ObjectId as _BsonObjectId  # type: ignore
except Exception:  # pragma: no cover - fallback if bson is unavailable at runtime
    _BsonObjectId = str  # degrade gracefully for type purposes


# PUBLIC_INTERFACE
def to_object_id(value: Union[str, "_ObjectId", None]) -> Optional["_ObjectId"]:
    """Convert a string to a MongoDB ObjectId where possible.

    Returns None for None input. If value is already an ObjectId, returns as-is.
    Raises ValueError if the string is not a valid ObjectId hex.

    Note: This helper is useful for validating inbound payloads that may carry
    string ids which we want to convert to ObjectId before DB usage.
    """
    if value is None:
        return None
    if isinstance(value, _BsonObjectId):
        return value
    if isinstance(value, str):
        # Validate using ObjectId validity check
        try:
            return _BsonObjectId(value)  # type: ignore[call-arg]
        except Exception as exc:
            raise ValueError(f"Invalid ObjectId: {value}") from exc
    raise ValueError("Unsupported id type")


class _ObjectId(_BsonObjectId):  # type: ignore[misc]
    """Type alias for readability."""


# Enums

class UserRole(str, Enum):
    patient = "patient"
    doctor = "doctor"
    admin = "admin"


class ConsultationStatus(str, Enum):
    scheduled = "scheduled"
    in_progress = "in_progress"
    completed = "completed"
    cancelled = "cancelled"


# Common output base model with ObjectId serialization

class _MongoModel(BaseModel):
    """Internal base model with ObjectId serialization utilities."""

    def model_dump(self, *args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Override to ensure ObjectId values are converted to strings in dumps."""
        data = super().model_dump(*args, **kwargs)
        return convert_object_ids(data)


# PUBLIC_INTERFACE
class MongoModelOut(_MongoModel):
    """Base output model mapping MongoDB _id to id string.

    Use this as a base for response models representing persisted DB documents.
    """
    id: str = Field(..., description="Document id (stringified ObjectId)", alias="_id")

    # Pydantic v2: populate by field name and alias
    model_config = {
        "populate_by_name": True,
        "from_attributes": True,
        "json_encoders": {
            _BsonObjectId: lambda v: str(v),
        },
    }

    @field_validator("id", mode="before")
    @classmethod
    def _validate_id(cls, v: Any) -> str:
        # Accept ObjectId or string; return string
        if isinstance(v, _BsonObjectId):
            return str(v)
        if isinstance(v, str):
            return v
        raise ValueError("Invalid id type")


# Serialization helper

# PUBLIC_INTERFACE
def convert_object_ids(obj: Any) -> Any:
    """Recursively convert MongoDB ObjectId to string for JSON responses.

    Args:
        obj: Any Python object possibly containing ObjectId instances.

    Returns:
        Same structure with any ObjectId instances converted to their hex string.
    """
    if isinstance(obj, _BsonObjectId):
        return str(obj)
    if isinstance(obj, list):
        return [convert_object_ids(i) for i in obj]
    if isinstance(obj, tuple):
        return tuple(convert_object_ids(i) for i in obj)
    if isinstance(obj, dict):
        return {k: convert_object_ids(v) for k, v in obj.items()}
    return obj


# Authentication models

# PUBLIC_INTERFACE
class UserCreate(BaseModel):
    """Registration payload for creating a new user."""
    email: EmailStr = Field(..., description="User email (unique)")
    password: str = Field(..., min_length=6, description="Password (min 6 chars)")
    full_name: Optional[str] = Field(None, description="Full name")
    role: UserRole = Field(..., description="User role")

    model_config = {"json_schema_extra": {"example": {
        "email": "user@example.com",
        "password": "secret123",
        "full_name": "Jane Doe",
        "role": "patient",
    }}}


# PUBLIC_INTERFACE
class UserLogin(BaseModel):
    """Login payload (when not using OAuth2 form)."""
    email: EmailStr = Field(..., description="Email")
    password: str = Field(..., description="Password")


# PUBLIC_INTERFACE
class Token(BaseModel):
    """JWT token response."""
    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field("bearer", description="Token type")


# PUBLIC_INTERFACE
class UserOut(MongoModelOut):
    """Public user representation."""
    email: EmailStr = Field(..., description="Email")
    role: UserRole = Field(..., description="Role")
    full_name: Optional[str] = Field(None, description="Full name")


# Patient models

# PUBLIC_INTERFACE
class PatientCreate(BaseModel):
    """Create payload for a patient profile (usually auto-created on user registration)."""
    user_id: Optional[str] = Field(None, description="Associated user id (stringified ObjectId)")
    email: Optional[EmailStr] = Field(None, description="Email (redundant for convenience)")
    full_name: Optional[str] = Field(None, description="Full name")
    age: Optional[int] = Field(None, ge=0, description="Age")
    medical_history: List[str] = Field(default_factory=list, description="Medical history notes")
    allergies: List[str] = Field(default_factory=list, description="Allergies")

    @field_validator("user_id", mode="before")
    @classmethod
    def _validate_user_id(cls, v: Any) -> Any:
        if v is None:
            return v
        # Accept either valid ObjectId string or leave as-is; DB layer will convert
        if isinstance(v, str):
            _ = to_object_id(v)  # validate
            return v
        if isinstance(v, _BsonObjectId):
            return str(v)
        raise ValueError("user_id must be a string ObjectId or None")


# PUBLIC_INTERFACE
class PatientUpdate(BaseModel):
    """Update payload for a patient profile."""
    full_name: Optional[str] = Field(None, description="Full name")
    age: Optional[int] = Field(None, ge=0, description="Age")
    medical_history: Optional[List[str]] = Field(None, description="Medical history notes")
    allergies: Optional[List[str]] = Field(None, description="Allergies")


# PUBLIC_INTERFACE
class PatientOut(MongoModelOut):
    """Public patient profile representation."""
    user_id: Optional[str] = Field(None, description="Associated user id")
    email: Optional[EmailStr] = Field(None, description="Email")
    full_name: Optional[str] = Field(None, description="Full name")
    age: Optional[int] = Field(None, description="Age")
    medical_history: List[str] = Field(default_factory=list, description="Medical history notes")
    allergies: List[str] = Field(default_factory=list, description="Allergies")


# Doctor models

# PUBLIC_INTERFACE
class DoctorCreate(BaseModel):
    """Create payload for a doctor profile (usually auto-created on user registration)."""
    user_id: Optional[str] = Field(None, description="Associated user id (stringified ObjectId)")
    email: Optional[EmailStr] = Field(None, description="Email")
    full_name: Optional[str] = Field(None, description="Full name")
    specialization: Optional[str] = Field(None, description="Specialization")
    years_experience: Optional[int] = Field(None, ge=0, description="Years of experience")
    license_no: Optional[str] = Field(None, description="License number")

    @field_validator("user_id", mode="before")
    @classmethod
    def _validate_user_id(cls, v: Any) -> Any:
        if v is None:
            return v
        if isinstance(v, str):
            _ = to_object_id(v)
            return v
        if isinstance(v, _BsonObjectId):
            return str(v)
        raise ValueError("user_id must be a string ObjectId or None")


# PUBLIC_INTERFACE
class DoctorUpdate(BaseModel):
    """Update payload for a doctor profile."""
    full_name: Optional[str] = Field(None, description="Full name")
    specialization: Optional[str] = Field(None, description="Specialization")
    years_experience: Optional[int] = Field(None, ge=0, description="Years of experience")
    license_no: Optional[str] = Field(None, description="License number")


# PUBLIC_INTERFACE
class DoctorOut(MongoModelOut):
    """Public doctor profile representation."""
    user_id: Optional[str] = Field(None, description="Associated user id")
    email: Optional[EmailStr] = Field(None, description="Email")
    full_name: Optional[str] = Field(None, description="Full name")
    specialization: Optional[str] = Field(None, description="Specialization")
    years_experience: Optional[int] = Field(None, ge=0, description="Years of experience")
    license_no: Optional[str] = Field(None, description="License number")


# Consultation models

# PUBLIC_INTERFACE
class ConsultationCreate(BaseModel):
    """Create payload for a consultation."""
    patient_id: str = Field(..., description="Patient document id (stringified ObjectId)")
    doctor_id: str = Field(..., description="Doctor document id (stringified ObjectId)")
    scheduled_time: datetime = Field(..., description="Scheduled time")
    symptoms: Optional[str] = Field(None, description="Symptoms description")
    notes: Optional[str] = Field(None, description="Additional notes")
    status: ConsultationStatus = Field(ConsultationStatus.scheduled, description="Consultation status")

    @field_validator("patient_id", "doctor_id", mode="before")
    @classmethod
    def _validate_ref_ids(cls, v: Any) -> Any:
        if isinstance(v, str):
            _ = to_object_id(v)
            return v
        if isinstance(v, _BsonObjectId):
            return str(v)
        raise ValueError("Reference id must be a string ObjectId")


# PUBLIC_INTERFACE
class ConsultationUpdate(BaseModel):
    """Update payload for a consultation."""
    scheduled_time: Optional[datetime] = Field(None, description="Scheduled time")
    symptoms: Optional[str] = Field(None, description="Symptoms description")
    notes: Optional[str] = Field(None, description="Additional notes")
    status: Optional[ConsultationStatus] = Field(None, description="Consultation status")


# PUBLIC_INTERFACE
class ConsultationOut(MongoModelOut):
    """Public consultation representation."""
    patient_id: str = Field(..., description="Patient id")
    doctor_id: str = Field(..., description="Doctor id")
    scheduled_time: datetime = Field(..., description="Scheduled time")
    symptoms: Optional[str] = Field(None, description="Symptoms")
    notes: Optional[str] = Field(None, description="Notes")
    status: ConsultationStatus = Field(..., description="Status")


# Medical Record models

# PUBLIC_INTERFACE
class MedicalRecordCreate(BaseModel):
    """Create payload for a medical record."""
    patient_id: str = Field(..., description="Patient id (stringified ObjectId)")
    doctor_id: Optional[str] = Field(None, description="Doctor id (stringified ObjectId)")
    consultation_id: Optional[str] = Field(None, description="Optional related consultation id")
    diagnosis: Optional[str] = Field(None, description="Diagnosis")
    prescriptions: List[str] = Field(default_factory=list, description="Prescriptions")
    attachments: List[str] = Field(default_factory=list, description="Attachment URLs/ids")
    created_at: Optional[datetime] = Field(None, description="Created timestamp (server may set)")

    @field_validator("patient_id", "doctor_id", "consultation_id", mode="before")
    @classmethod
    def _validate_ref_ids(cls, v: Any) -> Any:
        if v is None:
            return v
        if isinstance(v, str):
            _ = to_object_id(v)
            return v
        if isinstance(v, _BsonObjectId):
            return str(v)
        raise ValueError("Reference id must be a string ObjectId or None")


# PUBLIC_INTERFACE
class MedicalRecordUpdate(BaseModel):
    """Update payload for a medical record."""
    diagnosis: Optional[str] = Field(None, description="Diagnosis")
    prescriptions: Optional[List[str]] = Field(None, description="Prescriptions")
    attachments: Optional[List[str]] = Field(None, description="Attachments")


# PUBLIC_INTERFACE
class MedicalRecordOut(MongoModelOut):
    """Public medical record representation."""
    patient_id: str = Field(..., description="Patient id")
    doctor_id: Optional[str] = Field(None, description="Doctor id")
    consultation_id: Optional[str] = Field(None, description="Consultation id")
    diagnosis: Optional[str] = Field(None, description="Diagnosis")
    prescriptions: List[str] = Field(default_factory=list, description="Prescriptions")
    attachments: List[str] = Field(default_factory=list, description="Attachments")
    created_at: Optional[datetime] = Field(None, description="Created timestamp")
