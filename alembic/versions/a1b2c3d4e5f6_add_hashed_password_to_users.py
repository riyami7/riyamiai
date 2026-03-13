"""add_hashed_password_to_users

Revision ID: a1b2c3d4e5f6
Revises: 148368cc64fd
Create Date: 2026-02-12 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = '148368cc64fd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add hashed_password column to users table."""
    # Add as nullable first to handle any existing rows
    op.add_column('users', sa.Column('hashed_password', sa.String(255), nullable=True))

    # Set a placeholder for any existing rows (they will need to reset their password)
    op.execute("UPDATE users SET hashed_password = 'NEEDS_RESET' WHERE hashed_password IS NULL")

    # Now make it non-nullable
    op.alter_column('users', 'hashed_password', nullable=False)


def downgrade() -> None:
    """Remove hashed_password column from users table."""
    op.drop_column('users', 'hashed_password')
