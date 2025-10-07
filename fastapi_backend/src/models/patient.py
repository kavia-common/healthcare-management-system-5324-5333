from typing import Optional, List
from pydantic import BaseModel, Field
from src.models.common import MongoModel, PyObjectId


class PatientBase(BaseModel):
    user_id: PyObjectId = Field(..., description="Linked user id")
    full_name: Optional[str] = Field(None, description="Patient full name")
    age: Optional[int] = Field(None, ge=0, description="Age")
    gender: Optional[str] = Field(None, description="Gender")
    conditions: Optional[List[str]] = Field(default_factory=list, description="Known conditions")


class PatientCreate(PatientBase):
    pass


class PatientUpdate(BaseModel):
    full_name: Optional[str] = None
    age: Optional[int] = Field(None, ge=0)
    gender: Optional[str] = None
    conditions: Optional[List[str]] = None


class PatientPublic(MongoModel, PatientBase):
    pass
