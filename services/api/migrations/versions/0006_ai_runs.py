"""AI generation log: prompt versions and one row per AI call. Additive."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0006_ai_runs"
down_revision = "0005_persona_context"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "ai_prompts", sa.Column("sha256", sa.String(64), primary_key=True),
        sa.Column("kind", sa.String(40), nullable=False),
        sa.Column("instruction", sa.Text(), nullable=False),
        sa.Column("output_schema", JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
    )
    op.create_table(
        "ai_runs", sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"),
                  nullable=False),
        sa.Column("kind", sa.String(40), nullable=False),
        sa.Column("subject", sa.String(300), nullable=True),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("prompt_sha256", sa.String(64), sa.ForeignKey("ai_prompts.sha256"),
                  nullable=True),
        sa.Column("model", sa.String(200), nullable=True),
        sa.Column("meta", JSONB(), nullable=False, server_default="{}"),
        sa.Column("research", JSONB(), nullable=True),
        sa.Column("input", JSONB(), nullable=True),
        sa.Column("output", JSONB(), nullable=True),
        sa.Column("result", JSONB(), nullable=True),
        sa.Column("rejected", JSONB(), nullable=False, server_default="[]"),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("prompt_tokens", sa.Integer(), nullable=True),
        sa.Column("completion_tokens", sa.Integer(), nullable=True),
        sa.Column("rating", sa.SmallInteger(), nullable=True),
        sa.Column("feedback", sa.Text(), nullable=False, server_default=""),
        sa.Column("rated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.CheckConstraint("rating IN (-1, 1)", name="ai_rating_values"),
    )
    op.create_index("ix_ai_runs_user_created", "ai_runs", ["user_id", "created_at"])


def downgrade():
    op.drop_index("ix_ai_runs_user_created", "ai_runs")
    op.drop_table("ai_runs")
    op.drop_table("ai_prompts")
