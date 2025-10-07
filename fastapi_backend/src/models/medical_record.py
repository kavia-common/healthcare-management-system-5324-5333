from datetime import datetime
from typing import Dict, Any
from pydantic import BaseModel, Field
from src.models.common import MongoModel, PyObjectId


class MedicalRecordBase(BaseModel):
    patient_id: PyObjectId = Field(..., description="Patient id")
    record_type: str = Field(..., description="Type, e.g., 'lab', 'note'")
    title: str = Field(..., description="Short title")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Arbitrary metadata")


class MedicalRecordCreate(MedicalRecordBase):
    pass


class MedicalRecordPublic(MongoModel, MedicalRecordBase):
    created_at: datetime = Field(default_factory=datetime.utcnow)
