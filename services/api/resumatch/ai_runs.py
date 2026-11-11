"""AI monitoring: every generation is stored so prompts can be improved from real results.

A run records the prompt version, the exact input (including fetched website research), the raw
model output, what grounding kept or rejected, errors, latency, tokens and the user's rating.
`provider_json` fills the active trace; call sites add research, results and rejections.
"""

import hashlib
import json
import logging
import uuid
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import Field
from sqlalchemy import case, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from resumatch.auth import DB, Owner, require_origin
from resumatch.db import get_engine
from resumatch.models import AiPrompt, AiRun
from resumatch.schemas import Input

router = APIRouter(prefix="/api")
writes = [Depends(require_origin)]
log = logging.getLogger(__name__)
KINDS = ("capture_fields", "brief", "persona", "source_analysis", "recap_reflection")
STATUSES = ("ok", "partial", "rejected", "provider_error", "fetch_error", "error")


@dataclass
class Trace:
    user_id: UUID
    kind: str
    subject: str | None = None
    id: UUID = field(default_factory=uuid.uuid4)
    meta: dict = field(default_factory=dict)
    status: str | None = None
    instruction: str | None = None
    output_schema: dict | None = None
    model: str | None = None
    research: dict | None = None
    input: dict | None = None
    output: dict | None = None
    result: dict | None = None
    rejected: list = field(default_factory=list)
    error: str | None = None
    latency_ms: int | None = None
    usage: dict = field(default_factory=dict)

    def request(self, instruction, output_schema, data, model):
        self.instruction, self.output_schema, self.input, self.model = (
            instruction, output_schema, data, model)

    def response(self, latency_ms, output=None, usage=None, error=None):
        self.latency_ms, self.output, self.usage = latency_ms, output, usage or {}
        if error:
            self.status, self.error = "provider_error", error

    def reject(self, error):
        """Model answered but nothing usable survived grounding/validation."""
        if self.status is None:
            self.status, self.error = "rejected", error

    def final_status(self):
        return self.status or ("partial" if self.rejected else "ok")


CURRENT: ContextVar[Trace | None] = ContextVar("ai_trace", default=None)


def current_trace():
    return CURRENT.get()


def prompt_sha(instruction, output_schema):
    blob = json.dumps({"instruction": instruction, "schema": output_schema}, sort_keys=True)
    return hashlib.sha256(blob.encode()).hexdigest()


def save(trace):
    sha = None
    with Session(get_engine()) as db:
        if trace.instruction is not None:
            sha = prompt_sha(trace.instruction, trace.output_schema)
            db.execute(insert(AiPrompt).values(
                sha256=sha, kind=trace.kind, instruction=trace.instruction,
                output_schema=trace.output_schema or {}).on_conflict_do_nothing())
        db.add(AiRun(
            id=trace.id, user_id=trace.user_id, kind=trace.kind, subject=trace.subject,
            status=trace.final_status(), prompt_sha256=sha, model=trace.model, meta=trace.meta,
            research=trace.research, input=trace.input, output=trace.output, result=trace.result,
            rejected=trace.rejected, error=trace.error, latency_ms=trace.latency_ms,
            prompt_tokens=trace.usage.get("prompt_tokens"),
            completion_tokens=trace.usage.get("completion_tokens")))
        db.commit()


@contextmanager
def ai_run(user_id, kind, subject=None, **meta):
    """Trace one generation. Saved in its own transaction so failed requests are kept too."""
    trace = Trace(user_id=user_id, kind=kind, subject=subject, meta=meta)
    token = CURRENT.set(trace)
    try:
        yield trace
    except HTTPException as error:
        if trace.status is None:
            trace.status, trace.error = "error", str(error.detail)
        raise
    except Exception as error:
        if trace.status is None:
            trace.status, trace.error = "error", type(error).__name__
        raise
    finally:
        CURRENT.reset(token)
        # Nothing reached research or the provider (e.g. validation 404s): nothing to learn from.
        if trace.instruction is not None or trace.research is not None:
            try:
                save(trace)
            except Exception:
                log.exception("Could not store AI run %s", trace.id)


def run_summary(run):
    return {"id": run.id, "kind": run.kind, "subject": run.subject, "status": run.status,
            "model": run.model, "prompt_sha256": run.prompt_sha256, "meta": run.meta,
            "rejected_count": len(run.rejected), "error": run.error,
            "latency_ms": run.latency_ms, "prompt_tokens": run.prompt_tokens,
            "completion_tokens": run.completion_tokens, "rating": run.rating,
            "feedback": run.feedback, "created_at": run.created_at}


def owned_run(db, user, run_id):
    run = db.get(AiRun, run_id)
    if run is None or run.user_id != user.id:
        raise HTTPException(404, "AI run not found")
    return run


@router.get("/ai-runs")
def list_runs(user: Owner, db: DB, kind: str | None = Query(None, max_length=40),
              status: str | None = Query(None, max_length=20),
              limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0)):
    query = select(AiRun).where(AiRun.user_id == user.id)
    if kind:
        query = query.where(AiRun.kind == kind)
    if status:
        query = query.where(AiRun.status == status)
    runs = db.scalars(query.order_by(AiRun.created_at.desc()).offset(offset).limit(limit))
    return {"runs": [run_summary(r) for r in runs]}


def count(condition):
    return func.count(case((condition, 1)))


@router.get("/ai-runs/stats")
def run_stats(user: Owner, db: DB):
    """Per prompt version, so a prompt change can be compared against the one before it."""
    rows = db.execute(
        select(AiRun.kind, AiRun.prompt_sha256, func.count(),
               *[count(AiRun.status == s) for s in STATUSES],
               func.avg(AiRun.latency_ms), func.sum(AiRun.prompt_tokens),
               func.sum(AiRun.completion_tokens), count(AiRun.rating == 1),
               count(AiRun.rating == -1), func.min(AiRun.created_at), func.max(AiRun.created_at))
        .where(AiRun.user_id == user.id).group_by(AiRun.kind, AiRun.prompt_sha256)
        .order_by(func.max(AiRun.created_at).desc())
    ).all()
    out = []
    for r in rows:
        kind, sha, total, *rest = r
        by_status = dict(zip(STATUSES, rest[:len(STATUSES)], strict=True))
        avg, p_tok, c_tok, up, down, first, last = rest[len(STATUSES):]
        out.append({"kind": kind, "prompt_sha256": sha, "runs": total, "statuses": by_status,
                    "avg_latency_ms": round(avg) if avg is not None else None,
                    "prompt_tokens": p_tok, "completion_tokens": c_tok, "thumbs_up": up,
                    "thumbs_down": down, "first_at": first, "last_at": last})
    return {"versions": out}


@router.get("/ai-runs/{run_id}")
def get_run(run_id: UUID, user: Owner, db: DB):
    run = owned_run(db, user, run_id)
    prompt = db.get(AiPrompt, run.prompt_sha256) if run.prompt_sha256 else None
    return {**run_summary(run), "research": run.research, "input": run.input,
            "output": run.output, "result": run.result, "rejected": run.rejected,
            "prompt": prompt and {"sha256": prompt.sha256, "instruction": prompt.instruction,
                                  "output_schema": prompt.output_schema}}


class Feedback(Input):
    rating: Literal[-1, 0, 1]  # 0 clears the rating
    feedback: str = Field(default="", max_length=2000)


@router.put("/ai-runs/{run_id}/feedback", dependencies=writes)
def rate_run(run_id: UUID, body: Feedback, user: Owner, db: DB):
    run = owned_run(db, user, run_id)
    run.rating = body.rating or None
    run.feedback = body.feedback.strip()
    run.rated_at = datetime.now(UTC)
    db.commit()
    return run_summary(run)
