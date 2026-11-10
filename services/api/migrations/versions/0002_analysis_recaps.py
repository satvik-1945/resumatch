"""Private capture suggestions and immutable completed-session recap snapshots."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0002_analysis_recaps"
down_revision = "0001_outreach"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("captures", sa.Column("analysis", postgresql.JSONB(), nullable=True))
    op.create_table(
        "session_recaps",
        sa.Column("session_id", sa.Uuid(),
                  sa.ForeignKey("outreach_sessions.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.Column("reflection", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
    )


def downgrade():
    op.drop_table("session_recaps")
    op.drop_column("captures", "analysis")
