import os
from fastapi.testclient import TestClient

# Ensure minimal env present for app import even if DB is down
os.environ.setdefault("MONGODB_URL", "mongodb://localhost:5001")
os.environ.setdefault("MONGODB_DB", "healthcare")
os.environ.setdefault("JWT_SECRET", "test-secret")
os.environ.setdefault("JWT_ALGORITHM", "HS256")
os.environ.setdefault("ACCESS_TOKEN_EXPIRE_MINUTES", "5")
os.environ.setdefault("FRONTEND_ORIGINS", "http://localhost:3000")

from src.api.main import app  # noqa: E402

client = TestClient(app)


def test_health_endpoint():
    r = client.get("/")
    assert r.status_code == 200
    body = r.json()
    assert body.get("status") == "ok"
    assert body.get("db") in {"ok", "down"}
