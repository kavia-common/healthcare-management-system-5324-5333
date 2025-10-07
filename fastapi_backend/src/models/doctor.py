from typing import Optional, List
from pydantic import BaseModel, Field
from src.models.common import MongoModel, PyObjectId


class AvailabilitySlot(BaseModel):
    day: str = Field(..., description="Day of week")
    start: str = Field(..., description="Start time e.g., 09:00")
    end: str = Field(..., description="End time e.g., 17:00")


class DoctorBase(BaseModel):
    user_id: PyObjectId = Field(..., description="Linked user id")
    full_name: Optional[str] = Field(None)
    specialty: Optional[str] = Field(None)
    availability: Optional[List[AvailabilitySlot]] = Field(default_factory=list)


class DoctorCreate(DoctorBase):
    pass


class DoctorUpdate(BaseModel):
    full_name: Optional[str] = None
    specialty: Optional[str] = None
    availability: Optional[List[AvailabilitySlot]] = None


class DoctorPublic(MongoModel, DoctorBase):
    pass
