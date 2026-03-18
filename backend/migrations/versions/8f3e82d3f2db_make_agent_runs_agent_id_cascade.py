"""make_agent_runs_agent_id_cascade

Revision ID: 8f3e82d3f2db
Revises: d2192aa1e33e
Create Date: 2026-03-18 11:10:00.000000

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "8f3e82d3f2db"
down_revision: str | Sequence[str] | None = "d2192aa1e33e"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_constraint("agent_runs_agent_id_fkey", "agent_runs", type_="foreignkey")
    op.create_foreign_key(
        "agent_runs_agent_id_fkey",
        "agent_runs",
        "agents",
        ["agent_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint("agent_runs_agent_id_fkey", "agent_runs", type_="foreignkey")
    op.create_foreign_key(
        "agent_runs_agent_id_fkey",
        "agent_runs",
        "agents",
        ["agent_id"],
        ["id"],
    )
