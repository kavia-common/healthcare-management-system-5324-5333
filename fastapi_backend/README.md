# Healthcare Management System - FastAPI Backend (App structure)

FastAPI backend with MongoDB (Motor) using environment-based configuration.

- API docs: http://localhost:3001/docs
- OpenAPI JSON: http://localhost:3001/openapi.json

## Quickstart

1) Python setup
- Python 3.10+
- Create and activate a virtual environment

2) Install dependencies
- pip install --upgrade pip
- pip install -r requirements.txt

3) Create .env
Create a .env file (use .env.example if provided) with:
- MONGODB_URL=mongodb://localhost:5001
- MONGODB_DB=healthcare
- JWT_SECRET=your-strong-secret
- JWT_ALGORITHM=HS256
- ACCESS_TOKEN_EXPIRE_MINUTES=60
- FRONTEND_ORIGINS=http://localhost:3000
- PORT=3001

4) Run the server
- uvicorn app.main:app --host 0.0.0.0 --port 3001

5) Health
- GET /health -> {"status":"ok","db":"ok" | "down"}

## Code structure
- app/main.py: FastAPI app, CORS, routers, app metadata, health
- app/core/config.py: Env settings utilities
- app/core/security.py: Password hashing (bcrypt) and JWT utilities (PyJWT)
- app/db/mongo.py: Motor client lifecycle, FastAPI dependency get_db, ping_db, register_db_events
- app/models/schemas.py: Pydantic models (User, Token, Patient)
- app/routers/auth.py: Register/Login/Me
- app/routers/patients.py: CRUD for patients (JWT protected)

## Notes
- Ensure MongoDB is accessible at the provided MONGODB_URL (default local port 5001).
- CORS allows http://localhost:3000 by default for Flutter/web preview.
