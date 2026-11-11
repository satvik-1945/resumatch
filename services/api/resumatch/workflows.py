"""Private parent workflows, dated runs, field contracts and consolidated contact views."""

import hashlib
import re
from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import Field
from sqlalchemy import select

from resumatch.ai_runs import ai_run
from resumatch.auth import DB, Owner, require_origin
from resumatch.duplicates import normalized_name, profile_identity
from resumatch.intelligence import local_suggestions, provider_json
from resumatch.models import Capture, OutreachSession, Workflow, WorkflowVersion
from resumatch.run_names import next_run_name
from resumatch.schemas import Input
from resumatch.workflow_contracts import (
    WorkflowWrite,
    compile_definition,
    ground_output,
    template,
    transform_output,
    validate_record_fields,
)

router = APIRouter(prefix="/api")
writes = [Depends(require_origin)]


def owned_workflow(db, user, wid, lock=False):
    q = select(Workflow).where(Workflow.id == wid, Workflow.user_id == user.id)
    item = db.scalar(q.with_for_update() if lock else q)
    if item is None:
        raise HTTPException(404, "Workflow not found")
    return item


def definition_for(db, session):
    return db.get(WorkflowVersion, (session.workflow_id, session.workflow_version)).definition


def validate_fields(db, session, details):
    try:
        details["fields"] = validate_record_fields(details, definition_for(db, session))
    except ValueError as error:
        raise HTTPException(422, str(error)) from None
    return details


def create_workflow(db, user_id, body):
    item = Workflow(user_id=user_id, name=body.name, description=body.description, kind=body.kind)
    db.add(item)
    db.flush()
    db.add(WorkflowVersion(workflow_id=item.id, version=1,
                           definition=compile_definition([f.model_dump() for f in body.fields])))
    db.flush()
    return item


def workflow_view(db, item):
    definition = db.get(WorkflowVersion, (item.id, item.version)).definition
    runs = db.scalars(select(OutreachSession).where(OutreachSession.workflow_id == item.id)
                      .order_by(OutreachSession.started_at.desc())).all()
    records = db.scalars(select(Capture).join(OutreachSession).where(
        OutreachSession.workflow_id == item.id, Capture.decision != "discarded"
    )).all()
    return {"id": item.id, "name": item.name, "description": item.description, "kind": item.kind,
            "version": item.version, "fields": definition["fields"], "record_count": len(records),
            "next_run_name": next_run_name(db, item.id, datetime.now(UTC)),
            "approved_count": sum(c.decision == "approved" for c in records),
            "pending_count": sum(c.decision == "pending" for c in records),
            "runs": [{"id": s.id, "run_name": s.run_name, "intention": s.intention,
                      "state": s.state, "started_at": s.started_at,
                      "workflow_version": s.workflow_version, "elapsed_seconds": s.elapsed_seconds,
                      "record_count": sum(c.session_id == s.id for c in records),
                      "pending_count": sum(c.session_id == s.id and c.decision == "pending"
                                           for c in records),
                      "approved_count": sum(c.session_id == s.id and c.decision == "approved"
                                            for c in records)} for s in runs]}


@router.get("/workflow-templates")
def templates(user: Owner):
    return [template("founder_connections"), template("contact_outreach")]


@router.get("/workflows")
def list_workflows(user: Owner, db: DB):
    items = db.scalars(select(Workflow).where(Workflow.user_id == user.id)
                       .order_by(Workflow.created_at.desc()).limit(100)).all()
    return [workflow_view(db, w) for w in items]


@router.post("/workflows", status_code=201, dependencies=writes)
def new_workflow(body: WorkflowWrite, user: Owner, db: DB):
    item = create_workflow(db, user.id, body)
    db.commit()
    return workflow_view(db, item)


@router.put("/workflows/{wid}", dependencies=writes)
def update_workflow(wid: UUID, body: WorkflowWrite, user: Owner, db: DB):
    item = owned_workflow(db, user, wid, True)
    if body.expected_version != item.version:
        raise HTTPException(409, "Workflow changed; reload its fields before saving")
    item.name, item.description, item.kind = body.name, body.description, body.kind
    item.version += 1
    db.add(WorkflowVersion(workflow_id=item.id, version=item.version,
                           definition=compile_definition([f.model_dump() for f in body.fields])))
    db.commit()
    return workflow_view(db, item)


@router.get("/workflows/{wid}/contract")
def workflow_contract(wid: UUID, user: Owner, db: DB):
    item = owned_workflow(db, user, wid)
    return {"workflow_id": item.id, "name": item.name, "version": item.version,
            **db.get(WorkflowVersion, (item.id, item.version)).definition}


@router.get("/workflows/{wid}/records")
def consolidated_records(wid: UUID, user: Owner, db: DB):
    owned_workflow(db, user, wid)
    entries = db.execute(select(Capture, OutreachSession).join(OutreachSession).where(
        OutreachSession.workflow_id == wid, OutreachSession.user_id == user.id,
        Capture.decision != "discarded",
    ).order_by(Capture.created_at.desc(), Capture.id).limit(5001)).all()
    if len(entries) > 5000:
        raise HTTPException(409, "Workflow exceeds the current 5,000-record consolidated limit")
    grouped = {}
    for c, run in entries:
        d = c.details
        key = profile_identity(d["source_url"]) or (
            "name:" + normalized_name(d["person"]) + ":" + normalized_name(d["company"])
            if d["person"] else "url:" + d["source_url"]
        )
        if key not in grouped:
            grouped[key] = {"contact_key": key, "contact_url": d["source_url"],
                            "person": "", "company": "", "fields": {}, "entries": []}
        row = grouped[key]
        for field in ("person", "company"):
            if not row[field] and d[field]:
                row[field] = d[field]
        for field, value in d.get("fields", {}).items():
            if field not in row["fields"] and value is not None and value != "":
                row["fields"][field] = value
        row["entries"].append({"capture_id": c.id, "run_id": run.id, "run_name": run.run_name,
                               "decision": c.decision, "action": d["action"],
                               "occurred_at": d["occurred_at"],
                               "followup_on": d.get("followup_on")})
    return {"contacts": list(grouped.values()), "record_count": len(entries),
            "contact_count": len(grouped), "includes_pending": True}


class RunUpdate(Input):
    run_name: str = Field(min_length=1, max_length=200)


@router.put("/sessions/{sid}/name", dependencies=writes)
def rename_run(sid: UUID, body: RunUpdate, user: Owner, db: DB):
    from resumatch.routes import session_for, session_view

    session = session_for(db, user, sid, True)
    session.run_name = body.run_name
    db.commit()
    return session_view(db, session, True)


@router.post("/sessions/{sid}/sync-workflow", dependencies=writes)
def sync_run_fields(sid: UUID, user: Owner, db: DB):
    from resumatch.routes import session_for, session_view

    session = session_for(db, user, sid, True)
    if session.state == "completed":
        raise HTTPException(409, "Completed runs keep their field-definition version")
    latest = owned_workflow(db, user, session.workflow_id)
    old = {f["key"]: f for f in definition_for(db, session)["fields"]}
    new = db.get(WorkflowVersion, (latest.id, latest.version)).definition
    types = {f["key"]: f["type"] for f in new["fields"]}
    if any(k not in types or f["type"] != types[k] for k, f in old.items()):
        raise HTTPException(409, "Update removes/changes existing fields; start a new run instead")
    session.workflow_version = latest.version
    db.commit()
    return session_view(db, session, True)


def raw_capture_text(details):
    notes, quote = details.get("notes", ""), details.get("quote", "")
    return (notes + ("\n\n" + quote if quote and quote not in notes else "")).strip()[:16000]


def local_fields(source, definition):
    known = local_suggestions(source)
    output = {"fields": {}}
    for field in definition["fields"]:
        key = field["key"]
        if key == "contact_url":
            continue
        if key in {"person", "company", "role"} and getattr(known, key):
            output["fields"][key] = getattr(known, key).model_dump()
        elif field["type"] in {"text", "long_text"}:
            pattern = re.escape(field["label"]) + "|" + re.escape(key)
            match = re.search(rf"(?im)^[ \t]*(?:{pattern})[ \t]*:[ \t]*([^\r\n]{{1,200}})", source)
            if match and match.group(1).strip():
                output["fields"][key] = {"value": match.group(1).strip(),
                                          "source_quote": match.group(0).strip()}
    return output


@router.post("/sessions/{sid}/captures/{cid}/process-ai", dependencies=writes)
def process_capture(sid: UUID, cid: UUID, user: Owner, db: DB):
    from resumatch.config import get_settings
    from resumatch.routes import capture_view, session_for

    session = session_for(db, user, sid)
    capture = db.scalar(select(Capture).where(Capture.session_id == sid, Capture.id == cid))
    if capture is None:
        raise HTTPException(404, "Capture not found")
    if session.state == "completed" or capture.decision != "pending":
        raise HTTPException(409, "AI processing only updates pending records in an open run")
    source = raw_capture_text(capture.details)
    if not source:
        raise HTTPException(422, "Add raw capture text before processing this record")
    sha = hashlib.sha256(source.encode()).hexdigest()
    definition = definition_for(db, session)
    version, wid = session.workflow_version, session.workflow_id
    if capture.analysis and capture.analysis.get("workflow_version") == version and (
        capture.analysis.get("workflow_id") == str(wid)
        and capture.analysis.get("source_sha256") == sha and capture.analysis.get("method") == "llm"
    ):
        return {"capture": capture_view(capture), "cached": True}
    with ai_run(user.id, "capture_fields", str(cid), run_id=str(sid), workflow_id=str(wid),
                workflow_version=version) as run:
        db.rollback()
        method, warning, failure, rejected = "llm", None, None, []
        try:
            output = provider_json(definition["output_schema"], definition["system_prompt"],
                                   {"raw_text": source})
        except ValueError as error:
            failure, warning = "provider", str(error)
        else:
            try:
                output, rejected = ground_output(output, source, definition)
            except ValueError as error:
                failure, warning = "output", str(error)
                run.reject(warning)
        local, _ = ground_output(local_fields(source, definition), source, definition)
        if failure:
            method, rejected, output = "local", [], local
        else:
            # Labeled "Field: value" lines still fill what the model omitted or got rejected for.
            output["fields"] = {**local["fields"], **output["fields"]}
            if rejected:
                warning = "Skipped AI values not found in the raw text: " + ", ".join(rejected)
        mapped = transform_output(output, source, definition)
        session = session_for(db, user, sid, True)
        db.expire_all()
        capture = db.scalar(select(Capture).where(Capture.session_id == sid, Capture.id == cid))
        if (session.state == "completed" or capture.decision != "pending"
                or session.workflow_version != version
                or raw_capture_text(capture.details) != source):
            raise HTTPException(409, "Record or workflow changed during processing; "
                                     "reload and retry")
        details = {**capture.details, "fields": dict(capture.details.get("fields", {}))}
        filled, preserved = [], []
        for key, value in mapped.items():
            if value is None or value == "":
                continue
            target = details if key in {"person", "company"} else details["fields"]
            if target.get(key) is not None and target.get(key) != "":
                preserved.append(key)
            else:
                target[key] = value
                filled.append(key)
        capture.details = validate_fields(db, session, details)
        capture.analysis = {
            "schema_version": 2, "workflow_id": str(wid), "workflow_version": version,
            "method": method, "model": get_settings().llm_model if method == "llm" else None,
            "source_text": source, "source_sha256": sha,
            "processed_at": datetime.now(UTC).isoformat(), "fields": output["fields"],
            "filled_fields": filled, "preserved_fields": preserved,
            "rejected_fields": rejected, "failure": failure, "warning": warning,
            "ai_run_id": str(run.id)}
        run.result = {"method": method, "fields": output["fields"], "filled_fields": filled,
                      "preserved_fields": preserved}
        run.rejected = rejected
        db.commit()
    return {"capture": capture_view(capture), "cached": False}
