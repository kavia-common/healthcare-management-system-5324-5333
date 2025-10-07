# Healthcare Management System - FastAPI Backend

FastAPI backend for authentication, patients, doctors, consultations, and medical records using MongoDB (Motor) and environment-based configuration.

- API docs: after running, open http://localhost:8000/docs
- OpenAPI JSON: http://localhost:8000/openapi.json

## Quickstart

1) Python setup
- Python 3.10+ recommended
- Create and activate a virtual environment
  - macOS/Linux:
    - python3 -m venv .venv
    - source .venv/bin/activate
  - Windows (PowerShell):
    - py -m venv .venv
    - .\.venv\Scripts\Activate.ps1

2) Install dependencies
- pip install --upgrade pip
- pip install -r requirements.txt

3) Create .env
Create a .env file in this directory with the following variables:
- MONGODB_URL=your-mongodb-connection-string
- MONGODB_DB=your-database-name
- JWT_SECRET=your-strong-secret
- JWT_ALGORITHM=HS256
- ACCESS_TOKEN_EXPIRE_MINUTES=60
- FRONTEND_ORIGINS=http://localhost:3000,https://localhost:3000

Notes:
- Do not commit real secrets.
- In CI or production, these values should be set as environment variables.

4) Run the server
- Development (auto-reload):
  - uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload
- Production example:
  - uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --workers 2

5) Explore the API
- Open http://localhost:8000/ to see health check
- Open http://localhost:8000/docs for Swagger UI

## Environment variables

The backend reads configuration from environment variables (via python-dotenv if .env exists):

Required:
- MONGODB_URL: Full MongoDB connection string
- MONGODB_DB: Database name
- JWT_SECRET: Secret used to sign JWTs

Optional:
- JWT_ALGORITHM: Default HS256
- ACCESS_TOKEN_EXPIRE_MINUTES: Default 60
- FRONTEND_ORIGINS: Comma-separated list of allowed origins for CORS (overrides permissive dev default)

## Running with Docker (optional example)

If you have a MongoDB accessible via MONGODB_URL, you can run the API container with:
- docker run --rm -it -p 8000:8000 --env-file .env -v ${PWD}:/app -w /app python:3.11-slim bash -lc "pip install -r fastapi_backend/requirements.txt && uvicorn fastapi_backend.src.api.main:app --host 0.0.0.0 --port 8000"

Adjust paths as necessary.

## Endpoints overview

Health
- GET / : Health check

Authentication
- POST /auth/register : Create a user (role patient or doctor)
- POST /auth/login : OAuth2 password flow; returns access token
- GET /auth/me : Decode current token and return claims

Patients
- GET /patients/me : Get current patient's profile
- PUT /patients/me : Update current patient's profile
- GET /patients/{id} : Get patient by id (doctor/admin)
- POST /patients : Create patient (admin or self-create if allowed)
- GET /patients : List patients (doctor/admin) with pagination

Doctors
- GET /doctors/me : Get current doctor profile
- PUT /doctors/me : Update doctor profile
- GET /doctors/{id} : Get doctor by id
- GET /doctors : List doctors with pagination and optional q search

Consultations
- POST /consultations : Patient schedules a consultation
- GET /consultations : List consultations for current user (role-aware)
- GET /consultations/{id} : Get consultation by id (access-controlled)
- PATCH /consultations/{id} : Doctor updates their consultation

Medical Records
- POST /medical-records : Doctor creates a medical record
- GET /medical-records : List medical records for current user
- GET /medical-records/{id} : Get record by id (access-controlled)

For parameter details and schema examples, see the interactive docs at /docs.

## CORS

- By default in development, the application allows all origins ("*") unless FRONTEND_ORIGINS is specified.
- To restrict in production, set FRONTEND_ORIGINS with a comma-separated whitelist (e.g., FRONTEND_ORIGINS=https://yourapp.com,https://admin.yourapp.com).

## Code structure

- src/api/main.py: FastAPI app, CORS, routers, app metadata
- src/api/config.py: Environment settings utilities
- src/api/db.py: Motor client lifecycle, FastAPI dependency get_db, register_db_events
- src/api/auth.py: Password hashing (passlib[bcrypt]) and JWT utilities (python-jose[cryptography])
- src/api/models.py: Pydantic models and enums
- src/api/routes/*: Feature routers (auth, patients, doctors, consultations, medical_records)
- interfaces/openapi.json: Generated OpenAPI spec

## Development tips

- The DB lifecycle is registered via register_db_events(app) in main.py.
- Use get_db dependency in routes to access the AsyncIOMotorDatabase.
- Run python -m src.api.generate_openapi to refresh interfaces/openapi.json if needed (ensure app can start).

## .env.example

You can create a .env.example file mirroring the variables above to share expected configuration:
- MONGODB_URL=
- MONGODB_DB=
- JWT_SECRET=
- JWT_ALGORITHM=HS256
- ACCESS_TOKEN_EXPIRE_MINUTES=60
- FRONTEND_ORIGINS=http://localhost:3000,https://localhost:3000
