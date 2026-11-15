"""Owner-scoped activity calendar and factual comparisons; no AI-generated performance scores."""

from calendar import monthrange
from collections import defaultdict
from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import Field, field_validator
from sqlalchemy import and_, func, or_, select

from resumatch.auth import DB, Owner, require_origin
from resumatch.models import Capture, OutreachSession, Workflow
from resumatch.schemas import Input

PALETTE = ("#c8ef80", "#f6a58b", "#7fd6d0", "#b7adf5", "#edca76", "#9bbcf2", "#e8a3cc")
router = APIRouter(prefix="/api")


def approved_counts():
    return select(Capture.session_id, func.count().label("approved_records")).where(
        Capture.decision == "approved"
    ).group_by(Capture.session_id).subquery()


def available_color(db, user_id):
    used = set(db.scalars(select(Workflow.color).where(Workflow.user_id == user_id)))
    return next((c for c in PALETTE if c not in used), PALETTE[len(used) % len(PALETTE)])


class ColorWrite(Input):
    color: str = Field(pattern=r"^#[0-9a-fA-F]{6}$")

    @field_validator("color")
    @classmethod
    def normalize_color(cls, value):
        return value.lower()


@router.put("/workflows/{workflow_id}/color", dependencies=[Depends(require_origin)])
def change_color(workflow_id: UUID, body: ColorWrite, user: Owner, db: DB):
    workflow = db.scalar(select(Workflow).where(
        Workflow.id == workflow_id, Workflow.user_id == user.id
    ).with_for_update())
    if workflow is None:
        raise HTTPException(404, "Workflow not found")
    workflow.color = body.color
    db.commit()
    return {"id": workflow.id, "color": workflow.color}


@router.get("/activity")
def monthly_activity(user: Owner, db: DB, month: str | None = Query(
    default=None, pattern=r"^\d{4}-\d{2}$"
)):
    now = datetime.now(UTC)
    month = month or now.strftime("%Y-%m")
    try:
        year, number = map(int, month.split("-"))
        start = datetime(year, number, 1, tzinfo=UTC)
        end = datetime(year + (number == 12), number % 12 + 1, 1, tzinfo=UTC)
    except ValueError:
        raise HTTPException(422, "Choose a valid month in YYYY-MM format") from None
    approved = approved_counts()
    entries = db.execute(select(OutreachSession, Workflow, approved.c.approved_records).join(
        Workflow, Workflow.id == OutreachSession.workflow_id
    ).join(approved, approved.c.session_id == OutreachSession.id).where(
        OutreachSession.user_id == user.id, Workflow.user_id == user.id,
        OutreachSession.state == "completed", OutreachSession.started_at >= start,
        OutreachSession.started_at < end, OutreachSession.started_at <= now,
        OutreachSession.completed_at <= now,
    ).order_by(OutreachSession.started_at, OutreachSession.id)).all()
    grouped = defaultdict(list)
    legend = {}
    for run, workflow, count in entries:
        summary = {"id": run.id, "run_name": run.run_name, "workflow_id": workflow.id,
                   "workflow_name": workflow.name, "color": workflow.color,
                   "session_seconds": run.elapsed_seconds, "approved_records": count}
        grouped[run.started_at.astimezone(UTC).date().isoformat()].append(summary)
        legend[str(workflow.id)] = {"id": workflow.id, "name": workflow.name,
                                    "color": workflow.color}
    days = []
    for day in range(1, monthrange(year, number)[1] + 1):
        key = f"{month}-{day:02d}"
        runs = grouped[key]
        days.append({"date": key, "runs": runs,
                     "approved_records": sum(r["approved_records"] for r in runs),
                     "session_seconds": sum(r["session_seconds"] for r in runs)})
    return {"month": month, "today": now.date().isoformat(), "timezone": "UTC",
            "date_basis": "run_started_at", "days": days, "workflows": list(legend.values()),
            "summary": {"active_days": sum(bool(d["runs"]) for d in days),
                        "completed_runs": len(entries),
                        "approved_records": sum(d["approved_records"] for d in days),
                        "session_seconds": sum(d["session_seconds"] for d in days)}}


def recap_progress(db, session, payload):
    """Derived companion metadata: never rewrite the original completed recap snapshot."""
    approved = approved_counts()
    previous = db.execute(select(OutreachSession, approved.c.approved_records).join(
        approved, approved.c.session_id == OutreachSession.id
    ).where(
        OutreachSession.user_id == session.user_id,
        OutreachSession.workflow_id == session.workflow_id,
        OutreachSession.state == "completed",
        OutreachSession.completed_at <= session.completed_at,
        or_(OutreachSession.started_at < session.started_at, and_(
            OutreachSession.started_at == session.started_at, OutreachSession.id < session.id
        )),
    ).order_by(OutreachSession.started_at.desc(), OutreachSession.id.desc())).all()
    workflow = db.get(Workflow, session.workflow_id)
    baseline = previous[0] if previous else None
    return {"workflow_id": workflow.id, "workflow_name": workflow.name, "color": workflow.color,
            "run_name": session.run_name, "previous_runs": len(previous),
            "previous": {"id": baseline[0].id, "run_name": baseline[0].run_name,
                         "approved_records": baseline[1],
                         "session_seconds": baseline[0].elapsed_seconds} if baseline else None,
            "record_delta": payload["approved_records"] - baseline[1] if baseline else None,
            "time_delta_seconds": payload["session_seconds"] - baseline[0].elapsed_seconds
            if baseline else None,
            "personal_best_records": bool(previous) and payload["approved_records"] > max(
                count for _, count in previous
            )}
