import pytest
from fastapi.testclient import TestClient

from fakes import FakeClient

from guest_message_triage.app import app, get_client
from guest_message_triage.triage import Ticket, TriageResult

LEAK = TriageResult(
    tickets=[
        Ticket(
            category="maintenance",
            urgency="high",
            unit="4",
            next_action="Send someone to unit 4 before 3pm.",
        )
    ],
    needs_review=False,
)


@pytest.fixture
def fake():
    fake_client = FakeClient(LEAK)
    app.dependency_overrides[get_client] = lambda: fake_client
    yield fake_client
    app.dependency_overrides.clear()


client = TestClient(app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_message_returns_triage_result(fake):
    r = client.post("/messages", json={"text": "AC in unit 4 is leaking"})
    assert r.status_code == 200
    assert r.json() == LEAK.model_dump()
    assert fake.messages.calls[0]["messages"][0]["content"] == "AC in unit 4 is leaking"


def test_empty_message_is_rejected_without_calling_claude(fake):
    r = client.post("/messages", json={"text": ""})
    assert r.status_code == 422
    assert fake.messages.calls == []


def test_missing_text_is_rejected_without_calling_claude(fake):
    r = client.post("/messages", json={"sender": "guest"})
    assert r.status_code == 422
    assert fake.messages.calls == []
