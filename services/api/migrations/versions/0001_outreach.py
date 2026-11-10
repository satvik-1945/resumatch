"""Fresh outreach session schema after the user-approved reset."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0001_outreach"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("email", sa.String(320), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("weekly_target", sa.Integer(), nullable=False, server_default="3"),
        sa.CheckConstraint("weekly_target BETWEEN 1 AND 14", name="weekly_target_range"),
    )
    op.create_table(
        "logins",
        sa.Column("token_hash", sa.String(64), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"),
                  nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_logins_user_id", "logins", ["user_id"])
    op.create_table(
        "extension_pairings",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"),
                  nullable=False),
        sa.Column("extension_id", sa.String(32), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
    )
    op.create_index("ix_extension_pairings_user_id", "extension_pairings", ["user_id"])
    op.create_table(
        "outreach_sessions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"),
                  nullable=False),
        sa.Column("intention", sa.String(200), nullable=False),
        sa.Column("target_minutes", sa.Integer(), nullable=False),
        sa.Column("state", sa.String(20), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.Column("running_since", sa.DateTime(timezone=True)),
        sa.Column("elapsed_seconds", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint(
            "state IN ('active','paused','review','completed')", name="session_state"
        ),
        sa.CheckConstraint("elapsed_seconds >= 0", name="session_elapsed"),
        sa.CheckConstraint("target_minutes BETWEEN 5 AND 180", name="session_target"),
    )
    op.create_index("ix_outreach_sessions_user_id", "outreach_sessions", ["user_id"])
    op.create_index("one_open_session", "outreach_sessions", ["user_id"], unique=True,
                    postgresql_where=sa.text("state != 'completed'"))
    op.create_table(
        "captures",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("session_id", sa.Uuid(),
                  sa.ForeignKey("outreach_sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("request_id", sa.Uuid(), nullable=False),
        sa.Column("source", sa.String(20), nullable=False),
        sa.Column("original", postgresql.JSONB(), nullable=False),
        sa.Column("details", postgresql.JSONB(), nullable=False),
        sa.Column("decision", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.Column("reviewed_at", sa.DateTime(timezone=True)),
        sa.Column("followup_done", sa.Boolean(), nullable=False, server_default="false"),
        sa.CheckConstraint(
            "decision IN ('pending','approved','discarded')", name="capture_decision"
        ),
        sa.CheckConstraint("source IN ('manual','browser')", name="capture_source"),
    )
    op.create_index("capture_request_once", "captures", ["session_id", "request_id"], unique=True)
    op.create_index("ix_captures_session_id", "captures", ["session_id"])
    op.create_table(
        "session_events",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("session_id", sa.Uuid(),
                  sa.ForeignKey("outreach_sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("action", sa.Text(), nullable=False),
        sa.Column("at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_session_events_session_id", "session_events", ["session_id"])


def downgrade():
    for name in ["session_events", "captures", "outreach_sessions", "extension_pairings", "logins",
                 "users"]:
        op.drop_table(name)
