"""Resume text + grounded persona on users, per-contact outreach context. Additive."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0005_persona_context"
down_revision = "0004_contact_briefs"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("users", sa.Column("resume_text", sa.Text(), nullable=False, server_default=""))
    op.add_column("users", sa.Column("persona", JSONB(), nullable=True))
    op.add_column("contact_briefs",
                  sa.Column("context", sa.Text(), nullable=False, server_default=""))


def downgrade():
    op.drop_column("contact_briefs", "context")
    op.drop_column("users", "persona")
    op.drop_column("users", "resume_text")
