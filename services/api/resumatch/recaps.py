"""Versioned recap schema: metrics are calculated from approved records, never by an LLM."""

from collections import Counter
from datetime import UTC, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict
from sqlalchemy import select

from resumatch.duplicates import normalized_name, profile_identity
from resumatch.models import Capture, SessionRecap

ACTIONS = ("researched", "drafted", "connection_requested", "sent", "followed_up", "replied")


class ActivitySnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid")
    capture_id: UUID
    action: Literal[
        "researched", "drafted", "connection_requested", "sent", "followed_up", "replied"
    ]
    channel: str
    person: str
    company: str
    source_url: str
    notes: str
    source_text: str
    occurred_at: str
    followup_on: str | None
    fields: dict = {}


class RecapPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: Literal[1] = 1
    session_id: UUID
    intention: str
    generated_at: datetime
    completed_at: datetime
    session_seconds: int
    target_minutes: int
    approved_records: int
    discarded_records: int
    action_counts: dict[str, int]
    channel_counts: dict[str, int]
    known_people: int
    known_companies: int
    unknown_person_records: int
    highlights: list[str]
    limitations: list[str]
    activities: list[ActivitySnapshot]
    workflow_id: UUID | None = None
    workflow_name: str | None = None
    workflow_version: int | None = None
    run_name: str | None = None


def ensure_recap(db, session):
    from resumatch.models import Workflow
    existing = db.get(SessionRecap, session.id)
    if existing:
        return existing
    captures = db.scalars(select(Capture).where(Capture.session_id == session.id)
                         .order_by(Capture.created_at, Capture.id)).all()
    approved = [c for c in captures if c.decision == "approved"]
    counts = Counter(c.details["action"] for c in approved)
    people = {profile_identity(c.details["source_url"]) or normalized_name(c.details["person"])
              for c in approved if c.details["person"]}
    companies = {normalized_name(c.details["company"]) for c in approved if c.details["company"]}
    record_word = "record" if len(approved) == 1 else "records"
    highlights = [f"{len(approved)} reviewed {record_word} saved to your private history."]
    if counts["sent"]:
        word = "send" if counts["sent"] == 1 else "sends"
        highlights.append(f"{counts['sent']} initial {word} confirmed by you.")
    if counts["followed_up"]:
        word = "follow-up" if counts["followed_up"] == 1 else "follow-ups"
        highlights.append(f"{counts['followed_up']} {word} confirmed by you.")
    if counts["replied"]:
        word = "reply" if counts["replied"] == 1 else "replies"
        highlights.append(f"{counts['replied']} {word} recorded by you.")
    if counts["connection_requested"]:
        highlights.append(f"{counts['connection_requested']} connection requests confirmed by you.")
    if not any(counts[k] for k in ("sent", "followed_up", "replied", "connection_requested")):
        highlights.append("Preparation is progress. Research and drafts are not contact.")
    payload = RecapPayload(
        session_id=session.id, intention=session.intention, generated_at=datetime.now(UTC),
        workflow_id=session.workflow_id, workflow_name=db.get(Workflow, session.workflow_id).name,
        workflow_version=session.workflow_version, run_name=session.run_name,
        completed_at=session.completed_at, session_seconds=session.elapsed_seconds,
        target_minutes=session.target_minutes, approved_records=len(approved),
        discarded_records=sum(c.decision == "discarded" for c in captures),
        action_counts={key: counts[key] for key in ACTIONS},
        channel_counts=dict(Counter(c.details["channel"] for c in approved)),
        known_people=len(people), known_companies=len(companies),
        unknown_person_records=sum(not c.details["person"] for c in approved),
        highlights=highlights,
        limitations=["Session time is not proof of focused work.",
                     "Actions are user-confirmed, not verified sending or delivery.",
                     "People/companies are normalized logged identities, not verified entities.",
                     "This snapshot describes completion; reminders can be cleared later."],
        activities=[ActivitySnapshot(
            capture_id=c.id, action=c.details["action"], channel=c.details["channel"],
            person=c.details["person"], company=c.details["company"],
            source_url=c.details["source_url"], notes=c.details["notes"],
            source_text=c.details["quote"], occurred_at=c.details["occurred_at"],
            followup_on=c.details.get("followup_on"),
            fields=c.details.get("fields", {}),
        ) for c in approved],
    )
    recap = SessionRecap(session_id=session.id, payload=payload.model_dump(mode="json"))
    db.add(recap)
    db.flush()
    return recap
