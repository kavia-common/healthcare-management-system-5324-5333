import os
import pytest
from fastapi.testclient import TestClient

# Minimal env for app import
os.environ.setdefault("MONGODB_URL", "mongodb://localhost:5001")
os.environ.setdefault("MONGODB_DB", "healthcare")
os.environ.setdefault("JWT_SECRET", "test-secret")
os.environ.setdefault("JWT_ALGORITHM", "HS256")
os.environ.setdefault("ACCESS_TOKEN_EXPIRE_MINUTES", "5")
os.environ.setdefault("FRONTEND_ORIGINS", "http://localhost:3000")

from src.api.main import app  # noqa: E402
from src.api.db import get_db  # noqa: E402

# Simple in-memory "collections"
class FakeInsertResult:
    def __init__(self, inserted_id):
        self.inserted_id = inserted_id

class FakeCollection:
    def __init__(self):
        self._data = []
        self._id_counter = 1

    async def find_one(self, query):
        for item in self._data:
            ok = True
            for k, v in query.items():
                if item.get(k) != v:
                    ok = False
                    break
            if ok:
                return dict(item)
        return None

    async def insert_one(self, doc):
        if "_id" not in doc:
            doc["_id"] = str(self._id_counter)
            self._id_counter += 1
        self._data.append(dict(doc))
        return FakeInsertResult(doc["_id"])


class FakeDB:
    def __init__(self):
        self.collections = {
            "users": FakeCollection(),
            "patients": FakeCollection(),
            "doctors": FakeCollection(),
        }

    def __getitem__(self, name):
        return self.collections[name]


@pytest.fixture(autouse=True)
def fake_db_dependency(monkeypatch):
    db = FakeDB()

    async def _override_get_db():
        yield db  # emulate FastAPI dependency generator

    app.dependency_overrides[get_db] = _override_get_db
    yield
    app.dependency_overrides.clear()


client = TestClient(app)


def test_register_and_login_patient_flow():
    # Register
    reg_payload = {
        "email": "user1@example.com",
        "password": "secret123",
        "full_name": "User One",
        "role": "patient",
    }
    r = client.post("/auth/register", json=reg_payload)
    assert r.status_code == 201, r.text
    user = r.json()
    assert user["email"] == reg_payload["email"]
    assert user["role"] == "patient"
    assert "id" in user

    # Login
    r2 = client.post("/auth/login", data={"username": reg_payload["email"], "password": reg_payload["password"]})
    assert r2.status_code == 200, r2.text
    token = r2.json()["access_token"]
    assert token

    # Me
    r3 = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r3.status_code == 200, r3.text
    payload = r3.json()
    assert payload.get("sub") == user["id"]
    assert payload.get("role") == "patient"


def test_register_duplicate_conflict():
    reg_payload = {
        "email": "dup@example.com",
        "password": "secret123",
        "full_name": "Dup",
        "role": "doctor",
    }
    r1 = client.post("/auth/register", json=reg_payload)
    assert r1.status_code == 201
    r2 = client.post("/auth/register", json=reg_payload)
    assert r2.status_code == 409
