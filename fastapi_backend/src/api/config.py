import os
from datetime import timedelta
from typing import Optional

from dotenv import load_dotenv

# Load environment variables from a .env file if present
# This should be called once at module import time.
load_dotenv()


# PUBLIC_INTERFACE
def get_env(name: str, default: Optional[str] = None) -> str:
    """Get an environment variable or a default value.

    This utility is a thin wrapper around os.getenv that raises an error
    when a required variable is missing.

    Args:
        name: The name of the environment variable.
        default: The default value to use if not set. If None and the variable
                 is not set, a ValueError will be raised.

    Returns:
        The environment variable value as a string.

    Raises:
        ValueError: If the variable is not set and no default is provided.
    """
    value = os.getenv(name, default)
    if value is None:
        raise ValueError(f"Missing required environment variable: {name}")
    return value


# PUBLIC_INTERFACE
def get_settings() -> dict:
    """Return application settings loaded from environment.

    Loads required and optional configuration values for the application.
    Defaults are applied for optional values when not provided.

    Environment variables:
    - MONGODB_URL: Required. Full MongoDB connection string.
    - MONGODB_DB: Required. Database name to use.
    - JWT_SECRET: Required. Secret key for signing JWT tokens.
    - JWT_ALGORITHM: Optional. Defaults to 'HS256'.
    - ACCESS_TOKEN_EXPIRE_MINUTES: Optional. Defaults to 60 (int).

    Returns:
        dict with configuration keys:
            mongodb_url (str)
            mongodb_db (str)
            jwt_secret (str)
            jwt_algorithm (str)
            access_token_expire_minutes (int)
            access_token_expire_timedelta (timedelta)
    """
    mongodb_url = get_env("MONGODB_URL")
    mongodb_db = get_env("MONGODB_DB")
    jwt_secret = get_env("JWT_SECRET")
    jwt_algorithm = get_env("JWT_ALGORITHM", "HS256")
    expire_minutes_raw = get_env("ACCESS_TOKEN_EXPIRE_MINUTES", "60")

    try:
        expire_minutes = int(expire_minutes_raw)
    except ValueError as exc:
        raise ValueError("ACCESS_TOKEN_EXPIRE_MINUTES must be an integer") from exc

    return {
        "mongodb_url": mongodb_url,
        "mongodb_db": mongodb_db,
        "jwt_secret": jwt_secret,
        "jwt_algorithm": jwt_algorithm,
        "access_token_expire_minutes": expire_minutes,
        "access_token_expire_timedelta": timedelta(minutes=expire_minutes),
    }
