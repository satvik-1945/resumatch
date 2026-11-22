"""Connected Gmail accounts and inbox-scan runs. Additive; existing runs become source='manual'."""

import sqlalchemy as sa
from alembic import op

revision = "0008_email_applications"
down_revision = "0007_workflow_colors"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("outreach_sessions", sa.Column("source", sa.String(20), nullable=False,
                                                 server_default="manual"))
    op.create_check_constraint("session_source", "outreach_sessions",
                               "source IN ('manual','email')")
    # One open manual session as before, plus at most one open inbox-review run.
    op.drop_index("one_open_session", "outreach_sessions")
    op.create_index("one_open_session", "outreach_sessions", ["user_id"], unique=True,
                    postgresql_where=sa.text("state != 'completed' AND source = 'manual'"))
    op.create_index("one_open_inbox_run", "outreach_sessions", ["user_id"], unique=True,
                    postgresql_where=sa.text("state != 'completed' AND source = 'email'"))

    op.drop_constraint("capture_source", "captures", type_="check")
    op.create_check_constraint("capture_source", "captures",
                               "source IN ('manual','browser','email')")

    op.create_table(
        "email_accounts", sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"),
                  nullable=False, index=True),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("refresh_token", sa.Text(), nullable=False),  # Fernet-encrypted
        sa.Column("connected_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.Column("last_scanned_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.UniqueConstraint("user_id", "email", name="one_account_per_address"),
    )
    op.create_table(
        "oauth_states", sa.Column("state", sa.String(64), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"),
                  nullable=False),
        sa.Column("code_verifier", sa.String(128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
    )
    op.create_table(
        "email_messages", sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("account_id", sa.Uuid(),
                  sa.ForeignKey("email_accounts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("gmail_id", sa.String(64), nullable=False),
        sa.Column("thread_id", sa.String(64), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sender", sa.String(500), nullable=False, server_default=""),
        sa.Column("subject", sa.String(1000), nullable=False, server_default=""),
        sa.Column("category", sa.String(20), nullable=False),
        sa.Column("company", sa.String(200), nullable=False, server_default=""),
        sa.Column("capture_id", sa.Uuid(), sa.ForeignKey("captures.id", ondelete="SET NULL"),
                  nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.CheckConstraint("category IN ('application','response','ignored')",
                           name="email_category"),
        sa.UniqueConstraint("account_id", "gmail_id", name="one_row_per_message"),
    )
    op.create_index("ix_email_messages_thread", "email_messages", ["account_id", "thread_id"])


def downgrade():
    op.drop_index("ix_email_messages_thread", "email_messages")
    op.drop_table("email_messages")
    op.drop_table("oauth_states")
    op.drop_table("email_accounts")
    op.execute("DELETE FROM captures WHERE source = 'email'")
    op.drop_constraint("capture_source", "captures", type_="check")
    op.create_check_constraint("capture_source", "captures", "source IN ('manual','browser')")
    op.execute("DELETE FROM outreach_sessions WHERE source = 'email'")
    op.drop_index("one_open_inbox_run", "outreach_sessions")
    op.drop_index("one_open_session", "outreach_sessions")
    op.create_index("one_open_session", "outreach_sessions", ["user_id"], unique=True,
                    postgresql_where=sa.text("state != 'completed'"))
    op.drop_constraint("session_source", "outreach_sessions", type_="check")
    op.drop_column("outreach_sessions", "source")
