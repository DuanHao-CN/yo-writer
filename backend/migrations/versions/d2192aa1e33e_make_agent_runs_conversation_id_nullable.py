"""make_agent_runs_conversation_id_nullable

Revision ID: d2192aa1e33e
Revises: 44744a1a4454
Create Date: 2026-03-18 10:11:07.872299

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'd2192aa1e33e'
down_revision: str | Sequence[str] | None = '44744a1a4454'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.alter_column('agent_runs', 'conversation_id',
               existing_type=sa.UUID(),
               nullable=True)


def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column('agent_runs', 'conversation_id',
               existing_type=sa.UUID(),
               nullable=False)
