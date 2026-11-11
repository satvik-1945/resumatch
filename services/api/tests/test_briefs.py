import pytest
from tests.test_workflows import capture, complete, register, start, workflow

from resumatch import briefs
from resumatch.workflow_contracts import template

SITE = ("Synthetic Pay\nSynthetic Pay builds reconciliation APIs for card issuers.\n"
        "Trusted by 40 neobanks across Europe.")


def founder_record(client):
    w = workflow(client)
    s = start(client, w)
    c = capture(client, s, person="Mira Example", company="Synthetic Pay",
                notes="Mira Example · Founder at Synthetic Pay",
                source_url="https://www.linkedin.com/in/mira-example/")
    complete(client, s, c)
    return w


def test_lookup_finds_profile_across_workflows_and_is_owner_scoped(client, other):
    register(client)
    founder_record(client)
    outreach = workflow(client, **template("contact_outreach"))
    s = start(client, outreach, name="Outreach")
    url = "https://linkedin.com/in/Mira-Example?trk=feed"
    found = client.get("/api/contacts/lookup", params={"url": url}).json()
    assert found["found"] is True and found["contact"]["person"] == "Mira Example"
    assert found["records"][0]["workflow_name"] == "Fintech founder connections"
    assert found["records"][0]["decision"] == "approved" and found["about_me_set"] is False
    missing = client.get("/api/contacts/lookup",
                         params={"url": "https://www.linkedin.com/in/nobody"}).json()
    assert missing["found"] is False and missing["records"] == []
    assert client.get("/api/contacts/lookup",
                      params={"url": "https://example.com/about"}).status_code == 422
    register(other, "other-briefs@example.com")
    assert other.get("/api/contacts/lookup", params={"url": url}).json()["found"] is False
    assert s["workflow_id"] == outreach["id"]


def test_brief_grounds_company_facts_and_never_records_activity(client, monkeypatch):
    register(client)
    founder_record(client)
    url = "https://www.linkedin.com/in/mira-example"
    assert client.post("/api/contacts/brief", json={"url": url}).status_code == 422  # no about me
    assert client.put("/api/profile", json={
        "about_me": "FDE in fintech, 2.5 years. Built 2 products from scratch."
    }).status_code == 200
    assert client.post("/api/contacts/brief", json={
        "url": "https://www.linkedin.com/in/nobody"}).status_code == 404
    monkeypatch.setattr(briefs, "fetch_company", lambda u: [{"url": u, "text": SITE}])
    seen = {}

    def provider(schema, prompt, data):
        seen.update(data)
        assert "HANDWRITE" in prompt and "company_facts" in schema["properties"]
        return {
            "company_facts": [
                {"fact": "Reconciliation APIs for card issuers",
                 "source_quote": "builds reconciliation  APIs for card issuers"},
                {"fact": "Raised a Series B", "source_quote": "Raised a $20M Series B"},
            ],
            "hooks": ["your reconciliation APIs for card issuers"],
            "credentials": ["FDE in fintech, 2.5 years"], "bridges": ["seen recon pain firsthand"],
            "asks": ["just saying hi", "open to a short chat"], "avoid": ["pitching"],
            "reference_draft": "Hey Mira,\nSaw what you're building at Synthetic Pay...",
        }

    monkeypatch.setattr(briefs, "provider_json", provider)
    result = client.post("/api/contacts/brief", json={
        "url": url, "company_url": "https://synthetic-pay.example"}).json()
    research = result["brief"]["research"]
    assert [f["fact"] for f in research["facts"]] == ["Reconciliation APIs for card issuers"]
    assert research["dropped_facts"] == 1
    assert result["brief"]["brief"]["hooks"] == ["your reconciliation APIs for card issuers"]
    assert seen["sender_background"].startswith("FDE") and seen["website_text"] == SITE
    assert seen["contact_records"]["company"] == "Synthetic Pay"
    # Regenerating without a URL reuses the saved company site; the brief stays one row.
    again = client.post("/api/contacts/brief", json={"url": url}).json()
    assert again["brief"]["company_url"] == "https://synthetic-pay.example"
    found = client.get("/api/contacts/lookup", params={"url": url}).json()
    assert found["brief"]["brief"]["asks"] == ["just saying hi", "open to a short chat"]
    assert [r["action"] for r in found["records"]] == ["researched"]
    assert client.get("/api/overview").json()["week"]["counts"] == {"researched": 1}
    assert client.post("/api/contacts/brief", json={"url": url},
                       headers={"origin": "https://evil.example"}).status_code == 403


def test_extension_lookup_and_brief_use_pairing(client, monkeypatch):
    register(client)
    founder_record(client)
    client.put("/api/profile", json={"about_me": "Engineer in fintech."})
    eid = "b" * 32
    token = client.post("/api/pairings", json={"extension_id": eid}).json()["token"]
    client.cookies.clear()
    headers = {"Authorization": "Bearer " + token, "Origin": "chrome-extension://" + eid,
               "X-Extension-ID": eid}
    url = "https://www.linkedin.com/in/mira-example/recent-activity/"
    found = client.get("/api/extension/contacts/lookup", params={"url": url}, headers=headers)
    assert found.json()["found"] is True and found.json()["about_me_set"] is True
    assert client.get("/api/extension/contacts/lookup", params={"url": url}).status_code == 401
    monkeypatch.setattr(briefs, "provider_json", lambda *_: {
        "company_facts": [], "hooks": ["h"], "credentials": ["c"], "bridges": [], "asks": ["a"],
        "avoid": [], "reference_draft": "Hey Mira,"})
    made = client.post("/api/extension/contacts/brief", json={"url": url}, headers=headers)
    assert made.status_code == 200 and made.json()["brief"]["research"]["pages"] == []


def test_provider_failure_is_reported_and_nothing_saved(client, monkeypatch):
    register(client)
    founder_record(client)
    client.put("/api/profile", json={"about_me": "Engineer in fintech."})
    result = client.post("/api/contacts/brief",
                         json={"url": "https://www.linkedin.com/in/mira-example"})
    assert result.status_code == 502 and "LLM_API_KEY" in result.json()["detail"]
    found = client.get("/api/contacts/lookup",
                       params={"url": "https://www.linkedin.com/in/mira-example"}).json()
    assert found["brief"] is None


@pytest.mark.parametrize("url", [
    "http://127.0.0.1/", "http://localhost:8000/", "http://10.0.0.5/", "http://169.254.169.254/",
    "ftp://example.com/", "https://user:pw@example.com/", "https://example.com:8443/",
    "https://www.linkedin.com/company/x", "http://[::1]/",
])
def test_company_url_must_be_public_web(url):
    with pytest.raises(ValueError):
        briefs.public_url(url)


def test_visible_text_skips_scripts_and_keeps_meta_description():
    html = ('<html><head><title>Synthetic Pay</title><meta name="description" content="Recon '
            'APIs"><script>var secret=1</script><style>p{}</style></head><body><p>Hello'
            '&amp; welcome</p><noscript>enable js</noscript></body></html>')
    text = briefs.page_text(html)
    assert "Recon APIs" in text and "Hello& welcome" in text and "Synthetic Pay" in text
    assert "secret" not in text and "enable js" not in text and "p{}" not in text
