from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, EmailStr, Field

from src.api.auth import create_access_token, decode_token, hash_password, verify_password
from src.api.db import get_db

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
)


class TokenResponse(BaseModel):
    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field("bearer", description="Token type")


class RegisterRequest(BaseModel):
    email: EmailStr = Field(..., description="User email (unique)")
    password: str = Field(..., min_length=6, description="Password (min 6 chars)")
    full_name: Optional[str] = Field(None, description="Full name")
    # role: patient or doctor for this app scope
    role: str = Field(..., description="User role: 'patient' or 'doctor'")


class UserPublic(BaseModel):
    id: str = Field(..., description="User id")
    email: EmailStr = Field(..., description="Email")
    role: str = Field(..., description="Role")
    full_name: Optional[str] = Field(None, description="Full name")


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", scheme_name="JWT")


async def _get_users_collection(db: AsyncIOMotorDatabase):
    return db["users"]


async def _get_profile_collection(db: AsyncIOMotorDatabase, role: str):
    # Role-specific profile collections
    if role == "patient":
        return db["patients"]
    if role == "doctor":
        return db["doctors"]
    # Default generic collection if unexpected role
    return db["profiles"]


@router.post(
    "/register",
    response_model=UserPublic,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
    description="Create a new user with unique email. Stores password hash and creates role-specific profile stub.",
    responses={
        201: {"description": "User created"},
        400: {"description": "Invalid role or input"},
        409: {"description": "Email already exists"},
    },
)
async def register(
    payload: RegisterRequest,
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> UserPublic:
    users = await _get_users_collection(db)

    if payload.role not in {"patient", "doctor"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid role")

    # Ensure unique email
    existing = await users.find_one({"email": payload.email})
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    user_doc: Dict[str, Any] = {
        "email": payload.email,
        "password_hash": hash_password(payload.password),
        "role": payload.role,
        "full_name": payload.full_name,
    }
    # Create user
    result = await users.insert_one(user_doc)
    user_id = str(result.inserted_id)

    # Create role-specific profile stub
    profile_coll = await _get_profile_collection(db, payload.role)
    profile_stub: Dict[str, Any] = {
        "user_id": user_id,
        "email": payload.email,
        "full_name": payload.full_name,
        "role": payload.role,
    }
    # Additional defaults per role
    if payload.role == "patient":
        profile_stub.update({"medical_history": [], "allergies": [], "age": None})
    elif payload.role == "doctor":
        profile_stub.update({"specialization": None, "years_experience": None, "license_no": None})

    await profile_coll.insert_one(profile_stub)

    return UserPublic(id=user_id, email=payload.email, role=payload.role, full_name=payload.full_name)


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Login and get access token",
    description="Validate credentials and issue a JWT access token with subject=user_id and role claim.",
    responses={
        200: {"description": "Token issued"},
        401: {"description": "Invalid credentials"},
    },
)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> TokenResponse:
    users = await _get_users_collection(db)

    # OAuth2 form uses 'username' field for email
    email = form_data.username
    user = await users.find_one({"email": email})
    if not user or not verify_password(form_data.password, user.get("password_hash", "")):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    user_id = str(user["_id"])
    role = user.get("role", "patient")
    token = create_access_token(subject=user_id, role=role)
    return TokenResponse(access_token=token, token_type="bearer")


@router.get(
    "/me",
    response_model=Dict[str, Any],
    summary="Get current user info",
    description="Return the decoded JWT payload for the current user.",
    responses={
        200: {"description": "Current user payload"},
        401: {"description": "Invalid or expired token"},
    },
)
async def me(token: str = Depends(oauth2_scheme)) -> Dict[str, Any]:
    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")
    return payload
