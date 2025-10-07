from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import jwt  # PyJWT
from passlib.context import CryptContext

from app.core.config import get_settings

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# PUBLIC_INTERFACE
def hash_password(password: str) -> str:
    """Hash a plaintext password using bcrypt."""
    return _pwd_context.hash(password)


# PUBLIC_INTERFACE
def verify_password(plain_password: str, password_hash: str) -> bool:
    """Verify a plaintext password against its bcrypt hash."""
    try:
        return _pwd_context.verify(plain_password, password_hash)
    except Exception:
        return False


# PUBLIC_INTERFACE
def create_access_token(subject: str, role: str, additional_claims: Optional[Dict[str, Any]] = None) -> str:
    """Create a signed JWT access token.

    Args:
        subject: user id (string)
        role: user's role (e.g., "patient", "doctor")
        additional_claims: extra claims to include
    """
    settings = get_settings()
    expire_delta: timedelta = settings["access_token_expire_timedelta"]
    now = datetime.now(timezone.utc)
    payload: Dict[str, Any] = {
        "sub": subject,
        "role": role,
        "iat": int(now.timestamp()),
        "exp": int((now + expire_delta).timestamp()),
        "type": "access",
    }
    if additional_claims:
        payload.update(additional_claims)

    token = jwt.encode(payload, settings["jwt_secret"], algorithm=settings["jwt_algorithm"])
    return token


# PUBLIC_INTERFACE
def decode_token(token: str) -> Optional[Dict[str, Any]]:
    """Decode and validate a JWT access token. Returns claims or None."""
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings["jwt_secret"], algorithms=[settings["jwt_algorithm"]])
        return payload
    except Exception:
        return None
