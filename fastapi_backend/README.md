# FastAPI Backend - Healthcare Management System

This backend provides authentication, user/patient/doctor management, consultations scheduling, and medical records APIs. It uses FastAPI, MongoDB (motor), and JWT auth.

## Features
- JWT authentication (access/refresh) with password hashing (bcrypt via passlib)
- Modular routers: auth, users, patients, doctors, consultations, medical records
- Role-based authorization: admin, doctor, patient
- Pydantic v2 models with MongoDB ObjectId support
- Async Motor driver with startup index creation
- OpenAPI docs at /docs
- Health check with DB ping at GET /

## Prerequisites
- Python 3.11+
- MongoDB reachable via `MONGODB_URL`
- A `.env` file based on `.env.example`

## Configuration
Copy `.env.example` to `.env` and adjust values:
- API_TITLE, API_CORS_ORIGINS
- MONGODB_URL, MONGODB_DB
- JWT_SECRET, JWT_ALG, ACCESS_TOKEN_EXPIRE_MINUTES, REFRESH_TOKEN_EXPIRE_DAYS
- PASSWORD_SALT_ROUNDS, LOG_LEVEL

## Install and Run
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn src.api.main:app --host 0.0.0.0 --port 3001 --reload
```

## Health
- GET / -> `{ "status": "ok", "db": true }` when Mongo is reachable.

## Auth
- POST /auth/register -> Create patient user and patient profile
- POST /auth/login (OAuth2PasswordRequestForm) -> Token pair
- POST /auth/refresh -> New token pair from refresh token
- POST /auth/logout -> Stateless logout
- GET /auth/whoami -> Current user info

## Users
- GET /users/me
- PATCH /users/me
- GET /users (admin) -> list/search with `?q=term&skip=0&limit=50`

## Patients
- GET /patients (admin/doctor, optional `q`, paging)
- GET /patients/me (patient)
- GET /patients/{id} (admin/doctor)
- POST /patients (admin)
- PATCH /patients/{id} (admin/doctor)
- DELETE /patients/{id} (admin)

## Doctors
- GET /doctors (public search with `q`)
- GET /doctors/me (doctor)
- GET /doctors/{id} (public)
- POST /doctors (admin)
- PATCH /doctors/{id} (admin)
- DELETE /doctors/{id} (admin)

## Consultations
- POST /consultations (patient/admin)
- GET /consultations (role-aware: patients/doctors see own)
- PATCH /consultations/{id} (doctor/admin)

## Medical Records
- POST /medical-records (doctor/admin)
- GET /medical-records?patient_id=... (patient sees own only)
- GET /medical-records/{id}

## Notes
- Indexes are ensured at startup.
- Port: 3001
