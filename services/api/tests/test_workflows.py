import json
from datetime import UTC, datetime, timedelta
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
    # The unsupported AI value is skipped; the labeled line still fills the empty field.
    assert result["analysis"]["method"] == "llm"
    assert result["analysis"]["rejected_fields"] == ["person"]
    assert "person" in result["analysis"]["warning"]
    assert result["details"]["person"] == "Mira Example"

    fresh = capture(client, s, notes="Name: Ada Example",
                    source_url="https://linkedin.com/in/synthetic-ada")

    def edit_while_extracting(*_):
        details = {**fresh["details"], "notes": "Different raw source"}
        assert client.put(f"/api/sessions/{s['id']}/captures/{fresh['id']}", json={
            "details": details
        }).status_code == 200
        return {"fields": {}}

    monkeypatch.setattr("resumatch.workflows.provider_json", edit_while_extracting)
    fresh_path = f"/api/sessions/{s['id']}/captures/{fresh['id']}/process-ai"
    assert client.post(fresh_path).status_code == 409


def test_one_unsupported_ai_value_does_not_discard_the_supported_ones(client, monkeypatch):
    register(client)
    s = start(client, workflow(client))
    source = "Mira  Example\nCTO at Synthetic Labs \u2014 building \u201cpayments rails\u201d"
    c = capture(client, s, notes=source)
    calls = []

    def extract(*_):
        calls.append(1)
        return {"fields": {
            # Whitespace, case and smart punctuation differences are tolerated...
            "person": {"value": "Mira Example", "source_quote": "mira example"},
            "role": {"value": "CTO", "source_quote": 'CTO at Synthetic Labs - building "payments'},
            # ...but inferred or reworded facts are not.
            "industry": {"value": "Fintech", "source_quote": "building payments rails"},
            "location": {"value": "London", "source_quote": "Mira Example"},
            "company": {"value": "", "source_quote": ""},
        }}

    monkeypatch.setattr("resumatch.workflows.provider_json", extract)
    path = f"/api/sessions/{s['id']}/captures/{c['id']}/process-ai"
    result = client.post(path).json()["capture"]
    analysis = result["analysis"]
    assert analysis["method"] == "llm" and analysis["failure"] is None
    assert sorted(analysis["rejected_fields"]) == ["industry", "location"]
    assert sorted(analysis["filled_fields"]) == ["person", "role"]
    assert result["details"]["person"] == "Mira Example"
    assert result["details"]["fields"]["role"] == "CTO"
    assert not result["details"]["fields"].get("industry")
    assert not result["details"]["fields"].get("location")
    assert not result["details"]["company"] and result["original"] == c["original"]
    assert client.post(path).json()["cached"] is True and len(calls) == 1


def test_provider_failure_is_flagged_separately_from_rejected_output(client, monkeypatch):
    register(client)
    s = start(client, workflow(client))
    c = capture(client, s, notes="Name: Mira Example")
    path = f"/api/sessions/{s['id']}/captures/{c['id']}/process-ai"

    def unavailable(*_):
        raise ValueError("Provider quota/rate limit reached. Check billing or retry.")

    monkeypatch.setattr("resumatch.workflows.provider_json", unavailable)
    analysis = client.post(path).json()["capture"]["analysis"]
    assert analysis["method"] == "local" and analysis["failure"] == "provider"
    assert "quota" in analysis["warning"]
    monkeypatch.setattr("resumatch.workflows.provider_json", lambda *_: {"fields": {
        "action": {"value": "sent", "source_quote": "Name: Mira Example"}
    }})
    analysis = client.post(path).json()["capture"]["analysis"]
    assert analysis["method"] == "local" and analysis["failure"] == "output"


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


def finish_empty_run(client, run):
    path = f"/api/sessions/{run['id']}/transition"
    assert client.post(path, json={"action": "finish"}).status_code == 200
    assert client.post(path, json={"action": "complete"}).status_code == 200


def test_repeat_daily_run_names_custom_names_and_next_day(client, monkeypatch):
    register(client)
    parent = workflow(client)
    at = datetime(2026, 11, 11, 12, tzinfo=UTC)
    monkeypatch.setattr("resumatch.routes.now", lambda: at)
    first = start(client, parent, None)
    assert first["run_name"] == "2026-11-11"
    finish_empty_run(client, first)
    second = start(client, parent, " ")
    assert second["run_name"] == "2026-11-11 (1)"
    finish_empty_run(client, second)
    third = start(client, parent, "")
    assert third["run_name"] == "2026-11-11 (2)"
    finish_empty_run(client, third)
    custom = start(client, parent, "  Evening follow-ups  ")
    assert custom["run_name"] == "Evening follow-ups"
    finish_empty_run(client, custom)
    renamed = client.put(f"/api/sessions/{second['id']}/name", json={
        "run_name": "Lunch break"
    })
    assert renamed.status_code == 200
    fourth = start(client, parent, None)
    assert fourth["run_name"] == "2026-11-11 (4)"
    finish_empty_run(client, fourth)
    different = workflow(client, name="Another workflow")
    independent = start(client, different, None)
    assert independent["run_name"] == "2026-11-11"
    finish_empty_run(client, independent)
    at += timedelta(days=1)
    tomorrow = start(client, parent, None)
    assert tomorrow["run_name"] == "2026-11-12"


def test_default_run_name_avoids_explicit_name_collision_and_preview_matches(client):
    register(client)
    parent = workflow(client)
    today = datetime.now(UTC).date().isoformat()
    first = start(client, parent, f"{today} (5)")
    finish_empty_run(client, first)
    preview = client.get("/api/workflows").json()[0]["next_run_name"]
    assert preview == f"{today} (6)"
    run = start(client, parent, None)
    assert run["run_name"] == preview


def test_ai_reruns_preserve_manual_values_and_concurrent_edits(client, monkeypatch):
    register(client)
    extra = [
        {"key": "team_size", "label": "Team size", "type": "number"},
        {"key": "is_founder", "label": "Is founder", "type": "boolean"},
    ]
    parent = workflow(client, fields=[*template()["fields"], *extra])
    run = start(client, parent)
    source = "AI Name\nAI Company\nCTO\nExample City\nTeam size: 12\nIs founder: true"
    record = capture(client, run, notes=source, person="Manual Name", company="Manual Company",
                     fields={"role": "Manual role", "team_size": 0, "is_founder": False})
    root = f"/api/sessions/{run['id']}/captures/{record['id']}"
    calls = []

    def provider(_schema, _prompt, _data):
        calls.append(True)
        if len(calls) == 1:
            # While the external call is pending, save edits from another request/tab.
            saved = {**record["details"], "person": "Manual name entered during AI",
                     "fields": {**record["details"]["fields"], "role": "New manual role"}}
            response = client.put(root, json={"details": saved})
            assert response.status_code == 200, response.text
        return {"fields": {
            "person": {"value": "AI Name", "source_quote": "AI Name"},
            "company": {"value": "AI Company", "source_quote": "AI Company"},
            "role": {"value": "CTO", "source_quote": "CTO"},
            "location": {"value": "Example City", "source_quote": "Example City"},
            "team_size": {"value": 12, "source_quote": "Team size: 12"},
            "is_founder": {"value": True, "source_quote": "Is founder: true"},
        }}

    monkeypatch.setattr("resumatch.workflows.provider_json", provider)
    first = client.post(root + "/process-ai")
    assert first.status_code == 200, first.text
    stored = first.json()["capture"]
    assert stored["details"]["person"] == "Manual name entered during AI"
    assert stored["details"]["company"] == "Manual Company"
    assert stored["details"]["fields"] == {
        "role": "New manual role", "team_size": 0, "is_founder": False, "location": "Example City"
    }
    assert stored["analysis"]["filled_fields"] == ["location"]
    assert set(stored["analysis"]["preserved_fields"]) == {
        "person", "company", "role", "team_size", "is_founder"
    }
    # Editing a field after successful extraction and hitting Process again must not replay it.
    edited = {**stored["details"], "company": "Company corrected after AI"}
    assert client.put(root, json={"details": edited}).status_code == 200
    cached = client.post(root + "/process-ai").json()
    assert cached["cached"] is True and len(calls) == 1
    assert cached["capture"]["details"] == edited
    # A changed raw source legitimately calls AI again, still preserving every populated field.
    edited["notes"] = source + "\nExtra source context"
    assert client.put(root, json={"details": edited}).status_code == 200
    retried = client.post(root + "/process-ai").json()["capture"]
    assert len(calls) == 2 and retried["details"] == edited
    assert retried["analysis"]["filled_fields"] == []
    assert retried["original"] == record["original"]
    assert retried["decision"] == "pending"


def test_reused_pasted_text_is_flagged_and_bulk_approve_skips_judgement_calls(client, other):
    register(client)
    s = start(client, workflow(client))
    pasted = "Anchal Example · 2nd\nPrecision hiring\nSynthetic Partners"
    first = capture(client, s, notes=pasted, source_url="https://www.linkedin.com/in/anchal")
    stale = capture(client, s, notes=pasted + "\n", source_url="https://www.linkedin.com/in/oss")
    plain = capture(client, s, notes="Name: Ada Example", source_url="https://example.com/ada")
    sent = capture(client, s, notes="Name: Bo Example", action="sent",
                   source_url="https://example.com/bo")
    late = capture(client, s, notes="Name: Cy Example", source_url="https://example.com/cy")
    root = f"/api/sessions/{s['id']}"
    records = {c["id"]: c for c in client.get(root).json()["captures"]}
    assert records[stale["id"]]["same_raw_text_as"] == first["id"]
    assert records[first["id"]]["same_raw_text_as"] == stale["id"]
    assert records[plain["id"]]["same_raw_text_as"] is None

    ids = [first["id"], stale["id"], plain["id"], sent["id"]]
    bulk = root + "/captures/bulk-approve"
    assert client.post(bulk, json={"capture_ids": ids}).status_code == 409
    assert client.post(root + "/transition", json={"action": "finish"}).status_code == 200
    register(other, "other-bulk@example.com")
    assert other.post(root + "/captures/bulk-approve",
                      json={"capture_ids": ids}).status_code == 404
    result = client.post(root + "/captures/bulk-approve", json={"capture_ids": ids}).json()
    assert result["approved"] == [plain["id"]]
    reasons = {item["id"]: item["reason"] for item in result["skipped"]}
    assert set(reasons) == {first["id"], stale["id"], sent["id"]}
    assert "confirmation" in reasons[sent["id"]] and "duplicate" in reasons[stale["id"]]
    decisions = {c["id"]: c["decision"] for c in result["session"]["captures"]}
    assert decisions[plain["id"]] == "approved" and decisions[late["id"]] == "pending"
    assert decisions[sent["id"]] == decisions[stale["id"]] == "pending"
    parent = client.get("/api/workflows").json()[0]
    assert (parent["record_count"], parent["pending_count"], parent["approved_count"]) == (5, 4, 1)
    assert (parent["runs"][0]["pending_count"], parent["runs"][0]["approved_count"]) == (4, 1)
    again = client.post(root + "/captures/bulk-approve", json={"capture_ids": [plain["id"]]})
    assert again.json()["skipped"] == [{"id": plain["id"], "reason": "Already reviewed"}]
