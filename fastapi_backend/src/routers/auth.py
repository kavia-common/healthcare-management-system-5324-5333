from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from bson import ObjectId

from src.core.security import get_password_hash, verify_password, create_access_token, create_refresh_token
from src.db.mongo import get_db
from src.models.auth import Token, TokenRefreshRequest
from src.models.user import UserCreate, UserInDB, UserPublic, Role
from src.core.deps import get_current_user

router = APIRouter()


@router.post(
    "/register",
    response_model=UserPublic,
    summary="Register a new patient",
    description="Creates a new user with 'patient' role and associated patient profile.",
)
async def register_user(payload: UserCreate):
    db = await get_db()
    existing = await db["users"].find_one({"email": payload.email})
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")

    doc = {
        "email": payload.email,
        "full_name": payload.full_name,
        "role": payload.role.value if isinstance(payload.role, Role) else str(payload.role),
        "hashed_password": get_password_hash(payload.password),
        "is_active": True,
    }
    # Force role patient for this register path
    doc["role"] = Role.patient.value

    result = await db["users"].insert_one(doc)
    user_id = result.inserted_id

    # Create patient profile
    patient_doc = {
        "user_id": user_id,
        "full_name": payload.full_name,
        "age": None,
        "gender": None,
        "conditions": [],
    }
    await db["patients"].insert_one(patient_doc)

    created = await db["users"].find_one({"_id": user_id})
    return UserPublic.model_validate(created)


@router.post(
    "/login",
    response_model=Token,
    summary="Login",
    description="Authenticate using OAuth2 password flow or JSON body and get tokens.",
)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    db = await get_db()
    user = await db["users"].find_one({"email": form_data.username})
    if not user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Incorrect username or password")
    if not verify_password(form_data.password, user.get("hashed_password", "")):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Incorrect username or password")
    if user.get("is_active") is False:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user")

    sub = str(user["_id"])
    access = create_access_token(sub)
    refresh = create_refresh_token(sub)
    return Token(access_token=access, refresh_token=refresh)


@router.post(
    "/refresh",
    response_model=Token,
    summary="Refresh access token",
    description="Provide a valid refresh token to receive a new access token pair.",
)
async def refresh(payload: TokenRefreshRequest):
    from jose import JWTError, jwt
    from src.core.config import settings

    try:
        data = jwt.decode(payload.refresh_token, settings.JWT_SECRET, algorithms=[settings.JWT_ALG])
        if data.get("type") != "refresh":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid token type")
        sub = data.get("sub")
        if not sub:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid token")

    # Validate user still exists/active
    db = await get_db()
    user = await db["users"].find_one({"_id": ObjectId(sub)})
    if not user or user.get("is_active") is False:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Inactive or not found user")

    access = create_access_token(sub)
    refresh = create_refresh_token(sub)
    return Token(access_token=access, refresh_token=refresh)


@router.post(
    "/logout",
    summary="Logout",
    description="Stateless logout for JWT (client should discard tokens).",
)
async def logout(_: UserInDB = Depends(get_current_user)):
    return {"message": "Logged out"}


@router.get(
    "/whoami",
    response_model=UserPublic,
    summary="Who am I",
    description="Return current user's public profile.",
)
async def whoami(current_user: UserInDB = Depends(get_current_user)):
    return UserPublic.model_validate(current_user.model_dump(by_alias=True))
