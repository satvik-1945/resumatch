from datetime import UTC, datetime
from urllib.parse import parse_qs, urlsplit

import pytest
from cryptography.fernet import Fernet
from tests.test_workflows import register, start, workflow

from resumatch import inbox
from resumatch.config import get_settings

LINKEDIN = "LinkedIn <jobs-noreply@linkedin.com>"
DATE = "Mon, 17 Nov 2026 21:48:00 +0530"


@pytest.fixture
def google_env(monkeypatch):
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "client-id.apps.googleusercontent.com")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "synthetic-secret")
    monkeypatch.setenv("EMAIL_TOKEN_KEY", Fernet.generate_key().decode())
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


class FakeGoogle:
    """Stands in for Google's token, profile and Gmail endpoints. No network."""

    def __init__(self, address="satvik@example.com"):
        self.address, self.messages, self.calls, self.revoked = address, {}, [], []
        self.refresh_ok = True

    def add(self, gid, sender, subject, snippet="", thread=None):
        self.messages[gid] = {"id": gid, "threadId": thread or gid, "snippet": snippet,
                              "payload": {"headers": [{"name": "From", "value": sender},
                                                      {"name": "Subject", "value": subject},
                                                      {"name": "Date", "value": DATE}]}}

    def __call__(self, method, url, *, token=None, data=None, params=None):
        self.calls.append((method, url, params))
        if url == inbox.TOKEN_URL and data["grant_type"] == "authorization_code":
            return 200, {"access_token": "at", "refresh_token": "rt-" + data["code"],
                         "scope": inbox.SCOPE}
        if url == inbox.TOKEN_URL:
            return (200, {"access_token": "at"}) if self.refresh_ok else (400, {})
        if url == inbox.REVOKE_URL:
            self.revoked.append(data["token"])
            return 200, {}
        if url.endswith("/profile"):
            return 200, {"emailAddress": self.address}
        if url.endswith("/messages"):
            assert "after:" in params["q"] and "subject:(" in params["q"]
            return 200, {"messages": [{"id": gid} for gid in self.messages]}
        return 200, self.messages[url.rsplit("/", 1)[1]]


def connect(client, fake, monkeypatch, code="abc"):
    monkeypatch.setattr(inbox, "google", fake)
    url = client.post("/api/email/connect").json()["url"]
    query = parse_qs(urlsplit(url).query)
    assert query["scope"] == [inbox.SCOPE] and query["code_challenge_method"] == ["S256"]
    assert query["access_type"] == ["offline"]
    back = client.get("/api/email/oauth/callback", params={
        "state": query["state"][0], "code": code}, follow_redirects=False)
    assert back.status_code == 303, back.text
    return query["state"][0], back.headers["location"]


def triage_ai(monkeypatch, answers):
    seen = []

    def provider(schema, prompt, data):
        seen.append(data)
        return {"emails": [{"id": e["id"], "role": "", "applied_via": "", "needs_reply": False,
                            **answers[e["id"]]} for e in data["emails"]]}

    monkeypatch.setattr(inbox, "provider_json", provider)
    return seen


def test_connect_stores_an_encrypted_token_and_states_are_single_use(
        client, other, monkeypatch, google_env, db):
    register(client)
    fake = FakeGoogle()
    state, location = connect(client, fake, monkeypatch)
    assert location.endswith("/?view=applications&email=connected")
    [account] = client.get("/api/email").json()["accounts"]
    assert account["email"] == "satvik@example.com" and account["last_scanned_at"] is None
    from resumatch.models import EmailAccount
    stored = db.query(EmailAccount).one().refresh_token
    assert "rt-abc" not in stored and inbox.fernet().decrypt(stored.encode()) == b"rt-abc"
    replay = client.get("/api/email/oauth/callback", params={"state": state, "code": "x"},
                        follow_redirects=False)
    assert replay.headers["location"].endswith("email=expired")
    # Another user's browser cannot finish this user's connection.
    url = client.post("/api/email/connect").json()["url"]
    foreign = parse_qs(urlsplit(url).query)["state"][0]
    register(other, "other-inbox@example.com")
    stolen = other.get("/api/email/oauth/callback", params={"state": foreign, "code": "x"},
                       follow_redirects=False)
    assert stolen.headers["location"].endswith("email=expired")
    assert other.get("/api/email").json()["accounts"] == []
    assert client.post("/api/email/connect",
                       headers={"origin": "https://evil.example"}).status_code == 403


def test_scan_finds_applications_flags_replies_and_ignores_the_rest(
        client, monkeypatch, google_env):
    register(client)
    fake = FakeGoogle()
    connect(client, fake, monkeypatch)
    fake.add("m1", LINKEDIN, "Satvik, your application was sent to GTECH LLC",
             "Your application was sent to GTECH LLC", thread="t1")
    fake.add("m2", LINKEDIN, "Satvik, your application was sent to GTECH LLC", thread="t1")
    fake.add("m3", LINKEDIN, "Satvik, your application was sent to Humaniti AI")
    fake.add("m4", "Reshma LTM Interview <reshma@ltm.example>",
             "Hi Tejassatvik - Register your LTM Multinational Application",
             "Dear Tejassatvik Your Application for LTM Tech New Opportunity &amp; next steps")
    fake.add("m5", "Naukri MINIs <minis@naukri.com>",
             "₹50,000 basic. Here is how much of it goes into PF")
    fake.add("m6", "Careers <jobs@acme.example>", "Thank you for applying",
             "Thanks for your interest in the Backend Engineer role at Acme")
    seen = triage_ai(monkeypatch, {
        "m4": {"category": "response", "company": "LTM", "needs_reply": True},
        "m5": {"category": "not_job", "company": ""},
        # "Acme Corp" is not in the email: the company is dropped, the record kept.
        "m6": {"category": "application", "company": "Acme Corp", "role": "Backend Engineer",
               "applied_via": "company careers site"}})
    result = client.post("/api/email/scan").json()
    # LinkedIn confirmations are settled locally; only the others went to the AI.
    assert sorted(e["id"] for e in seen[0]["emails"]) == ["m4", "m5", "m6"]
    assert {k: result[k] for k in ("scanned", "applications", "responses", "ignored",
                                    "duplicates")} == {
        "scanned": 6, "applications": 3, "responses": 1, "ignored": 1, "duplicates": 1}
    run = client.get(f"/api/sessions/{result['run_id']}").json()
    assert run["source"] == "email" and run["state"] == "review"
    assert run["workflow_name"] == "Job applications"
    by_company = {c["details"]["company"]: c for c in run["captures"]}
    assert set(by_company) == {"GTECH LLC", "Humaniti AI", "LTM", ""}
    reply = by_company["LTM"]["details"]
    assert reply["action"] == "replied" and reply["person"] == "Reshma LTM Interview"
    assert reply["fields"]["needs_reply"] is True
    assert reply["followup_on"] == datetime.now(UTC).date().isoformat()
    assert "next steps" in reply["notes"] and "&amp;" not in reply["notes"]
    acme = by_company[""]["details"]
    assert acme["action"] == "applied" and acme["fields"]["role"] == "Backend Engineer"
    gtech = by_company["GTECH LLC"]["details"]
    assert gtech["fields"]["applied_via"] == "LinkedIn" and gtech["person"] == ""
    assert gtech["source_url"] == "https://mail.google.com/mail/u/satvik@example.com/#all/m1"
    counts = result["counts"]
    assert counts["applied_to_review"] == 3 and counts["responses_to_review"] == 1
    assert counts["applied"] == 0 and counts["needs_reply"] == 1

    # Applications bulk-approve; the reply needs your own confirmation.
    root = f"/api/sessions/{run['id']}"
    bulk = client.post(root + "/captures/bulk-approve", json={
        "capture_ids": [c["id"] for c in run["captures"]]}).json()
    assert len(bulk["approved"]) == 3 and len(bulk["skipped"]) == 1, bulk["skipped"]
    ltm = by_company["LTM"]
    assert client.post(root + f"/captures/{ltm['id']}/review", json={
        "decision": "approved", "details": ltm["details"], "confirmed_action": True
    }).status_code == 200
    assert client.post(root + "/transition", json={"action": "complete"}).status_code == 200
    overview = client.get("/api/overview").json()
    assert [f["details"]["company"] for f in overview["followups"]] == ["LTM"]
    counts = client.get("/api/email").json()["counts"]
    assert (counts["applied"], counts["applied_this_week"], counts["responses"]) == (3, 3, 1)

    # The next scan skips everything already seen and opens a fresh review run.
    again = client.post("/api/email/scan").json()
    assert again["scanned"] == 0 and again["run_id"] != result["run_id"]
    assert client.get("/api/email").json()["accounts"][0]["last_scanned_at"]


def test_inbox_run_coexists_with_a_manual_session(client, monkeypatch, google_env):
    register(client)
    fake = FakeGoogle()
    connect(client, fake, monkeypatch)
    fake.add("m1", LINKEDIN, "Satvik, your application was sent to GTECH LLC")
    triage_ai(monkeypatch, {})
    manual = start(client, workflow(client))
    scanned = client.post("/api/email/scan").json()
    assert scanned["applications"] == 1
    assert client.get("/api/overview").json()["current"]["id"] == manual["id"]
    # A capture into the inbox run through the normal capture route is refused (not active).
    assert client.post(f"/api/sessions/{scanned['run_id']}/captures", json={
        "request_id": "00000000-0000-4000-8000-000000000001",
        "details": {"source_url": "https://example.com"}}).status_code == 409


def test_ai_failure_keeps_local_results_and_retries_the_rest(client, monkeypatch, google_env):
    register(client)
    fake = FakeGoogle()
    connect(client, fake, monkeypatch)
    fake.add("m1", LINKEDIN, "Satvik, your application was sent to GTECH LLC")
    fake.add("m2", "Recruiter <r@ltm.example>", "Interview next steps")

    def down(*_):
        raise ValueError("Provider quota/rate limit reached.")

    monkeypatch.setattr(inbox, "provider_json", down)
    result = client.post("/api/email/scan").json()
    assert result["applications"] == 1 and "retried next scan" in result["warnings"][0]
    assert client.get("/api/email").json()["accounts"][0]["last_scanned_at"] is None
    triage_ai(monkeypatch, {"m2": {"category": "response", "company": "", "needs_reply": True}})
    retry = client.post("/api/email/scan").json()
    assert (retry["scanned"], retry["responses"]) == (1, 1)


def test_revoked_access_is_reported_and_disconnect_revokes(client, other, monkeypatch,
                                                           google_env):
    register(client)
    fake = FakeGoogle()
    connect(client, fake, monkeypatch)
    fake.refresh_ok = False
    result = client.post("/api/email/scan").json()
    assert "reconnect" in result["warnings"][0]
    [account] = client.get("/api/email").json()["accounts"]
    assert "reconnect" in account["last_error"]
    register(other, "other-revoke@example.com")
    assert other.delete(f"/api/email/accounts/{account['id']}").status_code == 404
    assert client.delete(f"/api/email/accounts/{account['id']}").status_code == 204
    assert fake.revoked == ["rt-abc"] and client.get("/api/email").json()["accounts"] == []
    assert client.post("/api/email/scan").status_code == 409


def test_unconfigured_server_says_what_is_missing(client):
    register(client)
    assert client.get("/api/email").json()["configured"] is False
    response = client.post("/api/email/connect")
    assert response.status_code == 503 and "GOOGLE_CLIENT_ID" in response.json()["detail"]


def test_views_are_not_replies_and_a_capped_scan_keeps_its_window(client, monkeypatch,
                                                                  google_env):
    register(client)
    fake = FakeGoogle()
    connect(client, fake, monkeypatch)
    monkeypatch.setattr(inbox, "MAX_NEW", 2)
    fake.add("m1", LINKEDIN, "Your application was viewed by Cheerio AI")
    fake.add("m2", LINKEDIN, "Satvik, your application was sent to GTECH LLC")
    fake.add("m3", LINKEDIN, "Satvik, your application was sent to Humaniti AI")
    seen = triage_ai(monkeypatch, {})
    first = client.post("/api/email/scan").json()
    assert first["scanned"] == 2 and "scan again" in first["warnings"][0]
    assert client.get("/api/email").json()["accounts"][0]["last_scanned_at"] is None
    second = client.post("/api/email/scan").json()
    assert second["scanned"] == 1 and second["warnings"] == []
    assert first["viewed"] + second["viewed"] == 1 and seen == []
    assert first["applications"] + second["applications"] == 2
    assert first["responses"] + second["responses"] == 0
    assert client.get("/api/email").json()["accounts"][0]["last_scanned_at"]
