from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field
from src.models.common import MongoModel, PyObjectId


class ConsultationStatus(str, Enum):
    scheduled = "scheduled"
    completed = "completed"
    cancelled = "cancelled"


class ConsultationBase(BaseModel):
    patient_id: PyObjectId = Field(..., description="Patient id")
    doctor_id: PyObjectId = Field(..., description="Doctor id")
    scheduled_at: datetime = Field(..., description="When the consultation is scheduled")
    notes: Optional[str] = Field(None, description="Notes")


class ConsultationCreate(ConsultationBase):
    pass


class ConsultationUpdate(BaseModel):
    scheduled_at: Optional[datetime] = None
    notes: Optional[str] = None
    status: Optional[ConsultationStatus] = None


class ConsultationPublic(MongoModel, ConsultationBase):
    status: ConsultationStatus = Field(ConsultationStatus.scheduled)
