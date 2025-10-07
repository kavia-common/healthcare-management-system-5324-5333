from datetime import datetime, timedelta, timezone
from typing import Any, Dict

from fastapi.security import OAuth2PasswordBearer
from jose import jwt
from passlib.context import CryptContext

from src.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Token URL is our login endpoint
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


# PUBLIC_INTERFACE
def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against its hashed version."""
    return pwd_context.verify(plain_password, hashed_password)


# PUBLIC_INTERFACE
def get_password_hash(password: str) -> str:
    """Hash a password using bcrypt via passlib."""
    return pwd_context.hash(password)


# PUBLIC_INTERFACE
def create_token(subject: str, token_type: str, expires_delta: timedelta) -> str:
    """Create a JWT token for the given subject and token type."""
    now = datetime.now(tz=timezone.utc)
    to_encode: Dict[str, Any] = {
        "sub": subject,
        "type": token_type,
        "iat": int(now.timestamp()),
        "exp": int((now + expires_delta).timestamp()),
    }
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALG)
    return encoded_jwt


# PUBLIC_INTERFACE
def decode_token(token: str) -> Dict[str, Any]:
    """Decode a JWT token and return its payload."""
    payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALG])
    return payload


# PUBLIC_INTERFACE
def create_access_token(subject: str) -> str:
    """Create an access token."""
    return create_token(
        subject=subject,
        token_type="access",
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )


# PUBLIC_INTERFACE
def create_refresh_token(subject: str) -> str:
    """Create a refresh token."""
    return create_token(
        subject=subject,
        token_type="refresh",
        expires_delta=timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    )
