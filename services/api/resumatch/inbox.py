"""Read-only Gmail connection and the user-triggered inbox scan for job applications.

A scan runs only when the user clicks Scan inbox. Gmail's own search narrows the window to
likely job mail; for those messages only sender, subject and Gmail's short snippet are read.
Bodies and attachments are never downloaded. LinkedIn's "application was sent to X" mail is
settled by a local rule; only the remaining candidates go to the AI. Results land as pending
records in an inbox-review run of the Job applications workflow; nothing counts until approved.
"""

import base64
import hashlib
import html
import re
import secrets
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from email.utils import parseaddr, parsedate_to_datetime
from urllib.parse import urlencode
from uuid import UUID

import httpx
from cryptography.fernet import Fernet, InvalidToken
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from sqlalchemy import delete, func, select

from resumatch.ai_runs import ai_run
from resumatch.auth import DB, Owner, require_origin
from resumatch.config import get_settings
from resumatch.duplicates import normalized_name
from resumatch.intelligence import provider_json
from resumatch.models import (
    Capture,
    EmailAccount,
    EmailMessage,
    OauthState,
    OutreachSession,
    Workflow,
)
from resumatch.run_names import next_run_name
from resumatch.workflow_contracts import WorkflowWrite, comparable, template
from resumatch.workflows import create_workflow, validate_fields

router = APIRouter(prefix="/api")
writes = [Depends(require_origin)]

SCOPE = "https://www.googleapis.com/auth/gmail.readonly"
AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
REVOKE_URL = "https://oauth2.googleapis.com/revoke"
GMAIL = "https://gmail.googleapis.com/gmail/v1/users/me"
STATE_TTL = timedelta(minutes=10)
FIRST_SCAN = timedelta(days=5)
OVERLAP = timedelta(days=1)
LIST_LIMIT = 2000  # ids only: cheap to list
MAX_NEW = 300  # new messages read per scan; the rest wait for the next scan
RUN_LIMIT = 500  # records in one inbox review run (bulk approve takes up to 500)
AI_BATCH = 25
FETCH_WORKERS = 10
AI_WORKERS = 4
# Gmail-side prefilter: only subjects that can plausibly be about an application are listed.
QUERY = ('subject:(application OR applying OR applied OR interview OR candidacy OR assessment '
         'OR "next steps" OR "your interest" OR shortlisted OR recruiter OR offer OR position)')
LINKEDIN_SENT = re.compile(r"your application was sent to (?P<company>.+?)\s*$", re.I)
# A view is a signal about an application, not a company writing back.
LINKEDIN_VIEWED = re.compile(r"your application was viewed by (?P<company>.+?)\s*$", re.I)


def configured():
    s = get_settings()
    return bool(s.google_client_id and s.google_client_secret
                and s.google_client_secret.get_secret_value()
                and s.email_token_key and s.email_token_key.get_secret_value())


def require_configured():
    if not configured():
        raise HTTPException(503, "Gmail connection needs GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET "
                                 "and EMAIL_TOKEN_KEY in .env; see the setup guide")


def fernet():
    return Fernet(get_settings().email_token_key.get_secret_value().encode())


def redirect_uri():
    return get_settings().web_origin + "/api/email/oauth/callback"


_client = None


def http():
    # One pooled client: a scan makes hundreds of Gmail calls, mostly in parallel.
    global _client
    if _client is None:
        _client = httpx.Client(timeout=httpx.Timeout(15, connect=5), follow_redirects=False,
                               limits=httpx.Limits(max_connections=FETCH_WORKERS + 4))
    return _client


def google(method, url, *, token=None, data=None, params=None):
    """The only network call in this module, so tests replace exactly this."""
    headers = {"Authorization": "Bearer " + token} if token else {}
    try:
        response = http().request(method, url, headers=headers, data=data, params=params)
    except httpx.HTTPError:
        raise ValueError("Google is unreachable; try the scan again") from None
    try:
        body = response.json()
    except ValueError:
        body = {}
    return response.status_code, body


# ---- Connecting accounts -------------------------------------------------------------------

@router.post("/email/connect", dependencies=writes)
def connect(user: Owner, db: DB):
    require_configured()
    db.execute(delete(OauthState).where(OauthState.created_at < datetime.now(UTC) - STATE_TTL))
    state, verifier = secrets.token_urlsafe(32), secrets.token_urlsafe(64)
    db.add(OauthState(state=state, user_id=user.id, code_verifier=verifier))
    db.commit()
    challenge = base64.urlsafe_b64encode(
        hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    return {"url": AUTH_URL + "?" + urlencode({
        "client_id": get_settings().google_client_id, "redirect_uri": redirect_uri(),
        "response_type": "code", "scope": SCOPE, "access_type": "offline",
        "prompt": "consent select_account", "state": state,
        "code_challenge": challenge, "code_challenge_method": "S256",
    })}


def back_to_app(result):
    return RedirectResponse(get_settings().web_origin + "/?" + urlencode(
        {"view": "applications", "email": result}), status_code=303)


@router.get("/email/oauth/callback")
def oauth_callback(user: Owner, db: DB, state: str = Query(max_length=100),
                   code: str | None = Query(None, max_length=2000),
                   error: str | None = Query(None, max_length=200)):
    require_configured()
    pending = db.get(OauthState, state)
    if pending is None or pending.user_id != user.id:
        return back_to_app("expired")
    fresh = pending.created_at > datetime.now(UTC) - STATE_TTL
    verifier = pending.code_verifier
    db.delete(pending)
    db.commit()
    if not fresh:
        return back_to_app("expired")
    if error or not code:
        return back_to_app("denied")
    s = get_settings()
    try:
        status, token = google("POST", TOKEN_URL, data={
            "code": code, "client_id": s.google_client_id,
            "client_secret": s.google_client_secret.get_secret_value(),
            "redirect_uri": redirect_uri(), "grant_type": "authorization_code",
            "code_verifier": verifier})
        if status != 200 or not token.get("refresh_token"):
            return back_to_app("error")
        if SCOPE not in token.get("scope", "").split():
            return back_to_app("scope")
        status, profile = google("GET", GMAIL + "/profile", token=token["access_token"])
    except ValueError:
        return back_to_app("error")
    address = str(profile.get("emailAddress", "")).strip().lower()
    if status != 200 or "@" not in address or len(address) > 320:
        return back_to_app("error")
    account = db.scalar(select(EmailAccount).where(
        EmailAccount.user_id == user.id, EmailAccount.email == address))
    if account is None:
        account = EmailAccount(user_id=user.id, email=address)
        db.add(account)
    account.refresh_token = fernet().encrypt(token["refresh_token"].encode()).decode()
    account.last_error = None
    db.commit()
    return back_to_app("connected")


def owned_account(db, user, account_id):
    account = db.get(EmailAccount, account_id)
    if account is None or account.user_id != user.id:
        raise HTTPException(404, "Email account not found")
    return account


@router.delete("/email/accounts/{account_id}", status_code=204, dependencies=writes)
def disconnect(account_id: UUID, user: Owner, db: DB):
    account = owned_account(db, user, account_id)
    try:
        google("POST", REVOKE_URL, data={"token": fernet().decrypt(
            account.refresh_token.encode()).decode()})
    except (ValueError, InvalidToken):
        pass  # Already revoked or unreachable; deleting our copy is what matters.
    db.delete(account)  # Records already created from it stay in your history.
    db.commit()


# ---- Classification ------------------------------------------------------------------------

TRIAGE_SCHEMA = {
    "type": "object", "additionalProperties": False, "required": ["emails"],
    "properties": {"emails": {"type": "array", "items": {
        "type": "object", "additionalProperties": False,
        "required": ["id", "category", "company", "role", "applied_via", "needs_reply"],
        "properties": {
            "id": {"type": "string"},
            "category": {"type": "string", "enum": ["application", "response", "not_job"]},
            "company": {"type": "string"}, "role": {"type": "string"},
            "applied_via": {"type": "string"}, "needs_reply": {"type": "boolean"},
        },
    }}},
}

TRIAGE_PROMPT = (
    "Classify each email (sender, subject, short snippet) from the user's own inbox.\n"
    "application: confirms the user submitted a job application (\"thank you for applying\", "
    "\"we received your application\", \"your application was sent\").\n"
    "response: a company or recruiter writing back about the user's application or candidacy: "
    "interview invite, assessment, next steps, request to register, complete or reply, offer, "
    "rejection. A sender or subject that names an interview or asks the user to register or "
    "finish a job application is a response, even if it looks like a mass mailing: the user "
    "reviews every result, so prefer response over not_job when it is about their candidacy.\n"
    "not_job: everything else, including job alerts and recommendations (\"jobs for you\"), "
    "newsletters, salary tips, course or product marketing, platform announcements, and "
    "non-job applications (credit cards, loans, courses, bootcamps).\n"
    "company and role: only if named in the sender, subject or snippet, copied as written; "
    "otherwise \"\". Never use a platform (LinkedIn, Naukri, Indeed) as the company.\n"
    "applied_via: LinkedIn, Naukri, Indeed, company careers site, recruiter, or \"\".\n"
    "needs_reply: true only for a response that asks the user to do or answer something "
    "(schedule, register, complete, confirm, reply). Rejections are false.\n"
    "Return one entry per input id."
)


def grounded(value, source):
    value = value.strip() if isinstance(value, str) else ""
    return value[:200] if value and comparable(value) in source else ""


def triage(user_id, account, emails):
    """AI classification for messages the local rule could not settle. Ungrounded names drop."""
    with ai_run(user_id, "email_triage", account.email, count=len(emails)) as run:
        output = provider_json(TRIAGE_SCHEMA, TRIAGE_PROMPT, {"emails": [
            {"id": e["id"], "from": e["sender"], "subject": e["subject"],
             "snippet": e["snippet"]} for e in emails]})
        by_id = {e["id"]: e for e in emails}
        results, rejected = {}, []
        items = output.get("emails") if isinstance(output, dict) else None
        for item in items if isinstance(items, list) else []:
            if not isinstance(item, dict) or item.get("id") not in by_id:
                continue
            e = by_id[item["id"]]
            if item.get("category") not in {"application", "response", "not_job"}:
                rejected.append(item)
                continue
            source = comparable(" ".join((e["sender"], e["subject"], e["snippet"])))
            company = grounded(item.get("company"), source)
            role = grounded(item.get("role"), source)
            if item.get("company") and not company or item.get("role") and not role:
                rejected.append({"id": item["id"], "company": item.get("company"),
                                 "role": item.get("role")})
            results[item["id"]] = {
                "category": item["category"], "company": company, "role": role,
                "applied_via": (item.get("applied_via") or "")[:60]
                if isinstance(item.get("applied_via"), str) else "",
                "needs_reply": item.get("needs_reply") is True}
        run.result, run.rejected = {"classified": len(results)}, rejected
        if not results:
            run.reject("No email could be classified")
        return results


def local_rule(email):
    if "linkedin" not in email["sender"].lower():
        return None
    if match := LINKEDIN_SENT.search(email["subject"]):
        return {"category": "application", "company": match["company"].strip()[:200],
                "role": "", "applied_via": "LinkedIn", "needs_reply": False}
    if match := LINKEDIN_VIEWED.search(email["subject"]):
        return {"category": "viewed", "company": match["company"].strip()[:200]}
    return None


# ---- Scanning ------------------------------------------------------------------------------

def access_token(account):
    s = get_settings()
    try:
        refresh = fernet().decrypt(account.refresh_token.encode()).decode()
    except InvalidToken:
        raise ValueError("Stored Gmail access can't be read; reconnect this account") from None
    status, body = google("POST", TOKEN_URL, data={
        "client_id": s.google_client_id, "grant_type": "refresh_token",
        "client_secret": s.google_client_secret.get_secret_value(), "refresh_token": refresh})
    if status != 200 or "access_token" not in body:
        raise ValueError("Google access expired or was revoked; reconnect this account")
    return body["access_token"]


def fetch_candidates(account, token, since, seen):
    """New message ids in the window, newest first, and whether more remain for next scan."""
    ids, page = [], None
    while len(ids) < LIST_LIMIT:
        params = {"q": f"after:{int(since.timestamp())} {QUERY}", "maxResults": 100}
        if page:
            params["pageToken"] = page
        status, body = google("GET", GMAIL + "/messages", token=token, params=params)
        if status != 200:
            raise ValueError("Gmail search failed; try again or reconnect this account")
        ids += [m["id"] for m in body.get("messages", [])]
        page = body.get("nextPageToken")
        if not page:
            break
    new = [gid for gid in ids if gid not in seen]
    return new[:MAX_NEW], len(new) > MAX_NEW or bool(page)


def fetch_message(token, gmail_id):
    status, body = google("GET", f"{GMAIL}/messages/{gmail_id}", token=token, params={
        "format": "metadata", "metadataHeaders": ["From", "Subject", "Date"]})
    if status != 200:
        raise ValueError("Gmail message could not be read; try the scan again")
    headers = {h["name"].lower(): h["value"]
               for h in body.get("payload", {}).get("headers", [])}
    try:
        received = parsedate_to_datetime(headers.get("date", ""))
        received = received if received.tzinfo else received.replace(tzinfo=UTC)
    except (TypeError, ValueError):
        received = datetime.fromtimestamp(int(body.get("internalDate", 0)) / 1000, UTC)
    return {"id": gmail_id, "thread_id": body.get("threadId", gmail_id),
            "sender": headers.get("from", "")[:500], "subject": headers.get("subject", "")[:1000],
            "snippet": html.unescape(body.get("snippet", ""))[:500], "received_at": received}


def job_workflow(db, user):
    workflow = db.scalar(select(Workflow).where(
        Workflow.user_id == user.id, Workflow.kind == "job_applications"
    ).order_by(Workflow.created_at))
    return workflow or create_workflow(db, user.id, WorkflowWrite(**template("job_applications")))


def inbox_run(db, user, workflow):
    run = db.scalar(select(OutreachSession).where(
        OutreachSession.user_id == user.id, OutreachSession.source == "email",
        OutreachSession.state != "completed"))
    if run is None:
        at = datetime.now(UTC)
        run = OutreachSession(user_id=user.id, source="email", state="review",
                              intention="Inbox scan: applications and replies",
                              target_minutes=5, started_at=at, finished_at=at,
                              workflow_id=workflow.id, workflow_version=workflow.version,
                              run_name=next_run_name(db, workflow.id, at))
        db.add(run)
        db.flush()
    return run


def sender_name(sender):
    name, address = parseaddr(sender)
    name = name.strip().strip('"')
    platform = any(p in (name + address).lower() for p in (
        "linkedin", "naukri", "indeed", "noreply", "no-reply", "donotreply", "notification"))
    return "" if platform else name[:200]


def record_details(db, run, account, email, found):
    response = found["category"] == "response"
    details = {
        "source_url": f"https://mail.google.com/mail/u/{account.email}/#all/{email['id']}",
        "source_title": email["subject"][:500], "quote": "",
        "person": sender_name(email["sender"]) if response else "",
        "company": found["company"], "channel": "email",
        "action": "replied" if response else "applied",
        "notes": f"From: {email['sender']}\nSubject: {email['subject']}\n{email['snippet']}",
        "fields": {"role": found["role"] or None, "applied_via": found["applied_via"] or None,
                   "needs_reply": found["needs_reply"] if response else False},
        "occurred_at": email["received_at"].isoformat(),
        # A reply waiting on you shows up in Due follow-ups once approved.
        "followup_on": datetime.now(UTC).date().isoformat()
        if response and found["needs_reply"] else None,
    }
    return validate_fields(db, run, details)


def earlier_application(db, account, company):
    key = normalized_name(company)
    if not key:
        return None
    rows = db.execute(select(EmailMessage.company, EmailMessage.received_at).join(
        EmailAccount, EmailAccount.id == EmailMessage.account_id
    ).where(EmailAccount.user_id == account.user_id, EmailMessage.category == "application")
    ).all()
    return next((r for r in rows if normalized_name(r.company) == key), None)


def scan_account(db, user, account, run, summary):
    started = datetime.now(UTC)
    token = access_token(account)
    since = (account.last_scanned_at - OVERLAP if account.last_scanned_at
             else started - FIRST_SCAN)
    seen = set(db.scalars(select(EmailMessage.gmail_id).where(
        EmailMessage.account_id == account.id)))
    db.commit()  # No transaction held across Gmail and AI calls.
    ids, more = fetch_candidates(account, token, since, seen)
    with ThreadPoolExecutor(FETCH_WORKERS) as pool:
        emails = list(pool.map(lambda gid: fetch_message(token, gid), ids))
    summary["scanned"] += len(emails)
    decided = {e["id"]: local_rule(e) for e in emails}
    unsure = [e for e in emails if decided[e["id"]] is None]
    unresolved = 0
    if more:
        unresolved += 1  # Keep the window so the next scan reads the rest.
        summary["warnings"].append(f"{account.email}: read the newest {MAX_NEW} new emails; "
                                   "scan again to read the rest.")
    batches = [unsure[i:i + AI_BATCH] for i in range(0, len(unsure), AI_BATCH)]

    def classify(batch):
        try:
            return batch, triage(user.id, account, batch), None
        except ValueError as error:
            return batch, {}, error

    with ThreadPoolExecutor(AI_WORKERS) as pool:
        for batch, found, error in pool.map(classify, batches):
            decided.update(found)
            if error:
                # Left unrecorded so the next scan retries them; the window is not advanced.
                unresolved += len(batch)
                summary["warnings"].append(f"{account.email}: AI unavailable ({error}); "
                                           f"{len(batch)} emails will be retried next scan.")
    threads = dict(db.execute(select(EmailMessage.thread_id, EmailMessage.capture_id).where(
        EmailMessage.account_id == account.id, EmailMessage.capture_id.is_not(None))).all())
    for email in sorted(emails, key=lambda e: e["received_at"]):
        found = decided.get(email["id"])
        if found is None and email in unsure:
            continue
        category = (found or {}).get("category", "not_job")
        row = EmailMessage(account_id=account.id, gmail_id=email["id"],
                           thread_id=email["thread_id"], received_at=email["received_at"],
                           sender=email["sender"], subject=email["subject"],
                           category="ignored" if category in {"not_job", "viewed"}
                           else category, company=(found or {}).get("company", ""))
        db.add(row)
        if category in {"not_job", "viewed"}:
            summary["viewed" if category == "viewed" else "ignored"] += 1
            continue
        # Follow-ups in the same thread (LinkedIn's "2" bundles) are not a second application.
        if category == "application" and email["thread_id"] in threads:
            row.capture_id = threads[email["thread_id"]]
            summary["duplicates"] += 1
            continue
        if db.scalar(select(func.count()).select_from(Capture).where(
                Capture.session_id == run.id)) >= RUN_LIMIT:
            summary["warnings"].append(f"This review run is full ({RUN_LIMIT}); complete it, "
                                       "then scan again.")
            db.delete(row)
            unresolved += 1
            continue
        details = record_details(db, run, account, email, found)
        if category == "response" and (match := earlier_application(db, account,
                                                                    found["company"])):
            details["notes"] += (f"\nMatches your application to {match.company}"
                                 f" ({match.received_at:%Y-%m-%d}).")
        capture = Capture(session_id=run.id, source="email", details=details, original=details,
                          request_id=uuid.uuid5(uuid.NAMESPACE_URL,
                                                f"{account.id}:{email['id']}"))
        db.add(capture)
        db.flush()
        row.capture_id = capture.id
        threads[email["thread_id"]] = capture.id
        summary["applications" if category == "application" else "responses"] += 1
    if not unresolved:
        account.last_scanned_at = started
    account.last_error = None


@router.post("/email/scan", dependencies=writes)
def scan(user: Owner, db: DB):
    require_configured()
    accounts = db.scalars(select(EmailAccount).where(EmailAccount.user_id == user.id)
                          .order_by(EmailAccount.connected_at)).all()
    if not accounts:
        raise HTTPException(409, "Connect a Gmail account first")
    workflow = job_workflow(db, user)
    run = inbox_run(db, user, workflow)
    db.commit()
    summary = {"scanned": 0, "applications": 0, "responses": 0, "ignored": 0, "viewed": 0,
               "duplicates": 0, "warnings": []}
    for account in accounts:
        try:
            scan_account(db, user, account, run, summary)
            db.commit()
        except ValueError as error:
            db.rollback()
            account = db.get(EmailAccount, account.id)
            account.last_error = str(error)
            summary["warnings"].append(f"{account.email}: {error}")
            db.commit()
    return {**summary, "run_id": run.id, **email_overview(db, user)}


# ---- Overview ------------------------------------------------------------------------------

def email_overview(db, user):
    week_start = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    week_start -= timedelta(days=week_start.weekday())
    records = db.execute(select(Capture, OutreachSession.state).join(OutreachSession).join(
        Workflow, Workflow.id == OutreachSession.workflow_id
    ).where(OutreachSession.user_id == user.id, Workflow.kind == "job_applications",
            Capture.decision != "discarded")).all()
    applied = [c for c, _ in records if c.details["action"] == "applied"]
    replies = [c for c, _ in records if c.details["action"] == "replied"]
    open_run = db.scalar(select(OutreachSession).where(
        OutreachSession.user_id == user.id, OutreachSession.source == "email",
        OutreachSession.state != "completed"))
    accounts = db.scalars(select(EmailAccount).where(EmailAccount.user_id == user.id)
                          .order_by(EmailAccount.connected_at)).all()
    return {
        "configured": configured(),
        "accounts": [{"id": a.id, "email": a.email, "connected_at": a.connected_at,
                      "last_scanned_at": a.last_scanned_at, "last_error": a.last_error}
                     for a in accounts],
        "open_run_id": open_run.id if open_run else None,
        "counts": {
            "applied": sum(c.decision == "approved" for c in applied),
            "applied_this_week": sum(c.decision == "approved" and c.reviewed_at is not None
                                     and c.reviewed_at >= week_start for c in applied),
            "applied_to_review": sum(c.decision == "pending" for c in applied),
            "responses": sum(c.decision == "approved" for c in replies),
            "responses_to_review": sum(c.decision == "pending" for c in replies),
            "needs_reply": sum(bool(c.details["fields"].get("needs_reply"))
                               and not c.followup_done for c in replies),
        },
        "recent_responses": [{
            "id": c.id, "decision": c.decision, "person": c.details["person"],
            "company": c.details["company"], "subject": c.details["source_title"],
            "source_url": c.details["source_url"], "received_at": c.details["occurred_at"],
            "needs_reply": bool(c.details["fields"].get("needs_reply")) and not c.followup_done,
        } for c in sorted(replies, key=lambda c: c.details["occurred_at"], reverse=True)[:8]],
    }


@router.get("/email")
def overview(user: Owner, db: DB):
    return email_overview(db, user)
