import os
from datetime import timedelta
from typing import List, Optional

from dotenv import load_dotenv

# Load environment variables from a .env file if present
load_dotenv()


# PUBLIC_INTERFACE
def get_env(name: str, default: Optional[str] = None) -> str:
    """Get an environment variable or default.

    Raises ValueError if missing and default is None.
    """
    value = os.getenv(name, default)
    if value is None:
        raise ValueError(f"Missing required environment variable: {name}")
    return value


def _parse_origins(csv: str) -> List[str]:
    return [o.strip() for o in (csv or "").split(",") if o.strip()]


# PUBLIC_INTERFACE
def get_settings() -> dict:
    """Return application settings from environment.

    Required:
    - MONGODB_URL
    - MONGODB_DB
    - JWT_SECRET

    Optional:
    - ACCESS_TOKEN_EXPIRE_MINUTES (default 60)
    - JWT_ALGORITHM (default HS256)
    - FRONTEND_ORIGINS (default http://localhost:3000)
    - PORT (default 3001)
    """
    mongodb_url = get_env("MONGODB_URL")
    mongodb_db = get_env("MONGODB_DB")
    jwt_secret = get_env("JWT_SECRET")
    jwt_algorithm = get_env("JWT_ALGORITHM", "HS256")
    expire_minutes_raw = get_env("ACCESS_TOKEN_EXPIRE_MINUTES", "60")
    frontend_origins_csv = get_env("FRONTEND_ORIGINS", "http://localhost:3000")
    port_raw = get_env("PORT", "3001")

    try:
        expire_minutes = int(expire_minutes_raw)
    except ValueError as exc:
        raise ValueError("ACCESS_TOKEN_EXPIRE_MINUTES must be an integer") from exc

    try:
        port = int(port_raw)
    except ValueError as exc:
        raise ValueError("PORT must be an integer") from exc

    return {
        "mongodb_url": mongodb_url,
        "mongodb_db": mongodb_db,
        "jwt_secret": jwt_secret,
        "jwt_algorithm": jwt_algorithm,
        "access_token_expire_minutes": expire_minutes,
        "access_token_expire_timedelta": timedelta(minutes=expire_minutes),
        "frontend_origins": _parse_origins(frontend_origins_csv),
        "port": port,
    }
