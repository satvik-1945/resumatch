"""Sender background and per-contact message briefs. Additive; existing rows untouched."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0004_contact_briefs"
down_revision = "0003_workflows"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("users", sa.Column("about_me", sa.Text(), nullable=False, server_default=""))
    op.create_table(
        "contact_briefs", sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"),
                  nullable=False),
        sa.Column("contact_key", sa.String(300), nullable=False),
        sa.Column("company_url", sa.String(2000), nullable=True),
        sa.Column("research", JSONB(), nullable=False),
        sa.Column("brief", JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.UniqueConstraint("user_id", "contact_key", name="one_brief_per_contact"),
    )
    op.create_index("ix_contact_briefs_user_id", "contact_briefs", ["user_id"])


def downgrade():
    op.drop_index("ix_contact_briefs_user_id", "contact_briefs")
    op.drop_table("contact_briefs")
    op.drop_column("users", "about_me")
