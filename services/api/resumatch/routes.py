import secrets
from collections import Counter
from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select, text
from sqlalchemy.exc import SQLAlchemyError

from resumatch.auth import DB, BrowserOwner, Owner, digest, require_origin
from resumatch.duplicates import duplicate_of, same_subject
from resumatch.intelligence import SourceRequest, analyze_source, configured, reflect_on_recap
from resumatch.models import Capture, OutreachSession, Pairing, SessionEvent, User, Workflow
from resumatch.recaps import ensure_recap
from resumatch.run_names import next_run_name
from resumatch.schemas import (
    BulkApprove,
    CaptureInput,
    EditCapture,
    Goal,
    PairInput,
    Review,
    Start,
    Transition,
)
from resumatch.workflow_contracts import WorkflowWrite, template
from resumatch.workflows import (
    create_workflow,
    definition_for,
    owned_workflow,
    raw_capture_text,
    validate_fields,
)

CONFIRMED_ACTIONS = {"connection_requested", "sent", "followed_up", "replied"}
router = APIRouter(prefix="/api")
writes = [Depends(require_origin)]


def now():
    return datetime.now(UTC)


def session_for(db, user, session_id, lock=False):
    q = select(OutreachSession).where(
        OutreachSession.id == session_id, OutreachSession.user_id == user.id
    )
    session = db.scalar(q.with_for_update() if lock else q)
    if session is None:
        raise HTTPException(404, "Session not found")
    return session


def capture_view(c):
    return {"id": c.id, "details": c.details, "original": c.original, "source": c.source,
            "decision": c.decision, "created_at": c.created_at,
            "reviewed_at": c.reviewed_at, "followup_done": c.followup_done,
            "analysis": c.analysis}


def pasted_text_key(details):
    return " ".join(raw_capture_text(details).casefold().split())


def session_view(db, s, include_captures=False):
    captures = db.scalars(select(Capture).where(Capture.session_id == s.id)
                         .order_by(Capture.created_at, Capture.id)).all()
    approved = [c for c in captures if c.decision == "approved"]
    elapsed = s.elapsed_seconds
    if s.state == "active" and s.running_since:
        elapsed += max(0, int((now() - s.running_since).total_seconds()))
    result = {"id": s.id, "intention": s.intention, "state": s.state,
              "workflow_id": s.workflow_id, "workflow_version": s.workflow_version,
              "workflow_name": db.get(Workflow, s.workflow_id).name, "run_name": s.run_name,
              "workflow_kind": db.get(Workflow, s.workflow_id).kind,
              "field_definition": definition_for(db, s)["fields"],
              "target_minutes": s.target_minutes, "elapsed_seconds": elapsed,
              "started_at": s.started_at, "finished_at": s.finished_at,
              "completed_at": s.completed_at, "approved_count": len(approved),
              "pending_count": sum(c.decision == "pending" for c in captures),
              "counts": dict(Counter(c.details["action"] for c in approved))}
    if include_captures:
        records = []
        seen = []
        for c in captures:
            item = capture_view(c)
            item["duplicate_of"] = next(
                (p.id for p in seen if same_subject(p.details, c.details)), None
            ) if c.decision != "discarded" else None
            records.append(item)
            if c.decision != "discarded":
                seen.append(c)
        # Identical pasted text under different profiles usually means a stale clipboard. Flag
        # every record in the group: only the user can tell which profile the text belongs to.
        by_text = {}
        for c in seen:
            if text := pasted_text_key(c.details):
                by_text.setdefault(text, []).append(c)
        for item in records:
            group = by_text.get(pasted_text_key(item["details"]), []) if (
                item["decision"] != "discarded") else []
            item["same_raw_text_as"] = next((
                c.id for c in group if c.id != item["id"]
                and not same_subject(c.details, item["details"])
            ), None)
        result["captures"] = records
    return result


@router.get("/health/live")
def live():
    return {"status": "ok"}


@router.get("/health/ready")
def ready(db: DB):
    try:
        revision = db.scalar(text("SELECT version_num FROM alembic_version"))
        db.execute(select(OutreachSession.id).limit(0))
        if revision != "0004_contact_briefs":
            raise HTTPException(503, "Run uv run alembic upgrade head")
    except SQLAlchemyError:
        raise HTTPException(503, "Check database connection and run migrations") from None
    return {"status": "ok", "database": "ready"}


@router.post("/sessions", status_code=201, dependencies=writes)
def start(body: Start, user: Owner, db: DB):
    # Serialize creation by owner as well as the partial unique DB index.
    db.scalar(select(User).where(User.id == user.id).with_for_update())
    if db.scalar(select(OutreachSession.id).where(
        OutreachSession.user_id == user.id, OutreachSession.state != "completed"
    )):
        raise HTTPException(409, "Finish your current session and review before starting another")
    if body.workflow_id:
        workflow = owned_workflow(db, user, body.workflow_id)
    else:
        # Compatibility for older capture clients: create an owned parent, never orphan runs.
        workflow = create_workflow(db, user.id, WorkflowWrite(**{
            **template("founder_connections"), "name": body.intention, "kind": "custom"
        }))
    at = now()
    session = OutreachSession(user_id=user.id, running_since=at, started_at=at,
                              intention=body.intention,
                              target_minutes=body.target_minutes, workflow_id=workflow.id,
                              workflow_version=workflow.version,
                              run_name=body.run_name or next_run_name(db, workflow.id, at))
    db.add(session)
    db.flush()
    db.add(SessionEvent(session_id=session.id, action="start"))
    db.commit()
    return session_view(db, session, True)


@router.get("/sessions/{session_id}")
def detail(session_id: UUID, user: Owner, db: DB):
    return session_view(db, session_for(db, user, session_id), True)


@router.post("/sessions/{session_id}/transition", dependencies=writes)
def transition(session_id: UUID, body: Transition, user: Owner, db: DB):
    s = session_for(db, user, session_id, True)
    allowed = {"pause": {"active"}, "resume": {"paused"},
               "finish": {"active", "paused"}, "complete": {"review"}}
    if s.state not in allowed[body.action]:
        raise HTTPException(409, "Session state changed; reload before continuing")
    at = now()
    if body.action == "complete":
        if db.scalar(select(Capture.id).where(
            Capture.session_id == s.id, Capture.decision == "pending"
        ).limit(1)):
            raise HTTPException(409, "Review or discard every capture before completing")
        s.state, s.completed_at = "completed", at
    else:
        if s.state == "active":
            s.elapsed_seconds += max(0, int((at - s.running_since).total_seconds()))
            s.running_since = None
        if body.action == "resume":
            s.state, s.running_since = "active", at
        elif body.action == "pause":
            s.state = "paused"
        else:
            s.state, s.finished_at = "review", at
    db.add(SessionEvent(session_id=s.id, action=body.action))
    if body.action == "complete":
        ensure_recap(db, s)
    db.commit()
    return session_view(db, s, True)


def create_capture(db, user, session_id, body, source):
    s = session_for(db, user, session_id, True)
    previous = db.scalar(select(Capture).where(
        Capture.session_id == s.id, Capture.request_id == body.request_id
    ))
    if previous:
        return capture_view(previous)
    if s.state != "active":
        raise HTTPException(409, "Resume an active session before capturing")
    count = db.scalar(select(func.count()).select_from(Capture).where(Capture.session_id == s.id))
    if count >= 200:
        raise HTTPException(409, "This session has 200 captures; finish and review it")
    details = validate_fields(db, s, body.details.model_dump(mode="json"))
    reject_duplicate(db, s.id, details)
    details["occurred_at"] = details["occurred_at"] or now().isoformat()
    c = Capture(session_id=s.id, request_id=body.request_id, source=source,
                original=details, details=details)
    db.add(c)
    db.commit()
    return capture_view(c)


@router.get("/analysis/status")
def analysis_status(user: Owner):
    from resumatch.config import get_settings

    settings = get_settings()
    return {"configured": configured(), "model": settings.llm_model or None}


def pending_review_capture(db, user, session_id, capture_id, lock=False):
    session = session_for(db, user, session_id, lock)
    c = db.scalar(select(Capture).where(Capture.id == capture_id, Capture.session_id == session.id))
    if c is None:
        raise HTTPException(404, "Capture not found")
    if session.state != "review" or c.decision != "pending":
        raise HTTPException(409, "Source analysis is available for pending records in review")
    return c


@router.post("/sessions/{session_id}/captures/{capture_id}/analyze", dependencies=writes)
def analyze_capture(session_id: UUID, capture_id: UUID, body: SourceRequest, user: Owner, db: DB):
    if not body.source_text.strip():
        raise HTTPException(422, "Paste source text before analyzing")
    c = pending_review_capture(db, user, session_id, capture_id)
    if c.analysis and c.analysis["source_text"] == body.source_text:
        if c.analysis["method"] == "llm" or not configured():
            return c.analysis
    db.rollback()  # Never hold row locks or a database transaction across a provider call.
    result = analyze_source(body.source_text)
    c = pending_review_capture(db, user, session_id, capture_id, lock=True)
    c.analysis = result  # Suggestions only: never change details, decision or action counts.
    db.commit()
    return result


def recap_view(recap):
    return {"payload": recap.payload, "reflection": recap.reflection}


@router.get("/sessions/{session_id}/recap")
def get_recap(session_id: UUID, user: Owner, db: DB):
    session = session_for(db, user, session_id, True)
    if session.state != "completed":
        raise HTTPException(409, "Complete the session to see its recap")
    recap = ensure_recap(db, session)  # Lazy snapshot also supports pre-feature completed sessions.
    db.commit()
    return recap_view(recap)


@router.post("/sessions/{session_id}/recap/analyze", dependencies=writes)
def recap_analysis(session_id: UUID, user: Owner, db: DB):
    session = session_for(db, user, session_id, True)
    if session.state != "completed":
        raise HTTPException(409, "Complete the session before generating observations")
    recap = ensure_recap(db, session)
    if recap.reflection and recap.reflection["method"] == "llm":
        return recap_view(recap)
    payload = recap.payload
    db.commit()
    result = reflect_on_recap(payload)
    session = session_for(db, user, session_id, True)
    recap = ensure_recap(db, session)
    recap.reflection = result
    db.commit()
    return recap_view(recap)


def reject_duplicate(db, session_id, details, exclude_id=None, approved_only=False):
    existing = duplicate_of(db, session_id, details, exclude_id, approved_only)
    if existing:
        raise HTTPException(409, {
            "message": "Already captured in this session. Edit the existing record in the app "
                       "to update its action, notes or follow-up instead of adding it again.",
            "existing_capture_id": str(existing.id),
        })


@router.put("/sessions/{session_id}/captures/{capture_id}", dependencies=writes)
def edit_capture(session_id: UUID, capture_id: UUID, body: EditCapture, user: Owner, db: DB):
    s = session_for(db, user, session_id, True)
    c = db.scalar(select(Capture).where(Capture.id == capture_id, Capture.session_id == s.id))
    if c is None:
        raise HTTPException(404, "Capture not found")
    if s.state not in {"active", "paused", "review"} or c.decision != "pending":
        raise HTTPException(409, "Only pending captures in an open run can be edited")
    details = validate_fields(db, s, body.details.model_dump(mode="json"))
    reject_duplicate(db, s.id, details, c.id)
    details["occurred_at"] = details["occurred_at"] or c.details["occurred_at"]
    c.details = details
    db.commit()
    return capture_view(c)


@router.post("/sessions/{session_id}/captures", status_code=201, dependencies=writes)
def manual_capture(session_id: UUID, body: CaptureInput, user: Owner, db: DB):
    return create_capture(db, user, session_id, body, "manual")


@router.post("/sessions/{session_id}/captures/{capture_id}/review", dependencies=writes)
def review(session_id: UUID, capture_id: UUID, body: Review, user: Owner, db: DB):
    s = session_for(db, user, session_id, True)
    c = db.scalar(select(Capture).where(Capture.id == capture_id, Capture.session_id == s.id))
    if c is None:
        raise HTTPException(404, "Capture not found")
    if s.state != "review" or c.decision != "pending":
        raise HTTPException(409, "Only pending captures in a finished session can be reviewed")
    if body.decision == "approved" and body.details.action in CONFIRMED_ACTIONS:
        if not body.confirmed_action or not body.details.person:
            raise HTTPException(422, "Name the person and confirm this action actually happened")
    details = validate_fields(db, s, body.details.model_dump(mode="json"))
    if body.decision == "approved":
        reject_duplicate(db, s.id, details, c.id, approved_only=True)
    details["occurred_at"] = details["occurred_at"] or c.original["occurred_at"]
    c.details, c.decision, c.reviewed_at = details, body.decision, now()
    db.commit()
    return capture_view(c)


@router.post("/sessions/{session_id}/captures/bulk-approve", dependencies=writes)
def bulk_approve(session_id: UUID, body: BulkApprove, user: Owner, db: DB):
    """Approve the listed pending records as saved. Anything needing a person's judgement is
    skipped with a reason, never approved: confirmed actions, duplicates and reused pasted text."""
    s = session_for(db, user, session_id, True)
    if s.state != "review":
        raise HTTPException(409, "Only pending captures in a finished session can be reviewed")
    view = {item["id"]: item for item in session_view(db, s, True)["captures"]}
    approved, skipped = [], []
    for cid in dict.fromkeys(body.capture_ids):
        item = view.get(cid)
        c = db.get(Capture, cid) if item else None
        if c is None:
            reason = "Not in this run"
        elif c.decision != "pending":
            reason = "Already reviewed"
        elif c.details["action"] in CONFIRMED_ACTIONS:
            reason = "Needs your confirmation that the action happened"
        elif item["duplicate_of"] or item["same_raw_text_as"]:
            reason = "Possible duplicate; review it individually"
        elif duplicate_of(db, s.id, c.details, c.id, approved_only=True):
            reason = "Same contact already approved in this run"
        else:
            reason = None
        if reason:
            skipped.append({"id": cid, "reason": reason})
            continue
        details = validate_fields(db, s, dict(c.details))
        details["occurred_at"] = details["occurred_at"] or c.original["occurred_at"]
        c.details, c.decision, c.reviewed_at = details, "approved", now()
        db.flush()
        approved.append(cid)
    db.commit()
    return {"approved": approved, "skipped": skipped,
            "session": session_view(db, s, include_captures=True)}


@router.get("/overview")
def overview(user: Owner, db: DB, offset: int = Query(0, ge=0, le=100000)):
    sessions = db.scalars(select(OutreachSession).where(OutreachSession.user_id == user.id)
                         .order_by(OutreachSession.started_at.desc()).offset(offset).limit(20)).all()
    current = db.scalar(select(OutreachSession).where(
        OutreachSession.user_id == user.id, OutreachSession.state != "completed"
    ))
    week_start = now().replace(hour=0, minute=0, second=0, microsecond=0)
    week_start -= timedelta(days=week_start.weekday())
    reviewed_sessions = select(Capture.session_id).where(Capture.decision == "approved")
    completed_week = db.scalar(select(func.count()).select_from(OutreachSession).where(
        OutreachSession.user_id == user.id, OutreachSession.state == "completed",
        OutreachSession.completed_at >= week_start, OutreachSession.id.in_(reviewed_sessions),
    ))
    approved = db.scalars(select(Capture).join(OutreachSession).where(
        OutreachSession.user_id == user.id, Capture.decision == "approved",
        Capture.reviewed_at >= week_start,
    )).all()
    reminders = db.scalars(select(Capture).join(OutreachSession).where(
        OutreachSession.user_id == user.id, Capture.decision == "approved",
        Capture.followup_done.is_(False),
        Capture.details["followup_on"].astext.is_not(None),
    ).order_by(Capture.details["followup_on"].astext).limit(200)).all()
    today = now().date().isoformat()
    return {"current": session_view(db, current, True) if current else None,
            "history": [session_view(db, s) for s in sessions],
            "week": {"starts_at": week_start, "sessions": completed_week,
                     "target": user.weekly_target,
                     "counts": dict(Counter(c.details["action"] for c in approved))},
            "followups": [capture_view(c) for c in reminders if c.details["followup_on"] <= today],
            "upcoming_followups": [capture_view(c) for c in reminders
                                   if c.details["followup_on"] > today]}


@router.put("/goal", dependencies=writes)
def goal(body: Goal, user: Owner, db: DB):
    user.weekly_target = body.weekly_target
    db.commit()
    return {"weekly_target": user.weekly_target}


@router.post("/captures/{capture_id}/followup-done", dependencies=writes)
def followup_done(capture_id: UUID, user: Owner, db: DB):
    c = db.scalar(select(Capture).join(OutreachSession).where(
        Capture.id == capture_id, OutreachSession.user_id == user.id,
        Capture.decision == "approved",
    ).with_for_update())
    if c is None:
        raise HTTPException(404, "Follow-up not found")
    c.followup_done = True
    db.commit()
    return {"done": True}


@router.post("/pairings", dependencies=writes)
def pair(body: PairInput, user: Owner, db: DB):
    token = secrets.token_urlsafe(32)
    p = Pairing(user_id=user.id, extension_id=body.extension_id, token_hash=digest(token),
                expires_at=now() + timedelta(days=7))
    db.add(p)
    db.commit()
    return {"id": p.id, "token": token, "expires_at": p.expires_at}


@router.get("/pairings")
def pairings(user: Owner, db: DB):
    items = db.scalars(select(Pairing).where(Pairing.user_id == user.id)
                       .order_by(Pairing.created_at.desc()).limit(50)).all()
    return [{"id": p.id, "extension_id": p.extension_id, "expires_at": p.expires_at,
             "revoked": p.revoked} for p in items]


@router.delete("/pairings/{pairing_id}", status_code=204, dependencies=writes)
def revoke(pairing_id: UUID, user: Owner, db: DB):
    p = db.scalar(select(Pairing).where(Pairing.id == pairing_id, Pairing.user_id == user.id))
    if not p:
        raise HTTPException(404, "Pairing not found")
    p.revoked = True
    db.commit()


@router.get("/extension/session")
def browser_session(user: BrowserOwner, db: DB):
    s = db.scalar(select(OutreachSession).where(
        OutreachSession.user_id == user.id, OutreachSession.state != "completed"
    ))
    return {"session": {"id": s.id, "intention": s.intention, "state": s.state,
                        "run_name": s.run_name,
                        "workflow_name": db.get(Workflow, s.workflow_id).name,
                        "fields": definition_for(db, s)["fields"]} if s else None}


@router.post("/extension/sessions/{session_id}/captures", status_code=201)
def browser_capture(session_id: UUID, body: CaptureInput, user: BrowserOwner, db: DB):
    return create_capture(db, user, session_id, body, "browser")
