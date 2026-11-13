from fastapi.testclient import TestClient

from guest_message_triage.app import app

client = TestClient(app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_empty_message_is_rejected():
    r = client.post("/messages", json={"text": ""})
    assert r.status_code == 422

def test_valid_message_returns_length():
    r = client.post("/messages", json={"text": "AC in unit 4 is leaking"})
    assert r.status_code == 200
    assert r.json()["length"] == 23

def test_missing_text_is_rejected():
    r = client.post("/messages", json={"sender": "guest"})
    assert r.status_code == 422