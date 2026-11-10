import json
from uuid import uuid4

import pytest

from resumatch.workflow_contracts import compile_definition, template, transform_output


def register(client, email="workflows@example.com"):
    assert client.post("/api/auth/register", json={
        "email": email, "password": "synthetic workflow passphrase"
    }).status_code == 201


def workflow(client, **changes):
    response = client.post("/api/workflows", json={**template(), **changes})
    assert response.status_code == 201, response.text
    return response.json()


def start(client, w, name="First day"):
    r = client.post("/api/sessions", json={
        "workflow_id": w["id"], "intention": "Find relevant founders", "run_name": name
    })
    assert r.status_code == 201, r.text
    return r.json()


def capture(client, s, **details):
    r = client.post(f"/api/sessions/{s['id']}/captures", json={
        "request_id": str(uuid4()), "details": {
            "source_url": "https://linkedin.com/in/synthetic-person", **details
        }
    })
    assert r.status_code == 201, r.text
    return r.json()


def complete(client, s, c):
    root = f"/api/sessions/{s['id']}"
    assert client.post(root + "/transition", json={"action": "finish"}).status_code == 200
    assert client.post(root + f"/captures/{c['id']}/review", json={
        "decision": "approved", "details": c["details"], "confirmed_action": True
    }).status_code == 200
    assert client.post(root + "/transition", json={"action": "complete"}).status_code == 200


def test_parent_workflows_runs_contract_and_isolation(client, other):
    register(client)
    register(other, "other-workflow@example.com")
    assert other.get("/api/workflows").json() == []
    w = workflow(client)
    contract = client.get(f"/api/workflows/{w['id']}/contract").json()
    assert contract["dsl_version"] == 1 and "source_quote" in json.dumps(contract["output_schema"])
    assert "fields." in contract["jsonata"]
    s = start(client, w)
    assert s["workflow_name"] == w["name"] and s["run_name"] == "First day"
    assert s["workflow_version"] == 1 and s["field_definition"] == w["fields"]
    for path in ("contract", "records"):
        assert other.get(f"/api/workflows/{w['id']}/{path}").status_code == 404
    assert other.post("/api/sessions", json={
        "workflow_id": w["id"], "intention": "Injected owner"
    }).status_code == 404
    stolen = other.put(f"/api/sessions/{s['id']}/name", json={"run_name": "Stolen"})
    assert stolen.status_code == 404
    rename = client.put(f"/api/sessions/{s['id']}/name", json={
        "run_name": "Morning fintech sprint"
    })
    assert rename.json()["run_name"] == "Morning fintech sprint"


def test_versions_add_fields_to_existing_run_explicitly(client):
    register(client)
    w = workflow(client)
    s = start(client, w)
    extra = {"key": "team_size", "label": "Team size", "type": "number",
             "instruction": "Explicit size only"}
    updated = client.put(f"/api/workflows/{w['id']}", json={
        **template(), "fields": [*w["fields"], extra], "expected_version": 1
    })
    assert updated.status_code == 200 and updated.json()["version"] == 2
    assert client.get(f"/api/sessions/{s['id']}").json()["workflow_version"] == 1
    assert client.post(f"/api/sessions/{s['id']}/captures", json={
        "request_id": str(uuid4()), "details": {
            "source_url": "https://example.com", "fields": {"team_size": 12}
        }
    }).status_code == 422
    synced = client.post(f"/api/sessions/{s['id']}/sync-workflow")
    assert synced.status_code == 200 and synced.json()["workflow_version"] == 2
    c = capture(client, s, fields={"team_size": 12})
    assert c["details"]["fields"]["team_size"] == 12
    assert client.put(f"/api/workflows/{w['id']}", json={
        **template(), "expected_version": 1
    }).status_code == 409


@pytest.mark.parametrize("field", [
    {"key": "action", "label": "Action"},
    {"key": "x);$eval('bad')", "label": "Code"},
    {"key": "person", "label": "Duplicate"},
])
def test_custom_fields_cannot_override_actions_or_inject_mapping(client, field):
    register(client)
    assert client.post("/api/workflows", json={
        **template(), "fields": [*template()["fields"], field]
    }).status_code == 422


def test_consolidation_keeps_runs_and_pending_decisions(client):
    register(client)
    w = workflow(client)
    first = start(client, w, "Yesterday")
    c = capture(client, first, person="Mira Example", company="Synthetic Labs",
                fields={"role": "CTO"})
    complete(client, first, c)
    second = start(client, w, "Today")
    capture(client, second, person="Mira Example", fields={"location": "Example City"})
    result = client.get(f"/api/workflows/{w['id']}/records").json()
    assert result["contact_count"] == 1 and result["record_count"] == 2
    assert result["contacts"][0]["company"] == "Synthetic Labs"
    assert result["contacts"][0]["fields"] == {"role": "CTO", "location": "Example City"}
    assert {e["decision"] for e in result["contacts"][0]["entries"]} == {"pending", "approved"}
    parents = client.get("/api/workflows").json()
    assert len(parents[0]["runs"]) == 2


def test_real_jsonata_mapping_and_evidence_rules():
    definition = compile_definition([*template()["fields"], {
        "key": "team_size", "label": "Team size", "type": "number"
    }])
    source = "Mira Example\nRole: CTO\nTeam size: 12"
    result = transform_output({"fields": {
        "person": {"value": "Mira Example", "source_quote": "Mira Example"},
        "role": {"value": "CTO", "source_quote": "Role: CTO"},
        "team_size": {"value": 12, "source_quote": "Team size: 12"},
        "company": None,
    }}, source, definition)
    assert result == {"person": "Mira Example", "role": "CTO", "team_size": 12}
    with pytest.raises(ValueError):
        transform_output({"fields": {"person": {"value": "Invented", "source_quote": source}}},
                         source, definition)
    with pytest.raises(ValueError):
        transform_output({"fields": {"action": {"value": "sent", "source_quote": source}}},
                         source, definition)


def test_workflow_ai_fills_empty_fields_preserves_manual_and_caches(client, other, monkeypatch):
    register(client)
    w = workflow(client)
    s = start(client, w)
    source = "Mira Example\nSynthetic Labs\nCTO\nExample City\nFintech"
    c = capture(client, s, person="Manual Person", notes=source)
    calls = []

    def extract(schema, prompt, data):
        calls.append(data)
        assert "hiring_signal" in schema["properties"]["fields"]["properties"]
        assert "untrusted data" in prompt
        return {"fields": {key: {"value": value, "source_quote": value} for key, value in {
            "person": "Mira Example", "company": "Synthetic Labs", "role": "CTO",
            "location": "Example City", "industry": "Fintech"
        }.items()}}

    monkeypatch.setattr("resumatch.workflows.provider_json", extract)
    path = f"/api/sessions/{s['id']}/captures/{c['id']}/process-ai"
    result = client.post(path)
    assert result.status_code == 200, result.text
    updated = result.json()["capture"]
    assert updated["details"]["person"] == "Manual Person"
    assert updated["details"]["company"] == "Synthetic Labs"
    assert updated["details"]["fields"]["role"] == "CTO"
    assert updated["details"]["action"] == "researched" and updated["decision"] == "pending"
    assert updated["original"] == c["original"]
    assert updated["analysis"]["preserved_fields"] == ["person"]
    assert client.post(path).json()["cached"] is True and len(calls) == 1
    assert client.get("/api/overview").json()["week"]["counts"] == {}
    register(other, "other-ai@example.com")
    assert other.post(path).status_code == 404
    assert client.post(path, headers={"origin": "https://evil.example"}).status_code == 403


def test_workflow_ai_bad_output_and_concurrent_edit(client, monkeypatch):
    register(client)
    w = workflow(client)
    s = start(client, w)
    c = capture(client, s, notes="Name: Mira Example\nCompany: Synthetic Labs")
    path = f"/api/sessions/{s['id']}/captures/{c['id']}/process-ai"
    monkeypatch.setattr("resumatch.workflows.provider_json", lambda *_: {
        "fields": {"person": {"value": "Unfounded", "source_quote": "Name: Mira Example"}}
    })
    result = client.post(path).json()["capture"]
    assert result["analysis"]["method"] == "local" and result["analysis"]["warning"]
    assert result["details"]["person"] == "Mira Example"

    def edit_while_extracting(*_):
        details = {**result["details"], "notes": "Different raw source"}
        assert client.put(f"/api/sessions/{s['id']}/captures/{c['id']}", json={
            "details": details
        }).status_code == 200
        return {"fields": {}}

    monkeypatch.setattr("resumatch.workflows.provider_json", edit_while_extracting)
    assert client.post(path).status_code == 409


def test_forty_raw_records_process_without_inventing_activity(client, monkeypatch):
    register(client)
    w = workflow(client)
    s = start(client, w)
    entries = []
    for i in range(40):
        entries.append(capture(client, s, source_url=f"https://example.com/contact/{i}",
                               notes=f"Name: Synthetic Person {i}\nCompany: Synthetic Labs"))

    def provider(_schema, _prompt, data):
        name = data["raw_text"].splitlines()[0].split(": ", 1)[1]
        return {"fields": {"person": {"value": name, "source_quote": "Name: " + name}}}

    monkeypatch.setattr("resumatch.workflows.provider_json", provider)
    for c in entries:
        result = client.post(f"/api/sessions/{s['id']}/captures/{c['id']}/process-ai")
        assert result.status_code == 200, result.text
        assert result.json()["capture"]["analysis"]["method"] == "llm"
    run = client.get(f"/api/sessions/{s['id']}").json()
    assert run["pending_count"] == 40 and run["approved_count"] == 0
    assert len({c["details"]["person"] for c in run["captures"]}) == 40
    assert all(c["details"]["action"] == "researched" for c in run["captures"])
    assert client.get("/api/overview").json()["week"]["counts"] == {}


def test_connection_requests_are_confirmed_and_separate_from_initial_messages(client):
    register(client)
    w = workflow(client)
    s = start(client, w)
    c = capture(client, s, person="Mira Example", action="connection_requested")
    root = f"/api/sessions/{s['id']}"
    client.post(root + "/transition", json={"action": "finish"})
    path = root + f"/captures/{c['id']}/review"
    assert client.post(path, json={
        "decision": "approved", "details": c["details"]
    }).status_code == 422
    assert client.post(path, json={
        "decision": "approved", "details": c["details"], "confirmed_action": True
    }).status_code == 200
    client.post(root + "/transition", json={"action": "complete"})
    counts = client.get(root + "/recap").json()["payload"]["action_counts"]
    assert counts["connection_requested"] == 1 and counts["sent"] == 0
