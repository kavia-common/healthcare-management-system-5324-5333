from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from jose import JWTError, jwt
from passlib.context import CryptContext

from src.api.config import get_settings

# Password hashing context using bcrypt
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
        # In case of invalid hash format or other issues
        return False


# PUBLIC_INTERFACE
def create_access_token(subject: str, role: str, additional_claims: Optional[Dict[str, Any]] = None) -> str:
    """Create a signed JWT access token.

    Args:
        subject: The subject of the token, typically the user id.
        role: The user's role (e.g., 'patient', 'doctor', 'admin').
        additional_claims: Optional additional claims to include.

    Returns:
        A signed JWT string.
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

    token = jwt.encode(
        payload,
        settings["jwt_secret"],
        algorithm=settings["jwt_algorithm"],
    )
    return token


# PUBLIC_INTERFACE
def decode_token(token: str) -> Optional[Dict[str, Any]]:
    """Decode and validate a JWT access token.

    Returns:
        Decoded claims dict if valid, otherwise None.
    """
    settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            settings["jwt_secret"],
            algorithms=[settings["jwt_algorithm"]],
            options={"verify_aud": False},
        )
        return payload
    except JWTError:
        return None
