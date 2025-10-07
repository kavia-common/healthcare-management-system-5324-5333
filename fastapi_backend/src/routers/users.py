from typing import List, Optional

from fastapi import APIRouter, Depends, Query

from src.core.deps import get_current_user, require_roles
from src.models.user import UserInDB, UserPublic, UserUpdate, Role
from src.db.mongo import get_db

router = APIRouter()


@router.get(
    "/me",
    response_model=UserPublic,
    summary="Get current user",
    description="Return the authenticated user's public profile.",
)
async def get_me(user: UserInDB = Depends(get_current_user)):
    return UserPublic.model_validate(user.model_dump(by_alias=True))


@router.patch(
    "/me",
    response_model=UserPublic,
    summary="Update current user",
    description="Update own profile fields like full_name.",
)
async def update_me(payload: UserUpdate, user: UserInDB = Depends(get_current_user)):
    db = await get_db()
    update = {k: v for k, v in payload.model_dump(exclude_none=True).items()}
    if not update:
        return UserPublic.model_validate(user.model_dump(by_alias=True))
    await db["users"].update_one({"_id": user.id}, {"$set": update})
    refreshed = await db["users"].find_one({"_id": user.id})
    return UserPublic.model_validate(refreshed)


@router.get(
    "",
    response_model=List[UserPublic],
    summary="List users (admin)",
    description="Admin can list/search users by email or name.",
)
async def list_users(
    q: Optional[str] = Query(None, description="Search term for email or name"),
    limit: int = Query(50, ge=1, le=200),
    skip: int = Query(0, ge=0),
    _: UserInDB = Depends(require_roles(Role.admin)),
):
    db = await get_db()
    query = {}
    if q:
        query = {"$or": [{"email": {"$regex": q, "$options": "i"}}, {"full_name": {"$regex": q, "$options": "i"}}]}
    cursor = db["users"].find(query).skip(skip).limit(limit)
    results = [UserPublic.model_validate(doc) async for doc in cursor]
    return results
