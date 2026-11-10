from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from resumatch.auth import COOKIE
from resumatch.duplicates import same_subject
from resumatch.main import app
from resumatch.models import Capture


def setup(client):
    result = client.post("/api/auth/register", json={
        "email": "duplicates@example.com", "password": "synthetic duplicate passphrase"
    })
    assert result.status_code == 201
    return client.post("/api/sessions", json={"intention": "Find a founder"}).json()["id"]


def add(client, sid, url="https://www.linkedin.com/in/example-person/", **fields):
    return client.post(f"/api/sessions/{sid}/captures", json={
        "request_id": str(uuid4()), "details": {"source_url": url, **fields}
    })


@pytest.mark.parametrize("url", [
    "https://linkedin.com/in/example-person",
    "http://www.linkedin.com/in/EXAMPLE-PERSON/?trk=test#about",
    "https://uk.linkedin.com/in/example-person/details/experience/",
])
def test_profile_url_variants_cannot_create_another_person(client, url):
    sid = setup(client)
    first = add(client, sid, person="Example Person").json()
    second = add(client, sid, url, person="Example Person | LinkedIn", action="sent")
    assert second.status_code == 409
    assert second.json()["detail"]["existing_capture_id"] == first["id"]
    assert len(client.get(f"/api/sessions/{sid}").json()["captures"]) == 1


def test_manual_names_and_cross_channel_match_but_different_profile_wins(client):
    sid = setup(client)
    assert add(client, sid, "https://example.com/team", person="  Example  PERSON ",
               company="Synthetic Ltd").status_code == 201
    assert add(client, sid, "https://example.com/email", person="example person | LinkedIn",
               company="synthetic ltd", channel="email").status_code == 409
    # Two explicit distinct identities must not be merged just because names match.
    assert not same_subject(
        {"source_url": "https://linkedin.com/in/one", "person": "Alex Example"},
        {"source_url": "https://linkedin.com/in/two", "person": "Alex Example"},
    )
    # Different known people on a shared page/inbox are not duplicate contacts.
    assert add(client, sid, "https://example.com/team", person="Other Person").status_code == 201


def test_update_capture_keeps_original_and_reminder_appears_after_review(client, other, db):
    sid = setup(client)
    first = add(client, sid).json()
    future = (datetime.now(UTC).date() + timedelta(days=3)).isoformat()
    details = {**first["details"], "person": "Reviewed Person", "action": "sent",
               "followup_on": future, "notes": "Update instead of duplicate"}
    assert client.get("/api/overview").json()["upcoming_followups"] == []
    path = f"/api/sessions/{sid}/captures/{first['id']}"
    assert client.put(path, json={"details": details}).status_code == 200
    paused = client.post(f"/api/sessions/{sid}/transition", json={"action": "pause"})
    assert paused.status_code == 200
    assert client.put(path, json={"details": details}).status_code == 200
    other.post("/api/auth/register", json={
        "email": "other@example.com", "password": "synthetic duplicate passphrase"
    })
    assert other.put(path, json={"details": details}).status_code == 404
    client.post(f"/api/sessions/{sid}/transition", json={"action": "finish"})
    assert client.put(path, json={"details": details}).status_code == 200
    assert client.post(path + "/review", json={
        "decision": "approved", "confirmed_action": True, "details": details
    }).status_code == 200
    data = client.get("/api/overview").json()
    assert data["followups"] == []
    assert data["upcoming_followups"][0]["details"]["followup_on"] == future
    assert other.get("/api/overview").json()["upcoming_followups"] == []
    stored = db.get(Capture, UUID(first["id"]))
    assert stored.original["action"] == "researched" and stored.details["action"] == "sent"


def test_concurrent_duplicates_serialized_by_session(client):
    sid = setup(client)
    token = client.cookies.get(COOKIE)

    def attempt(_):
        with TestClient(app, headers={"origin": "http://localhost:3000"}) as c:
            c.cookies.set(COOKIE, token)
            return add(c, sid).status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(attempt, range(2))) == [201, 409]


def test_legacy_duplicates_preserved_flagged_and_only_one_can_be_approved(client, db):
    sid = setup(client)
    first = add(client, sid).json()
    # Simulate existing records from the pre-deduplication version, without data deletion.
    db.add(Capture(session_id=UUID(sid), request_id=uuid4(), source="browser",
                   original=first["details"], details=first["details"]))
    db.commit()
    data = client.get(f"/api/sessions/{sid}").json()
    assert len(data["captures"]) == 2
    second = next(c for c in data["captures"] if c["id"] != first["id"])
    assert second["duplicate_of"] == first["id"]
    client.post(f"/api/sessions/{sid}/transition", json={"action": "finish"})
    root = f"/api/sessions/{sid}/captures/"
    assert client.post(root + first["id"] + "/review", json={
        "decision": "approved", "details": first["details"]
    }).status_code == 200
    assert client.post(root + second["id"] + "/review", json={
        "decision": "approved", "details": second["details"]
    }).status_code == 409
    assert client.post(root + second["id"] + "/review", json={
        "decision": "discarded", "details": second["details"]
    }).status_code == 200
    assert len(db.scalars(select(Capture)).all()) == 2
    client.post(f"/api/sessions/{sid}/transition", json={"action": "complete"})
    fresh = client.post("/api/sessions", json={"intention": "A later follow-up"}).json()["id"]
    assert add(client, fresh).status_code == 201  # Deduplication is session-local.
