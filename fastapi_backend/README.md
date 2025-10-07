# healthcare-management-system-5324-5333 FastAPI Backend

This backend uses FastAPI with MongoDB (Motor) and environment-based configuration.

## Configuration
- Environment variables are loaded via python-dotenv from a `.env` file (if present).
- See `.env.example` for required and optional variables:
  - MONGODB_URL (required)
  - MONGODB_DB (required)
  - JWT_SECRET (required)
  - JWT_ALGORITHM (optional, default: HS256)
  - ACCESS_TOKEN_EXPIRE_MINUTES (optional, default: 60)

## Modules
- src/api/config.py
  - get_env(name, default=None): utility to read env vars.
  - get_settings(): loads and validates app settings.

- src/api/db.py
  - get_db(): FastAPI dependency yielding an AsyncIOMotorDatabase.
  - register_db_events(app): registers startup/shutdown to init/close client.

## Usage in main.py (minimal integration)
To enable database lifecycle management, import and register the events:
```python
from src.api.db import register_db_events
register_db_events(app)
```

For routes needing DB access:
```python
from fastapi import Depends
from motor.motor_asyncio import AsyncIOMotorDatabase
from src.api.db import get_db

@app.get("/example")
async def example(db: AsyncIOMotorDatabase = Depends(get_db)):
    await db["example"].insert_one({"ok": True})
    return {"status": "inserted"}
```

Note: The current main.py remains functional without modifications. You may optionally add the event registration as shown to initialize the DB on startup.
