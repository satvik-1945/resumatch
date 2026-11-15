from datetime import UTC, datetime

from tests.test_workflows import capture, complete, register, start, workflow

from resumatch.activity import PALETTE
from resumatch.workflow_contracts import template

MONTH = datetime.now(UTC).strftime("%Y-%m")
TODAY = datetime.now(UTC).date().isoformat()


def approved_run(client, w, name, people):
    s = start(client, w, name=name)
    captures = [capture(client, s, person=p, source_url=f"https://linkedin.com/in/{p.lower()}")
                for p in people]
    root = f"/api/sessions/{s['id']}"
    assert client.post(root + "/transition", json={"action": "finish"}).status_code == 200
    for c in captures:
        assert client.post(root + f"/captures/{c['id']}/review", json={
            "decision": "approved", "details": c["details"], "confirmed_action": True
        }).status_code == 200
    assert client.post(root + "/transition", json={"action": "complete"}).status_code == 200
    return s


def test_workflows_get_distinct_colors_and_owner_can_change_them(client, other):
    register(client)
    first = workflow(client)
    second = workflow(client, **template("contact_outreach"))
    assert (first["color"], second["color"]) == PALETTE[:2]
    assert workflow(client, name="Picked", color="#ABCDEF")["color"] == "#abcdef"
    path = f"/api/workflows/{first['id']}/color"
    assert client.put(path, json={"color": "#7FD6D0"}).json()["color"] == "#7fd6d0"
    assert client.put(path, json={"color": "red"}).status_code == 422
    assert client.put(path, json={"color": "#7fd6d0"},
                      headers={"origin": "https://evil.example"}).status_code == 403
    register(other, "other-colors@example.com")
    assert other.put(path, json={"color": "#000000"}).status_code == 404


def test_calendar_shows_only_completed_runs_with_approved_records(client, other):
    register(client)
    founders = workflow(client)
    outreach = workflow(client, **template("contact_outreach"))
    approved_run(client, founders, "Founders", ["Ada", "Grace"])
    approved_run(client, outreach, "Outreach", ["Linus"])
    # A completed run whose only record was discarded does not light up the day.
    s = start(client, founders, name="Discarded only")
    c = capture(client, s, person="Nobody", source_url="https://linkedin.com/in/nobody")
    root = f"/api/sessions/{s['id']}"
    client.post(root + "/transition", json={"action": "finish"})
    client.post(root + f"/captures/{c['id']}/review",
                json={"decision": "discarded", "details": c["details"]})
    client.post(root + "/transition", json={"action": "complete"})
    # An active run with a pending capture does not count either.
    capture(client, start(client, outreach, name="Still open"), person="Pending")

    month = client.get("/api/activity").json()
    assert month["month"] == MONTH and month["today"] == TODAY
    day = next(d for d in month["days"] if d["date"] == TODAY)
    assert sorted(r["run_name"] for r in day["runs"]) == ["Founders", "Outreach"]
    assert sorted(r["color"] for r in day["runs"]) == sorted([founders["color"],
                                                               outreach["color"]])
    assert day["approved_records"] == 3
    assert month["summary"] == {**month["summary"], "active_days": 1, "completed_runs": 2,
                                "approved_records": 3}
    assert {w["name"] for w in month["workflows"]} == {founders["name"], outreach["name"]}
    assert client.get("/api/activity", params={"month": "2020-02"}).json()["summary"][
        "completed_runs"] == 0
    assert len(client.get("/api/activity", params={"month": "2024-02"}).json()["days"]) == 29
    assert client.get("/api/activity", params={"month": "2024-13"}).status_code == 422
    assert client.get("/api/activity", params={"month": "May"}).status_code == 422
    register(other, "other-calendar@example.com")
    assert other.get("/api/activity").json()["summary"]["completed_runs"] == 0


def test_recap_compares_with_the_previous_run_of_the_same_workflow(client):
    register(client)
    w = workflow(client)
    first = approved_run(client, w, "Day one", ["Ada"])
    recap = client.get(f"/api/sessions/{first['id']}/recap").json()
    assert recap["progress"]["previous"] is None and recap["progress"]["color"] == w["color"]
    assert recap["progress"]["personal_best_records"] is False
    # A run in another workflow is never the baseline.
    approved_run(client, workflow(client, name="Other"), "Elsewhere", ["X", "Y", "Z"])
    second = approved_run(client, w, "Day two", ["Grace", "Linus"])
    progress = client.get(f"/api/sessions/{second['id']}/recap").json()["progress"]
    assert progress["previous"]["run_name"] == "Day one"
    assert progress["record_delta"] == 1 and progress["personal_best_records"] is True
    # The first run's recap is unchanged by later runs.
    again = client.get(f"/api/sessions/{first['id']}/recap").json()["progress"]
    assert again["previous"] is None


def test_existing_completion_helper_still_lights_the_calendar(client):
    register(client)
    w = workflow(client)
    s = start(client, w)
    complete(client, s, capture(client, s, person="Mira"))
    day = next(d for d in client.get("/api/activity").json()["days"] if d["date"] == TODAY)
    assert [r["workflow_name"] for r in day["runs"]] == [w["name"]]
