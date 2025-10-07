from enum import Enum
from typing import Optional

from pydantic import BaseModel, EmailStr, Field
from src.models.common import MongoModel


class Role(str, Enum):
    admin = "admin"
    doctor = "doctor"
    patient = "patient"


class UserBase(BaseModel):
    email: EmailStr = Field(..., description="Unique email for login")
    full_name: Optional[str] = Field(None, description="Full name")
    role: Role = Field(Role.patient, description="Role of the user")
    is_active: bool = Field(True, description="Active status")


class UserCreate(UserBase):
    password: str = Field(..., min_length=6, description="Password for the user")


class UserUpdate(BaseModel):
    full_name: Optional[str] = Field(None)
    is_active: Optional[bool] = Field(None)


class UserPublic(MongoModel, UserBase):
    pass


class UserInDB(MongoModel, UserBase):
    hashed_password: str = Field(..., description="Hashed password")
