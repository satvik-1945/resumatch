import base64

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
        "url": url, "company_url": "https://synthetic-pay.example",
        "context": "Posted about hiring a founding engineer. Goal: intro chat."}).json()
    research = result["brief"]["research"]
    assert [f["fact"] for f in research["facts"]] == ["Reconciliation APIs for card issuers"]
    assert research["dropped_facts"] == 1
    assert result["brief"]["brief"]["hooks"] == ["your reconciliation APIs for card issuers"]
    assert seen["sender_background"]["about_me"].startswith("FDE")
    assert seen["website_text"] == SITE and seen["outreach_context"].startswith("Posted")
    assert seen["contact_records"]["company"] == "Synthetic Pay"
    # Regenerating without a URL reuses the saved company site; the brief stays one row.
    again = client.post("/api/contacts/brief", json={"url": url}).json()
    assert again["brief"]["company_url"] == "https://synthetic-pay.example"
    assert again["brief"]["context"].endswith("Goal: intro chat.")
    assert seen["outreach_context"].endswith("Goal: intro chat.")
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


RESUME = ("Satvik Example\nForward Deployed Engineer, Synthetic Fintech (2023-2025)\n"
          "- Built 2 products from scratch\n- Onboarded 12 enterprise customers\n"
          "Skills: Python, TypeScript, payments reconciliation")


def persona_output():
    return {
        "headline": "Forward deployed engineer in fintech", "summary": "Builds and ships.",
        "domains": ["fintech", "payments"],
        "strengths": [{"point": "Payments reconciliation", "evidence": "payments reconciliation"}],
        "proof_points": [
            {"point": "Built 2 products from scratch",
             "evidence": "Built 2 products  from scratch"},
            {"point": "Onboarded 50 customers", "evidence": "Onboarded 50 enterprise customers"},
            {"point": "Onboarded 12 enterprise customers",
             "evidence": "Onboarded 12 enterprise customers"},
        ],
    }


def test_resume_persona_is_grounded_and_marked_stale_when_resume_changes(client, monkeypatch):
    register(client)
    assert client.post("/api/profile/persona").status_code == 422  # no resume yet
    saved = client.put("/api/profile", json={"about_me": "cheers, Satvik",
                                              "resume_text": RESUME}).json()
    assert saved["resume_text"] == RESUME and saved["persona"] is None
    failed = client.post("/api/profile/persona")
    assert failed.status_code == 502 and "LLM_API_KEY" in failed.json()["detail"]
    seen = {}
    monkeypatch.setattr(briefs, "provider_json",
                        lambda schema, prompt, data: seen.update(data) or persona_output())
    persona = client.post("/api/profile/persona").json()["persona"]
    assert seen["resume_text"] == RESUME and seen["about_me"] == "cheers, Satvik"
    assert [p["point"] for p in persona["proof_points"]] == [
        "Built 2 products from scratch", "Onboarded 12 enterprise customers"]
    assert persona["dropped"] == 1 and persona["stale"] is False
    assert persona["domains"] == ["fintech", "payments"]
    # About-only edits keep the resume; a resume edit marks the persona stale.
    kept = client.put("/api/profile", json={"about_me": "cheers"}).json()
    assert kept["resume_text"] == RESUME and kept["persona"]["stale"] is False
    edited = client.put("/api/profile", json={"about_me": "cheers",
                                               "resume_text": RESUME + "\nRust"}).json()
    assert edited["persona"]["stale"] is True
    assert client.post("/api/profile/persona",
                       headers={"origin": "https://evil.example"}).status_code == 403


def test_persona_with_no_quotable_point_is_rejected(client, monkeypatch):
    register(client)
    client.put("/api/profile", json={"about_me": "", "resume_text": RESUME})
    monkeypatch.setattr(briefs, "provider_json", lambda *_: {
        "headline": "h", "summary": "s", "domains": [],
        "strengths": [{"point": "Leadership", "evidence": "Led a team of 40"}],
        "proof_points": []})
    assert client.post("/api/profile/persona").status_code == 502
    assert client.get("/api/profile").json()["persona"] is None


def test_brief_uses_resume_persona_without_about_me(client, monkeypatch):
    register(client)
    founder_record(client)
    client.put("/api/profile", json={"about_me": "", "resume_text": RESUME})
    monkeypatch.setattr(briefs, "provider_json", lambda *_: persona_output())
    client.post("/api/profile/persona")
    seen = {}

    def provider(schema, prompt, data):
        seen.update(data)
        return {"company_facts": [], "hooks": ["h"], "credentials": ["c"], "bridges": [],
                "asks": ["a"], "avoid": [], "reference_draft": "Hey Mira,"}

    monkeypatch.setattr(briefs, "provider_json", provider)
    url = "https://www.linkedin.com/in/mira-example"
    assert client.get("/api/contacts/lookup", params={"url": url}).json()["about_me_set"] is True
    assert client.post("/api/contacts/brief", json={"url": url}).status_code == 200
    background = seen["sender_background"]
    assert background["persona"]["proof_points"][0] == "Built 2 products from scratch"
    assert background["resume_excerpt"] == RESUME and seen["outreach_context"] == ""


def minimal_pdf(text):
    stream = f"BT /F1 12 Tf 72 720 Td ({text}) Tj ET".encode()
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R "
        b"/Resources << /Font << /F1 5 0 R >> >> >>",
        b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    out, offsets = bytearray(b"%PDF-1.4\n"), []
    for i, body in enumerate(objects, 1):
        offsets.append(len(out))
        out += b"%d 0 obj\n" % i + body + b"\nendobj\n"
    xref = len(out)
    out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objects) + 1)
    out += b"".join(b"%010d 00000 n \n" % o for o in offsets)
    out += b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF" % (
        len(objects) + 1, xref)
    return bytes(out)


def upload(client, name, data):
    return client.post("/api/profile/resume-file", json={
        "filename": name, "content_base64": base64.b64encode(data).decode()})


def test_resume_file_upload_extracts_text_without_saving(client):
    register(client)
    pdf = upload(client, "resume.pdf", minimal_pdf("Built 2 products from scratch"))
    assert pdf.status_code == 200 and "Built 2 products from scratch" in pdf.json()["resume_text"]
    assert client.get("/api/profile").json()["resume_text"] == ""
    text = upload(client, "resume.md", b"  Python   engineer \n\nFintech")
    assert text.json()["resume_text"] == "Python engineer\n\nFintech"
    assert upload(client, "resume.docx", b"PK\x03\x04").status_code == 422
    assert upload(client, "resume.pdf", b"%PDF-1.4 garbage").status_code == 422
    bad = client.post("/api/profile/resume-file",
                      json={"filename": "r.pdf", "content_base64": "%%%"})
    assert bad.status_code == 422
