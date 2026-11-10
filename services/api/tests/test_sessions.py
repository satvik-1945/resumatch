from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import select

from resumatch.auth import COOKIE, digest, hasher
from resumatch.db import get_engine
from resumatch.main import app
from resumatch.models import Capture, Login, Pairing, SessionEvent, User

PASSWORD = "a synthetic test password"


def register(client, email="first@example.com"):
    r = client.post("/api/auth/register", json={"email": email, "password": PASSWORD})
    assert r.status_code == 201, r.text
    return r.json()


def start(client):
    r = client.post("/api/sessions", json={"intention": "Research useful companies"})
    assert r.status_code == 201, r.text
    return r.json()["id"]


def move(client, sid, action):
    return client.post(f"/api/sessions/{sid}/transition", json={"action": action})


def capture(client, sid, **kwargs):
    r = client.post(f"/api/sessions/{sid}/captures", json={
        "request_id": str(uuid4()), "details": {"source_url": "https://example.com/story", **kwargs}
    })
    assert r.status_code == 201, r.text
    return r.json()


def review(client, sid, c, decision="approved", confirmed=False, **details):
    return client.post(f"/api/sessions/{sid}/captures/{c['id']}/review", json={
        "decision": decision, "details": {**c["details"], **details}, "confirmed_action": confirmed
    })


def test_migrations_health_auth_and_revocation(client, other, db):
    command.check(Config("alembic.ini"))
    assert client.get("/api/health/ready").status_code == 200
    assert client.get("/api/overview").status_code == 401
    assert client.get("/api/overview", headers={"x-user-id": str(uuid4())}).status_code == 401
    user = register(client)
    assert client.get("/api/auth/me").json()["id"] == user["id"]
    stored = db.get(User, UUID(user["id"]))
    assert hasher.verify(stored.password_hash, PASSWORD)
    token = client.cookies.get(COOKIE)
    assert db.get(Login, digest(token)) is not None
    assert client.get("/api/overview").headers["cache-control"] == "no-store"
    assert client.post("/api/auth/login", json={
        "email": "FIRST@example.com", "password": PASSWORD
    }).status_code == 200
    other.cookies.set(COOKIE, token)
    assert other.get("/api/overview").status_code == 401
    new_token = client.cookies.get(COOKIE)
    assert new_token != token
    assert client.post("/api/auth/logout").status_code == 204
    other.cookies.set(COOKIE, new_token)
    assert other.get("/api/overview").status_code == 401


@pytest.mark.parametrize("origin", ["https://evil.example", "null", "", "http://localhost:3001"])
def test_write_origins(client, origin):
    assert client.post("/api/auth/register", headers={"origin": origin}, json={
        "email": "first@example.com", "password": PASSWORD
    }).status_code == 403


def test_both_local_origins_and_expired_login(client, db):
    client.headers["origin"] = "http://127.0.0.1:3000"
    register(client)
    login = db.get(Login, digest(client.cookies.get(COOKIE)))
    login.expires_at = datetime.now(UTC) - timedelta(seconds=1)
    db.commit()
    assert client.get("/api/overview").status_code == 401


def test_durable_timer_transitions_and_single_open(client, other, db, monkeypatch):
    register(client)
    at = datetime.now(UTC)
    monkeypatch.setattr("resumatch.routes.now", lambda: at)
    sid = start(client)
    assert client.post("/api/sessions", json={"intention": "another"}).status_code == 409
    at += timedelta(seconds=65)
    paused = move(client, sid, "pause")
    assert paused.json()["elapsed_seconds"] == 65
    assert move(client, sid, "pause").status_code == 409
    at += timedelta(minutes=30)
    get_engine().dispose()  # Fresh connections, not in-memory timer state.
    other.cookies.set(COOKIE, client.cookies.get(COOKIE))
    assert other.get(f"/api/sessions/{sid}").json()["elapsed_seconds"] == 65
    assert move(client, sid, "resume").status_code == 200
    at += timedelta(seconds=35)
    assert move(client, sid, "finish").json()["elapsed_seconds"] == 100
    assert move(client, sid, "resume").status_code == 409
    assert move(client, sid, "complete").json()["state"] == "completed"
    assert client.get("/api/overview").json()["week"]["sessions"] == 0
    events = db.scalars(select(SessionEvent).order_by(SessionEvent.at)).all()
    assert [e.action for e in events] == ["start", "pause", "resume", "finish", "complete"]
    start(client)


def test_pending_draft_send_and_reviewed_progress(client, db):
    register(client)
    sid = start(client)
    draft = capture(client, sid, action="drafted", person="Example Person")
    sent = capture(client, sid, action="sent", person="Example Founder",
                   followup_on=datetime.now(UTC).date().isoformat())
    discarded = capture(client, sid)
    assert review(client, sid, draft).status_code == 409
    assert client.get("/api/overview").json()["week"]["counts"] == {}
    assert move(client, sid, "finish").status_code == 200
    assert move(client, sid, "complete").status_code == 409
    assert review(client, sid, draft).status_code == 200
    assert review(client, sid, sent).status_code == 422
    assert review(client, sid, sent, confirmed=True, person="").status_code == 422
    assert review(client, sid, sent, confirmed=True, notes="Reviewed note").status_code == 200
    assert review(client, sid, discarded, "discarded").status_code == 200
    assert review(client, sid, draft).status_code == 409
    assert move(client, sid, "complete").status_code == 200
    overview = client.get("/api/overview").json()
    assert overview["week"]["sessions"] == 1
    assert overview["week"]["counts"] == {"drafted": 1, "sent": 1}
    assert len(overview["followups"]) == 1
    assert client.post(f"/api/captures/{sent['id']}/followup-done").status_code == 200
    assert client.get("/api/overview").json()["followups"] == []
    assert client.get("/api/overview").json()["week"]["counts"] == {"drafted": 1, "sent": 1}
    stored = db.get(Capture, UUID(sent["id"]))
    assert stored.original["notes"] == "" and stored.details["notes"] == "Reviewed note"


def test_two_user_isolation_every_private_route(client, other):
    first = register(client)
    register(other, "other@example.com")
    sid = start(client)
    c = capture(client, sid)
    assert other.get(f"/api/sessions/{sid}").status_code == 404
    assert move(other, sid, "finish").status_code == 404
    assert other.post(f"/api/sessions/{sid}/captures", json={
        "request_id": str(uuid4()), "details": c["details"]
    }).status_code == 404
    assert review(other, sid, c).status_code == 404
    assert other.post(f"/api/captures/{c['id']}/followup-done").status_code == 404
    data = other.get(f"/api/overview?user_id={first['id']}").json()
    assert data["current"] is None and data["history"] == [] and data["followups"] == []
    injected = client.post("/api/sessions", json={"intention": "bad", "user_id": first["id"]})
    assert injected.status_code == 422


@pytest.mark.parametrize("url", ["javascript:alert(1)", "file:///etc/passwd", "https://a:b@example.com"])
def test_invalid_source_urls(client, url):
    register(client)
    sid = start(client)
    assert client.post(f"/api/sessions/{sid}/captures", json={
        "request_id": str(uuid4()), "details": {"source_url": url}
    }).status_code == 422


def test_retry_is_idempotent_and_paused_capture_blocked(client):
    register(client)
    sid = start(client)
    payload = {"request_id": str(uuid4()), "details": {"source_url": "https://example.com"}}
    first = client.post(f"/api/sessions/{sid}/captures", json=payload)
    second = client.post(f"/api/sessions/{sid}/captures", json=payload)
    assert first.json()["id"] == second.json()["id"]
    move(client, sid, "pause")
    assert client.post(f"/api/sessions/{sid}/captures", json=payload).status_code == 201
    payload["request_id"] = str(uuid4())
    assert client.post(f"/api/sessions/{sid}/captures", json=payload).status_code == 409


def test_extension_pairing_scopes_origin_expiry_revocation(client, other, db):
    register(client)
    register(other, "other@example.com")
    sid = start(client)
    eid = "a" * 32
    p = client.post("/api/pairings", json={"extension_id": eid}).json()
    assert other.delete(f"/api/pairings/{p['id']}").status_code == 404
    assert other.get("/api/pairings").json() == []
    stored = db.get(Pairing, UUID(p["id"]))
    assert stored.token_hash == digest(p["token"]) and stored.token_hash != p["token"]
    client.cookies.clear()
    headers = {"Authorization": "Bearer " + p["token"], "Origin": "chrome-extension://" + eid,
               "X-Extension-ID": eid}
    assert client.get("/api/extension/session", headers=headers).json()["session"]["id"] == sid
    assert client.get("/api/overview", headers=headers).status_code == 401
    assert client.get("/api/extension/session", headers={
        **headers, "X-Extension-ID": "b" * 32
    }).status_code == 403
    wrong_origin = client.get("/api/extension/session", headers={
        **headers, "Origin": "https://evil.example"
    })
    assert wrong_origin.status_code == 403
    payload = {"request_id": str(uuid4()), "details": {"source_url": "https://example.com"}}
    result = client.post(f"/api/extension/sessions/{sid}/captures", json=payload, headers=headers)
    assert result.status_code == 201 and result.json()["source"] == "browser"
    assert move(client, sid, "finish").status_code == 401
    stored.expires_at = datetime.now(UTC) - timedelta(seconds=1)
    db.commit()
    assert client.get("/api/extension/session", headers=headers).status_code == 401
    stored.expires_at = datetime.now(UTC) + timedelta(days=1)
    db.commit()
    client.post("/api/auth/login", json={"email": "first@example.com", "password": PASSWORD})
    assert client.delete(f"/api/pairings/{p['id']}").status_code == 204
    assert client.get("/api/extension/session", headers=headers).status_code == 401


def test_goal_bounds_and_unknown_actions(client):
    register(client)
    assert client.put("/api/goal", json={"weekly_target": 0}).status_code == 422
    assert client.put("/api/goal", json={"weekly_target": 4}).status_code == 200
    assert client.get("/api/overview").json()["week"]["target"] == 4
    sid = start(client)
    assert move(client, sid, "pretend_sent").status_code == 422


def test_concurrent_session_start_is_serialized(client):
    register(client)
    token = client.cookies.get(COOKIE)

    def attempt(_):
        with TestClient(app, headers={"origin": "http://localhost:3000"}) as worker:
            worker.cookies.set(COOKIE, token)
            return worker.post("/api/sessions", json={"intention": "Concurrent start"}).status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(attempt, range(2)))
    assert sorted(results) == [201, 409]
    assert len(client.get("/api/overview").json()["history"]) == 1


def test_privileged_extension_get_without_origin_still_requires_id_and_token(client):
    register(client)
    sid = start(client)
    eid = "c" * 32
    p = client.post("/api/pairings", json={"extension_id": eid}).json()
    client.cookies.clear()
    del client.headers["origin"]
    headers = {"Authorization": "Bearer " + p["token"], "X-Extension-ID": eid}
    result = client.get("/api/extension/session", headers=headers)
    assert result.status_code == 200 and result.json()["session"]["id"] == sid
    assert client.get("/api/extension/session", headers={
        "Authorization": "Bearer " + p["token"]
    }).status_code == 403
    assert client.get("/api/extension/session", headers={"X-Extension-ID": eid}).status_code == 401
