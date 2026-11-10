"""Group existing sessions into owned workflows without deleting or reclassifying captures."""

import uuid

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0003_workflows"
down_revision = "0002_analysis_recaps"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "workflows", sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"),
                  nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("kind", sa.String(40), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
    )
    op.create_index("ix_workflows_user_id", "workflows", ["user_id"])
    op.create_table(
        "workflow_versions",
        sa.Column("workflow_id", sa.Uuid(), sa.ForeignKey("workflows.id", ondelete="CASCADE"),
                  primary_key=True),
        sa.Column("version", sa.Integer(), primary_key=True),
        sa.Column("definition", JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
    )
    op.add_column("outreach_sessions", sa.Column("workflow_id", sa.Uuid(), nullable=True))
    op.add_column("outreach_sessions", sa.Column("workflow_version", sa.Integer(), nullable=True))
    op.add_column("outreach_sessions", sa.Column("run_name", sa.String(200), nullable=True))
    # The two known intentions were confirmed by the user as parent workflows. Other intentions
    # retain their own group rather than being guessed into one of these categories.
    from resumatch.workflow_contracts import compile_definition, template

    bind = op.get_bind()
    workflows = sa.table("workflows", sa.column("id", sa.Uuid()), sa.column("user_id", sa.Uuid()),
                         sa.column("name"), sa.column("description"), sa.column("kind"))
    versions = sa.table("workflow_versions", sa.column("workflow_id", sa.Uuid()),
                       sa.column("version", sa.Integer()), sa.column("definition", JSONB()))
    groups = {}
    date_counts = {}
    rows = bind.execute(sa.text(
        "SELECT id, user_id, intention, started_at FROM outreach_sessions ORDER BY started_at, id"
    )).mappings()
    for row in rows:
        normalized = " ".join(row["intention"].casefold().split())
        if normalized in {"find and contact a fintech founder", "find contact fintech founder"}:
            kind = "founder_connections"
        elif normalized == "reaching out the leads":
            kind = "contact_outreach"
        else:
            kind = "custom"
        key = (row["user_id"], kind if kind != "custom" else normalized)
        if key not in groups:
            value = template(kind if kind != "custom" else "founder_connections")
            if kind == "custom":
                value.update(name=row["intention"], kind=kind)
            wid = uuid.uuid4()
            bind.execute(workflows.insert().values(id=wid, user_id=row["user_id"],
                name=value["name"], description=value["description"], kind=kind))
            bind.execute(versions.insert().values(workflow_id=wid, version=1,
                                                  definition=compile_definition(value["fields"])))
            groups[key] = wid
        wid = groups[key]
        day = row["started_at"].date().isoformat()
        date_counts[(wid, day)] = date_counts.get((wid, day), 0) + 1
        suffix = "" if date_counts[(wid, day)] == 1 else f" · {date_counts[(wid, day)]}"
        bind.execute(sa.text(
            "UPDATE outreach_sessions SET workflow_id=:wid, workflow_version=1, "
            "run_name=:name WHERE id=:id"
        ), {"wid": wid, "name": day + suffix, "id": row["id"]})
    op.alter_column("outreach_sessions", "workflow_id", nullable=False)
    op.alter_column("outreach_sessions", "workflow_version", nullable=False)
    op.alter_column("outreach_sessions", "run_name", nullable=False)
    op.create_foreign_key("session_workflow_fk", "outreach_sessions", "workflows",
                          ["workflow_id"], ["id"])
    op.create_index("ix_outreach_sessions_workflow_id", "outreach_sessions", ["workflow_id"])


def downgrade():
    op.drop_index("ix_outreach_sessions_workflow_id", table_name="outreach_sessions")
    op.drop_constraint("session_workflow_fk", "outreach_sessions", type_="foreignkey")
    for column in ("run_name", "workflow_version", "workflow_id"):
        op.drop_column("outreach_sessions", column)
    op.drop_table("workflow_versions")
    op.drop_table("workflows")
