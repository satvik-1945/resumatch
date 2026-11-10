"""Exercise the additive data migration against the disposable project PostgreSQL DB."""

import json
from uuid import uuid4

from alembic import command
from alembic.config import Config
from sqlalchemy import text

from resumatch.db import get_engine


def test_migration_preserves_captures_and_groups_only_confirmed_intentions():
    config = Config("alembic.ini")
    command.downgrade(config, "0002_analysis_recaps")
    uid = uuid4()
    captures = []
    try:
        with get_engine().begin() as db:
            db.execute(text("INSERT INTO users (id,email,password_hash) "
                            "VALUES (:id,:email,'test')"),
                       {"id": uid, "email": "migration@example.com"})
            for i, intention in enumerate([
                "Find and contact a fintech founder", "Find contact Fintech Founder",
                "Reaching out the leads", "An unrelated workflow",
            ]):
                sid, cid = uuid4(), uuid4()
                details = {"notes": f"Synthetic retained source {i}", "person": "",
                           "action": "researched"}
                captures.append((str(cid), details))
                db.execute(text(
                    "INSERT INTO outreach_sessions (id,user_id,intention,target_minutes,state) "
                    "VALUES (:id,:uid,:intention,25,'completed')"
                ), {"id": sid, "uid": uid, "intention": intention})
                db.execute(text(
                    "INSERT INTO captures (id,session_id,request_id,source,original,details) "
                    "VALUES (:id,:sid,:rid,'manual',CAST(:d AS jsonb),CAST(:d AS jsonb))"
                ), {"id": cid, "sid": sid, "rid": uuid4(), "d": json.dumps(details)})
        command.upgrade(config, "head")
        with get_engine().connect() as db:
            names = db.execute(text("SELECT name FROM workflows WHERE user_id=:uid"),
                               {"uid": uid}).scalars().all()
            assert set(names) == {
                "Fintech founder connections", "Contact outreach", "An unrelated workflow"
            }
            grouped = db.execute(text(
                "SELECT count(*) FROM outreach_sessions s JOIN workflows w ON w.id=s.workflow_id "
                "WHERE w.name='Fintech founder connections' AND w.user_id=:uid"
            ), {"uid": uid}).scalar()
            assert grouped == 2
            rows = db.execute(text("SELECT id,details,original FROM captures")).all()
            assert {(str(row.id), json.dumps(row.details, sort_keys=True)) for row in rows} == {
                (cid, json.dumps(details, sort_keys=True)) for cid, details in captures
            }
            assert all(row.details == row.original for row in rows)
    finally:
        command.upgrade(config, "head")
