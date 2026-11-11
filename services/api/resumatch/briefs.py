"""Cross-workflow contact lookup and website-grounded talking points for handwritten notes.

A brief is research and drafting help only: it is never activity, never sent, and never counts.
"""

import base64
import binascii
import hashlib
import io
import ipaddress
import socket
from datetime import UTC, datetime
from html.parser import HTMLParser
from urllib.parse import urljoin, urlsplit

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import Field
from pypdf import PdfReader
from pypdf.errors import PyPdfError
from sqlalchemy import select

from resumatch.ai_runs import ai_run
from resumatch.auth import DB, BrowserOwner, Owner, require_origin
from resumatch.duplicates import profile_identity
from resumatch.intelligence import provider_json
from resumatch.models import Capture, ContactBrief, OutreachSession, User, Workflow
from resumatch.schemas import Input
from resumatch.workflow_contracts import comparable
from resumatch.workflows import definition_for, raw_capture_text

router = APIRouter(prefix="/api")
writes = [Depends(require_origin)]
MAX_PAGE_BYTES = 600_000
MAX_PAGE_CHARS = 12_000
MAX_RESUME_CHARS = 30_000
MAX_RESUME_BYTES = 4_000_000
MAX_RESUME_PAGES = 12


class AboutMe(Input):
    about_me: str = Field(max_length=3000)
    # None keeps the saved resume; "" clears it.
    resume_text: str | None = Field(default=None, max_length=MAX_RESUME_CHARS)


class ResumeFile(Input):
    filename: str = Field(min_length=1, max_length=200)
    content_base64: str = Field(min_length=1, max_length=MAX_RESUME_BYTES * 4 // 3 + 8)


class BriefRequest(Input):
    url: str = Field(min_length=1, max_length=2000)
    company_url: str | None = Field(default=None, max_length=2000)
    # None keeps the saved context for this contact; "" clears it.
    context: str | None = Field(default=None, max_length=2000)


def resume_hash(text):
    return hashlib.sha256(text.encode()).hexdigest()


def profile_view(user):
    persona = user.persona
    stale = bool(persona) and persona.get("resume_sha256") != resume_hash(user.resume_text)
    return {"about_me": user.about_me, "resume_text": user.resume_text,
            "persona": persona and {**persona, "stale": stale}}


def has_background(user):
    return bool(user.about_me.strip() or user.resume_text.strip())


@router.get("/profile")
def get_profile(user: Owner):
    return profile_view(user)


@router.put("/profile", dependencies=writes)
def put_profile(body: AboutMe, user: Owner, db: DB):
    row = db.get(User, user.id)
    row.about_me = body.about_me.strip()
    if body.resume_text is not None:
        row.resume_text = body.resume_text.strip()
    db.commit()
    return profile_view(row)


def resume_file_text(name, data):
    """Text from an uploaded PDF or plain-text resume. Returned for review, not saved."""
    if data.startswith(b"%PDF"):
        try:
            reader = PdfReader(io.BytesIO(data))
            if reader.is_encrypted:
                raise ValueError("This PDF is password-protected; paste the text instead")
            text = "\n".join(p.extract_text() or "" for p in reader.pages[:MAX_RESUME_PAGES])
        except (PyPdfError, ValueError, KeyError, TypeError, IndexError) as error:
            if "password" in str(error):
                raise
            raise ValueError("Could not read this PDF; paste the resume text instead") from None
    elif name.lower().endswith((".txt", ".md")):
        text = data.decode("utf-8", errors="replace")
    else:
        raise ValueError("Upload a PDF, .txt or .md resume, or paste the text")
    text = "\n".join(" ".join(line.split()) for line in text.splitlines()).strip()
    if not text:
        raise ValueError("No text found in this file (scanned image?); paste the text instead")
    return text[:MAX_RESUME_CHARS]


@router.post("/profile/resume-file", dependencies=writes)
def read_resume_file(body: ResumeFile, user: Owner):
    try:
        data = base64.b64decode(body.content_base64, validate=True)
    except (binascii.Error, ValueError):
        raise HTTPException(422, "File upload was not readable") from None
    if len(data) > MAX_RESUME_BYTES:
        raise HTTPException(422, "Resume file is larger than 4 MB")
    try:
        return {"resume_text": resume_file_text(body.filename, data)}
    except ValueError as error:
        raise HTTPException(422, str(error)) from None


PERSONA_SCHEMA = {
    "type": "object", "additionalProperties": False,
    "required": ["headline", "summary", "domains", "strengths", "proof_points"],
    "properties": {
        "headline": {"type": "string"}, "summary": {"type": "string"},
        "domains": {"type": "array", "maxItems": 6, "items": {"type": "string"}},
        **{key: {"type": "array", "maxItems": 6, "items": {
            "type": "object", "additionalProperties": False, "required": ["point", "evidence"],
            "properties": {"point": {"type": "string"}, "evidence": {"type": "string"}},
        }} for key in ("strengths", "proof_points")},
    },
}

PERSONA_PROMPT = (
    "Build the sender's professional persona from resume_text and about_me (their own words). "
    "It is used to pick ONE matching credential for short outreach notes, so be concrete and "
    "plain: no buzzwords, no adjectives the resume does not support.\n"
    "headline: under 12 words, role + domain. summary: 1-2 plain sentences. domains: industries "
    "or technical areas they have actually worked in. strengths: what they are good at. "
    "proof_points: concrete things they did (shipped products, customers, scale, metrics), each "
    "a 3-14 word fragment usable in a note. Every strength and proof_point needs evidence copied "
    "VERBATIM from resume_text. Never invent, round or upgrade numbers, titles or employers."
)


def ground_points(items, source):
    kept, dropped = [], []
    for item in items if isinstance(items, list) else []:
        evidence = item.get("evidence") if isinstance(item, dict) else None
        point = item.get("point") if isinstance(item, dict) else None
        if (isinstance(point, str) and point.strip() and isinstance(evidence, str)
                and comparable(evidence) and len(evidence) <= 400
                and comparable(evidence) in source):
            kept.append({"point": point.strip()[:200], "evidence": evidence.strip()})
        else:
            dropped.append(item)
    return kept, dropped


def clipped(value, limit):
    return value.strip()[:limit] if isinstance(value, str) else ""


def ground_persona(output, resume_text):
    if not isinstance(output, dict) or set(output) != set(PERSONA_SCHEMA["required"]):
        raise ValueError("AI persona did not match the expected format")
    source = comparable(resume_text)
    strengths, dropped_s = ground_points(output["strengths"], source)
    proof, dropped_p = ground_points(output["proof_points"], source)
    if not strengths and not proof:
        raise ValueError("no persona point could be matched to your resume text")
    domains = output["domains"] if isinstance(output["domains"], list) else []
    return {"headline": clipped(output["headline"], 160),
            "summary": clipped(output["summary"], 500),
            "domains": [d.strip()[:60] for d in domains if isinstance(d, str) and d.strip()][:6],
            "strengths": strengths, "proof_points": proof, "dropped": dropped_s + dropped_p}


@router.post("/profile/persona", dependencies=writes)
def build_persona(user: Owner, db: DB):
    resume = user.resume_text.strip()
    if not resume:
        raise HTTPException(422, "Paste or upload your resume and save it first")
    about_me = user.about_me.strip()
    db.rollback()  # No transaction held across the provider call.
    from resumatch.config import get_settings

    with ai_run(user.id, "persona", resume_hash(resume)[:16]) as run:
        try:
            persona = ground_persona(
                provider_json(PERSONA_SCHEMA, PERSONA_PROMPT,
                              {"resume_text": resume, "about_me": about_me}), resume)
        except ValueError as error:
            run.reject(str(error))
            raise HTTPException(502, f"AI persona unavailable: {error}") from None
        run.rejected, persona["dropped"] = persona["dropped"], len(persona["dropped"])
        run.result = persona
        row = db.get(User, user.id)
        row.persona = {**persona, "resume_sha256": resume_hash(resume),
                       "generated_at": datetime.now(UTC).isoformat(),
                       "model": get_settings().llm_model, "ai_run_id": str(run.id)}
        db.commit()
    return profile_view(row)


def brief_view(row):
    if row is None:
        return None
    return {"company_url": row.company_url, "context": row.context, "research": row.research,
            "brief": row.brief, "updated_at": row.updated_at}


def contact_lookup(db, user, url):
    key = profile_identity(url)
    if key is None:
        raise HTTPException(422, "Open a LinkedIn /in/ or X profile to check this contact")
    rows = db.execute(
        select(Capture, OutreachSession, Workflow)
        .join(OutreachSession, Capture.session_id == OutreachSession.id)
        .join(Workflow, OutreachSession.workflow_id == Workflow.id)
        .where(OutreachSession.user_id == user.id, Capture.decision != "discarded")
        .order_by(Capture.created_at.desc()).limit(5000)
    ).all()
    labels, records = {}, []
    for c, run, workflow in rows:
        if profile_identity(c.details["source_url"]) != key:
            continue
        if run.id not in labels:
            labels[run.id] = {f["key"]: f["label"] for f in definition_for(db, run)["fields"]}
        records.append({
            "capture_id": c.id, "workflow_id": workflow.id, "workflow_name": workflow.name,
            "run_id": run.id, "run_name": run.run_name, "decision": c.decision,
            "action": c.details["action"], "person": c.details["person"],
            "company": c.details["company"], "source_url": c.details["source_url"],
            "captured_at": c.created_at, "raw_text": raw_capture_text(c.details)[:2000],
            "fields": [{"label": labels[run.id].get(k, k), "value": v}
                       for k, v in c.details.get("fields", {}).items() if v not in (None, "")],
        })
    # Reviewed facts win over pending ones when both exist.
    ordered = sorted(records, key=lambda r: r["decision"] != "approved")
    contact = {"person": next((r["person"] for r in ordered if r["person"]), ""),
               "company": next((r["company"] for r in ordered if r["company"]), ""),
               "fields": []}
    seen = set()
    for r in ordered:
        for f in r["fields"]:
            if f["label"] not in seen:
                seen.add(f["label"])
                contact["fields"].append(f)
    brief = db.scalar(select(ContactBrief).where(
        ContactBrief.user_id == user.id, ContactBrief.contact_key == key))
    return {"contact_key": key, "found": bool(records), "contact": contact, "records": records,
            "brief": brief_view(brief), "about_me_set": has_background(user)}


@router.get("/contacts/lookup")
def lookup(user: Owner, db: DB, url: str = Query(min_length=1, max_length=2000)):
    return contact_lookup(db, user, url)


@router.get("/extension/contacts/lookup")
def browser_lookup(user: BrowserOwner, db: DB, url: str = Query(min_length=1, max_length=2000)):
    return contact_lookup(db, user, url)


def public_url(url):
    """Reject anything but a public http(s) site, so the server can't be pointed inward."""
    parts = urlsplit(url)
    host = (parts.hostname or "").lower()
    try:
        port = parts.port
    except ValueError:
        port = -1
    if (parts.scheme not in {"http", "https"} or not host or parts.username or parts.password
            or port not in {None, 80, 443}):
        raise ValueError("Use a public http(s) company website address")
    if host == "linkedin.com" or host.endswith(".linkedin.com"):
        raise ValueError("LinkedIn pages are not fetched; use the company's own website")
    try:
        infos = socket.getaddrinfo(host, port or (443 if parts.scheme == "https" else 80),
                                   type=socket.SOCK_STREAM)
    except (socket.gaierror, UnicodeError):
        raise ValueError("Company website could not be found") from None
    if not infos or any(not ipaddress.ip_address(i[4][0]).is_global for i in infos):
        raise ValueError("Company website must be a public internet address")


class VisibleText(HTMLParser):
    SKIP = {"script", "style", "noscript", "svg", "template"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.depth, self.parts = 0, []

    def handle_starttag(self, tag, attrs):
        if tag == "meta":
            a = dict(attrs)
            if (a.get("name") or a.get("property") or "").lower() in {
                "description", "og:description"
            } and a.get("content"):
                self.parts.append(a["content"].strip())
        elif tag in self.SKIP:
            self.depth += 1

    def handle_endtag(self, tag):
        if tag in self.SKIP and self.depth:
            self.depth -= 1

    def handle_data(self, data):
        if not self.depth and data.strip():
            self.parts.append(" ".join(data.split()))


def page_text(html):
    parser = VisibleText()
    parser.feed(html)
    return "\n".join(dict.fromkeys(parser.parts))[:MAX_PAGE_CHARS]


def fetch_page(client, url):
    for _ in range(4):
        public_url(url)
        with client.stream("GET", url, headers={"Accept": "text/html,text/plain"}) as response:
            if response.is_redirect:
                url = urljoin(url, response.headers.get("location", ""))
                continue
            if response.status_code >= 400:
                raise ValueError(f"Company website returned HTTP {response.status_code}")
            kind = response.headers.get("content-type", "")
            if "html" not in kind and "text/plain" not in kind:
                raise ValueError("Company website address is not a web page")
            body = bytearray()
            for chunk in response.iter_bytes():
                body.extend(chunk)
                if len(body) > MAX_PAGE_BYTES:
                    break
            return url, page_text(body.decode(response.encoding or "utf-8", errors="replace"))
    raise ValueError("Company website redirected too many times")


def fetch_company(url):
    """Homepage plus /about when it exists. Explicit, user-requested, two requests at most."""
    pages = []
    try:
        with httpx.Client(timeout=httpx.Timeout(8, connect=4), follow_redirects=False,
                          headers={"User-Agent": "outreach-brief/0.1 (personal research)"}) as c:
            final, text = fetch_page(c, url)
            pages.append({"url": final, "text": text})
            about = urljoin(final, "/about")
            if about.rstrip("/") != final.rstrip("/"):
                try:
                    pages.append(dict(zip(("url", "text"), fetch_page(c, about), strict=True)))
                except (ValueError, httpx.HTTPError):
                    pass  # No about page is normal; the homepage is enough.
    except httpx.HTTPError:
        raise ValueError("Company website unreachable or timed out") from None
    if not any(p["text"] for p in pages):
        raise ValueError("Company website had no readable text")
    return pages


BRIEF_SCHEMA = {
    "type": "object", "additionalProperties": False,
    "required": ["company_facts", "hooks", "credentials", "bridges", "asks", "avoid",
                 "reference_draft"],
    "properties": {
        "company_facts": {"type": "array", "maxItems": 5, "items": {
            "type": "object", "additionalProperties": False, "required": ["fact", "source_quote"],
            "properties": {"fact": {"type": "string"}, "source_quote": {"type": "string"}},
        }},
        **{key: {"type": "array", "maxItems": 4, "items": {"type": "string"}}
           for key in ("hooks", "credentials", "bridges", "asks", "avoid")},
        "reference_draft": {"type": "string"},
    },
}

# Distilled from notes the user wrote by hand that got accepted/replied to. No third-party names.
BRIEF_PROMPT = (
    "You prepare talking points for a short LinkedIn note the sender will HANDWRITE. People spot "
    "AI-written notes by polish, so give raw material, not prose. Write every bullet as a terse "
    "fragment of 3-14 plain words, the way someone jots notes: no em dashes, no semicolons, no "
    "buzzwords (passionate, synergy, leverage, thrilled, innovative, game-changing), no stacked "
    "compliments.\n"
    "Notes that worked follow this shape: casual first-name opener ('Hey <first name>,'), ONE "
    "specific hook naming what the person or company builds (product name, vision or the problem "
    "it solves), ONE credential from the sender's background picked because it matches that "
    "domain, a bridge saying why the sender's experience relates to their problem, then a soft "
    "low-pressure ask (just saying hi, expand network, explore collaborating, a short chat). Two "
    "to five sentences total. Short and specific beats long and generic.\n"
    "outreach_context is the sender's own notes on this person: something they found, shared "
    "ground, and their goal for the note. Treat it as true, prefer it for the hook, aim the ask "
    "at the stated goal, and allow ONE genuine, specific compliment drawn from it or the website "
    "(never generic flattery). Never present it as something the person said.\n"
    "Facts: use ONLY contact_records, website_text, outreach_context and sender_background "
    "(about_me, persona proof points, resume excerpt). Never invent metrics, "
    "funding, customers, mutual history, hiring, or that a message/request was sent. If "
    "website_text is empty, hook on the person's role/headline/company from contact_records.\n"
    "company_facts: up to 5 short facts about what the company does or builds, each with a "
    "source_quote copied VERBATIM from website_text (empty list if no website_text).\n"
    "hooks: 2-3 options, each naming something specific. credentials: 1-3 facts taken from "
    "sender_background, most relevant first. bridges: 1-2. asks: 2 soft options. avoid: 1-3 "
    "things that would make a note to THIS person feel templated or salesy.\n"
    "reference_draft: one example under 70 words in the sender's casual voice, opening "
    "'Hey <first name>,' and signing off like sender_background suggests. It is only a reference; "
    "the sender rewrites it by hand."
)


def ground_brief(output, website_text):
    if not isinstance(output, dict) or set(output) != set(BRIEF_SCHEMA["required"]):
        raise ValueError("AI brief did not match the expected format")
    text, facts, dropped = comparable(website_text), [], []
    for fact in output["company_facts"] if isinstance(output["company_facts"], list) else []:
        quote = fact.get("source_quote") if isinstance(fact, dict) else None
        if (isinstance(quote, str) and isinstance(fact.get("fact"), str) and fact["fact"].strip()
                and comparable(quote) and len(quote) <= 400 and comparable(quote) in text):
            facts.append({"fact": fact["fact"].strip()[:300], "source_quote": quote})
        else:
            dropped.append(fact)
    brief = {}
    for key in ("hooks", "credentials", "bridges", "asks", "avoid"):
        items = output[key] if isinstance(output[key], list) else []
        brief[key] = [i.strip()[:200] for i in items if isinstance(i, str) and i.strip()][:4]
    draft = output["reference_draft"]
    brief["reference_draft"] = draft.strip()[:900] if isinstance(draft, str) else ""
    return facts, dropped, brief


def generate_brief(db, user, body):
    found = contact_lookup(db, user, body.url)
    if not found["found"]:
        raise HTTPException(404, "No saved record for this profile yet. Capture it first.")
    if not has_background(user):
        raise HTTPException(422, "Add your resume or background under About you in the app "
                                 "first; credentials are only taken from it")
    persona = user.persona or {}
    background = {
        "about_me": user.about_me.strip(),
        "persona": {k: persona.get(k) for k in ("headline", "summary", "domains")} | {
            k: [p["point"] for p in persona.get(k, [])] for k in ("strengths", "proof_points")},
        "resume_excerpt": user.resume_text.strip()[:6000],
    }
    saved = found["brief"] or {}
    company_url = (body.company_url or "").strip() or saved.get("company_url")
    context = (body.context if body.context is not None else saved.get("context", "")).strip()
    db.rollback()  # Release locks/transactions before slow network calls.
    from resumatch.config import get_settings

    with ai_run(user.id, "brief", found["contact_key"], company_url=company_url,
                has_context=bool(context)) as run:
        pages = []
        if company_url:
            try:
                pages = fetch_company(company_url)
            except ValueError as error:
                run.status, run.error = "fetch_error", str(error)
                run.research = {"company_url": company_url, "pages": [], "error": str(error)}
                raise HTTPException(422, str(error)) from None
            run.research = {"company_url": company_url, "pages": [
                {"url": p["url"], "chars": len(p["text"])} for p in pages]}
        website_text = "\n\n".join(p["text"] for p in pages)
        data = {
            "contact_records": {**found["contact"], "records": [
                {"workflow": r["workflow_name"], "action": r["action"], "raw_text": r["raw_text"]}
                for r in found["records"][:3]
            ]},
            "website_text": website_text, "outreach_context": context,
            "sender_background": background,
        }
        try:
            output = provider_json(BRIEF_SCHEMA, BRIEF_PROMPT, data)
            facts, dropped, brief = ground_brief(output, website_text)
        except ValueError as error:
            run.reject(str(error))
            raise HTTPException(502, f"AI brief unavailable: {error}") from None
        run.result, run.rejected = {"facts": facts, "brief": brief}, dropped
        research = {"pages": [p["url"] for p in pages], "facts": facts,
                    "dropped_facts": len(dropped),
                    "fetched_at": datetime.now(UTC).isoformat() if pages else None,
                    "model": get_settings().llm_model, "ai_run_id": str(run.id)}
        row = db.scalar(select(ContactBrief).where(
            ContactBrief.user_id == user.id, ContactBrief.contact_key == found["contact_key"]
        ).with_for_update())
        if row is None:
            row = ContactBrief(user_id=user.id, contact_key=found["contact_key"])
            db.add(row)
        row.company_url, row.research, row.brief = company_url, research, brief
        row.context = context
        row.updated_at = datetime.now(UTC)
        db.commit()
    return {**contact_lookup(db, user, body.url), "brief": brief_view(row)}


@router.post("/contacts/brief", dependencies=writes)
def brief(body: BriefRequest, user: Owner, db: DB):
    return generate_brief(db, user, body)


@router.post("/extension/contacts/brief")
def browser_brief(body: BriefRequest, user: BrowserOwner, db: DB):
    return generate_brief(db, user, body)
