import json

from tests.test_briefs import SITE, founder_record
from tests.test_workflows import capture, register, start, workflow

from resumatch import briefs, intelligence

USAGE = {"prompt_tokens": 1200, "completion_tokens": 300}


def fake_provider(monkeypatch, content):
    """Replace only the HTTP request, so the real tracing in provider_json runs."""
    calls = []

    def call(schema, instruction, data, max_tokens):
        calls.append(data)
        return (content if isinstance(content, str) else json.dumps(content)), USAGE

    monkeypatch.setattr(intelligence, "configured", lambda: True)
    monkeypatch.setattr(intelligence, "call_provider", call)
    return calls


def runs(client, **params):
    return client.get("/api/ai-runs", params=params).json()["runs"]


def test_brief_run_stores_research_input_output_and_rejections(client, monkeypatch):
    register(client)
    founder_record(client)
    client.put("/api/profile", json={"about_me": "FDE in fintech."})
    monkeypatch.setattr(briefs, "fetch_company", lambda u: [{"url": u, "text": SITE}])
    fake_provider(monkeypatch, {
        "company_facts": [
            {"fact": "Recon APIs for issuers",
             "source_quote": "reconciliation APIs for card issuers"},
            {"fact": "Series B", "source_quote": "Raised a $20M Series B"},
        ],
        "hooks": ["your recon APIs"], "credentials": ["FDE in fintech"], "bridges": [],
        "asks": ["just saying hi"], "avoid": [], "reference_draft": "Hey Mira,"})
    url = "https://www.linkedin.com/in/mira-example"
    made = client.post("/api/contacts/brief", json={
        "url": url, "company_url": "https://synthetic-pay.example", "context": "Goal: chat"})
    assert made.status_code == 200
    [summary] = runs(client)
    assert summary["kind"] == "brief" and summary["status"] == "partial"
    assert summary["subject"] == "linkedin:mira-example"
    assert summary["prompt_tokens"] == 1200 and summary["latency_ms"] is not None
    assert made.json()["brief"]["research"]["ai_run_id"] == str(summary["id"])
    detail = client.get(f"/api/ai-runs/{summary['id']}").json()
    assert detail["research"] == {"company_url": "https://synthetic-pay.example", "pages": [
        {"url": "https://synthetic-pay.example", "chars": len(SITE)}]}
    assert detail["input"]["website_text"] == SITE
    assert detail["input"]["outreach_context"] == "Goal: chat"
    assert len(detail["output"]["company_facts"]) == 2
    assert [f["fact"] for f in detail["result"]["facts"]] == ["Recon APIs for issuers"]
    assert detail["rejected"] == [{"fact": "Series B", "source_quote": "Raised a $20M Series B"}]
    assert detail["prompt"]["instruction"] == briefs.BRIEF_PROMPT
    assert detail["meta"] == {"company_url": "https://synthetic-pay.example", "has_context": True}
    # Same prompt again → one version with two runs.
    client.post("/api/contacts/brief", json={"url": url})
    [version] = client.get("/api/ai-runs/stats").json()["versions"]
    assert version["kind"] == "brief" and version["runs"] == 2
    assert version["statuses"]["partial"] == 2 and version["prompt_tokens"] == 2400


def test_failures_are_kept_with_their_reason(client, monkeypatch):
    register(client)
    founder_record(client)
    client.put("/api/profile", json={"about_me": "FDE in fintech."})
    url = "https://www.linkedin.com/in/mira-example"
    # Validation failures before any research or AI call are not logged.
    assert client.post("/api/contacts/brief", json={
        "url": "https://www.linkedin.com/in/nobody"}).status_code == 404
    assert runs(client) == []
    # Unconfigured provider.
    assert client.post("/api/contacts/brief", json={"url": url}).status_code == 502
    [unconfigured] = runs(client)
    assert unconfigured["status"] == "provider_error" and "LLM_API_KEY" in unconfigured["error"]

    def unreachable(u):
        raise ValueError("Company website unreachable or timed out")

    monkeypatch.setattr(briefs, "fetch_company", unreachable)
    assert client.post("/api/contacts/brief", json={
        "url": url, "company_url": "https://down.example"}).status_code == 422
    fetch = runs(client, status="fetch_error")[0]
    assert client.get(f"/api/ai-runs/{fetch['id']}").json()["research"]["error"].startswith(
        "Company website unreachable")
    # Model answered with something that is not JSON.
    fake_provider(monkeypatch, "Sure! Here are some talking points")
    assert client.post("/api/contacts/brief", json={"url": url}).status_code == 502
    garbled = runs(client)[0]
    assert garbled["status"] == "provider_error"
    detail = client.get(f"/api/ai-runs/{garbled['id']}").json()
    assert detail["output"] == {"unparsed": "Sure! Here are some talking points"}
    # Model answered JSON in the wrong shape: kept as rejected output.
    fake_provider(monkeypatch, {"hooks": ["only this"]})
    assert client.post("/api/contacts/brief", json={"url": url}).status_code == 502
    wrong = client.get(f"/api/ai-runs/{runs(client)[0]['id']}").json()
    assert wrong["status"] == "rejected" and wrong["output"] == {"hooks": ["only this"]}
    assert client.get("/api/contacts/lookup", params={"url": url}).json()["brief"] is None


def test_capture_and_persona_runs_link_back_and_take_feedback(client, other, monkeypatch):
    register(client)
    s = start(client, workflow(client))
    c = capture(client, s, notes="Mira Example\nCTO at Synthetic Labs")
    fake_provider(monkeypatch, {"fields": {
        "person": {"value": "Mira Example", "source_quote": "Mira Example"},
        "location": {"value": "London", "source_quote": "Mira Example in London"}}})
    result = client.post(f"/api/sessions/{s['id']}/captures/{c['id']}/process-ai").json()
    run_id = result["capture"]["analysis"]["ai_run_id"]
    detail = client.get(f"/api/ai-runs/{run_id}").json()
    assert detail["kind"] == "capture_fields" and detail["status"] == "partial"
    assert detail["subject"] == c["id"] and detail["rejected"] == ["location"]
    assert detail["input"] == {"raw_text": "Mira Example\nCTO at Synthetic Labs"}
    assert detail["meta"]["workflow_version"] == 1 and detail["result"]["filled_fields"]

    client.put("/api/profile",
               json={"about_me": "", "resume_text": "Built 2 products from scratch"})
    fake_provider(monkeypatch, {
        "headline": "Engineer", "summary": "", "domains": [], "strengths": [],
        "proof_points": [{"point": "Built 2 products", "evidence": "Built 2 products"},
                         {"point": "Led 40 people", "evidence": "Led 40 people"}]})
    persona = client.post("/api/profile/persona").json()["persona"]
    persona_run = client.get(f"/api/ai-runs/{persona['ai_run_id']}").json()
    assert persona_run["status"] == "partial" and persona["dropped"] == 1
    assert persona_run["rejected"] == [{"point": "Led 40 people", "evidence": "Led 40 people"}]

    rated = client.put(f"/api/ai-runs/{run_id}/feedback",
                       json={"rating": -1, "feedback": "Missed the company"}).json()
    assert rated["rating"] == -1 and rated["feedback"] == "Missed the company"
    assert client.put(f"/api/ai-runs/{run_id}/feedback", json={"rating": 2}).status_code == 422
    assert client.put(f"/api/ai-runs/{run_id}/feedback", json={"rating": 1},
                      headers={"origin": "https://evil.example"}).status_code == 403
    cleared = client.put(f"/api/ai-runs/{run_id}/feedback", json={"rating": 0}).json()
    assert cleared["rating"] is None
    stats = {v["kind"]: v for v in client.get("/api/ai-runs/stats").json()["versions"]}
    assert set(stats) == {"capture_fields", "persona"}
    assert [r["kind"] for r in runs(client, kind="persona")] == ["persona"]
    register(other, "other-ai-runs@example.com")
    assert other.get(f"/api/ai-runs/{run_id}").status_code == 404
    assert other.put(f"/api/ai-runs/{run_id}/feedback", json={"rating": 1}).status_code == 404
    assert runs(other) == []
