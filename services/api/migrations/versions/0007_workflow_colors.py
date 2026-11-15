"""Persist a workflow's visual identity without changing records or field contracts."""

import sqlalchemy as sa
from alembic import op

revision = "0007_workflow_colors"
down_revision = "0006_ai_runs"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("workflows", sa.Column("color", sa.String(7), nullable=False,
                                        server_default="#c8ef80"))
    op.execute("""
        WITH ranked AS (
          SELECT id, (row_number() OVER (PARTITION BY user_id ORDER BY created_at, id) - 1) % 7 AS n
          FROM workflows
        )
        UPDATE workflows w SET color = CASE r.n
          WHEN 0 THEN '#c8ef80' WHEN 1 THEN '#f6a58b' WHEN 2 THEN '#7fd6d0'
          WHEN 3 THEN '#b7adf5' WHEN 4 THEN '#edca76' WHEN 5 THEN '#9bbcf2'
          ELSE '#e8a3cc' END
        FROM ranked r WHERE w.id = r.id
    """)
    op.create_check_constraint("workflow_color_hex", "workflows", "color ~ '^#[0-9a-f]{6}$'")


def downgrade():
    op.drop_constraint("workflow_color_hex", "workflows", type_="check")
    op.drop_column("workflows", "color")
