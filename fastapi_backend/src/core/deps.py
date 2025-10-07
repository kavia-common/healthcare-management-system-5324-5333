from fastapi import Depends, HTTPException, status
from jose import JWTError
from bson import ObjectId

from src.core.security import oauth2_scheme, decode_token
from src.db.mongo import get_db
from src.models.user import UserInDB, Role


# PUBLIC_INTERFACE
async def get_current_user(token: str = Depends(oauth2_scheme)) -> UserInDB:
    """Get the current user from the Authorization bearer token."""
    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")
        sub = payload.get("sub")
        if not sub:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials")

    db = await get_db()
    user_doc = await db["users"].find_one({"_id": ObjectId(sub)})
    if not user_doc or user_doc.get("is_active") is False:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Inactive or not found user")

    return UserInDB.model_validate(user_doc)


# PUBLIC_INTERFACE
def require_roles(*roles: Role):
    """Dependency factory to enforce that current user has one of the required roles."""

    async def _checker(user: UserInDB = Depends(get_current_user)) -> UserInDB:
        if user.role not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
        return user

    return _checker
