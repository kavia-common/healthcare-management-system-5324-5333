from __future__ import annotations

from typing import Any, List, Optional

from pydantic import BaseModel, EmailStr, Field, field_validator

try:
    from bson import ObjectId as _BsonObjectId  # type: ignore
except Exception:  # fallback for environments without bson
    _BsonObjectId = str  # type: ignore


# PUBLIC_INTERFACE
def convert_object_ids(obj: Any) -> Any:
    """Recursively convert MongoDB ObjectId to string for JSON responses."""
    if isinstance(obj, _BsonObjectId):
        return str(obj)
    if isinstance(obj, list):
        return [convert_object_ids(i) for i in obj]
    if isinstance(obj, tuple):
        return tuple(convert_object_ids(i) for i in obj)
    if isinstance(obj, dict):
        return {k: convert_object_ids(v) for k, v in obj.items()}
    return obj


# PUBLIC_INTERFACE
class MongoModelOut(BaseModel):
    """Base output model mapping MongoDB _id to id string."""
    id: str = Field(..., description="Document id (stringified ObjectId)", alias="_id")

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
        if isinstance(v, _BsonObjectId):
            return str(v)
        if isinstance(v, str):
            return v
        raise ValueError("Invalid id type")


# Auth models

# PUBLIC_INTERFACE
class UserCreate(BaseModel):
    """Payload for user registration."""
    email: EmailStr = Field(..., description="User email (unique)")
    password: str = Field(..., min_length=6, description="Password (min 6 chars)")
    full_name: Optional[str] = Field(None, description="Full name")


# PUBLIC_INTERFACE
class UserLogin(BaseModel):
    """Payload for user login."""
    email: EmailStr = Field(..., description="Email")
    password: str = Field(..., description="Password")


# PUBLIC_INTERFACE
class UserInDB(BaseModel):
    """Internal user shape stored in DB (excluding _id)."""
    email: EmailStr
    password_hash: str
    full_name: Optional[str] = None


# PUBLIC_INTERFACE
class Token(BaseModel):
    """JWT token response."""
    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field("bearer", description="Token type")


# Patients models

# PUBLIC_INTERFACE
class PatientCreate(BaseModel):
    """Create a patient profile."""
    user_id: Optional[str] = Field(None, description="Associated user id")
    email: Optional[EmailStr] = Field(None, description="Email")
    full_name: Optional[str] = Field(None, description="Full name")
    age: Optional[int] = Field(None, ge=0, description="Age")
    medical_history: List[str] = Field(default_factory=list, description="Medical history")
    allergies: List[str] = Field(default_factory=list, description="Allergies")


# PUBLIC_INTERFACE
class PatientUpdate(BaseModel):
    """Update a patient profile."""
    full_name: Optional[str] = Field(None)
    age: Optional[int] = Field(None, ge=0)
    medical_history: Optional[List[str]] = Field(None)
    allergies: Optional[List[str]] = Field(None)


# PUBLIC_INTERFACE
class PatientOut(MongoModelOut):
    """Public patient profile representation."""
    user_id: Optional[str] = Field(None, description="Associated user id")
    email: Optional[EmailStr] = Field(None, description="Email")
    full_name: Optional[str] = Field(None, description="Full name")
    age: Optional[int] = Field(None, description="Age")
    medical_history: List[str] = Field(default_factory=list, description="Medical history")
    allergies: List[str] = Field(default_factory=list, description="Allergies")
